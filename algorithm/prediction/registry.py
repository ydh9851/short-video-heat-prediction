"""
模型注册表同步（参考 MLflow Model Registry 的「版本 + 阶段」概念）

为什么需要：
    model_cache/ 里每个 .joblib 只是一个文件，谁是最新、哪个在线上、指标多少，
    全靠记忆。一旦改了特征工程、重训了模型，很难说清"线上跑的是哪一版"。

本脚本扫描 model_cache，把每个模型的 bundle 元信息（指标、特征版本、训练时间、体积）
登记到 data/models/model_registry.json，并保留已有的阶段（production / staging / archived），
使「模型版本」成为可展示、可切换、可回滚的对象。

CLI：
  python registry.py --sync           # 扫描缓存并写注册表
  python registry.py --list           # 只读输出
"""
import argparse
import json
import os
import shutil
import sys
import traceback
from datetime import datetime

PRED_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_ROOT = os.path.dirname(os.path.dirname(PRED_DIR))
CACHE_DIR = os.path.join(PRED_DIR, "model_cache")
MODELS_DIR = os.path.join(SYSTEM_ROOT, "data", "models")
VERSIONS_DIR = os.path.join(MODELS_DIR, "versions")
REGISTRY = os.path.join(MODELS_DIR, "model_registry.json")

sys.path.insert(0, PRED_DIR)
import predict_api as P  # noqa: E402

MODELS = ["lgbm", "xgb", "rf", "lr", "knn", "svm", "dt"]


def _version_of(path, bundle):
    """版本号优先取训练时写入 bundle 的 model_version，旧缓存回退到文件时间戳。"""
    if isinstance(bundle, dict) and bundle.get("model_version"):
        return str(bundle["model_version"])
    fv = bundle.get("feature_version", P.FEATURE_VERSION) if isinstance(bundle, dict) else P.FEATURE_VERSION
    stamp = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y%m%d_%H%M%S")
    return "v%s-%s" % (fv, stamp)


def artifact_relpath(name, version):
    """版本归档文件相对 data/models 的路径（统一使用 / 便于跨平台与 JSON 展示）。"""
    return "versions/%s/%s.joblib" % (name, version)


def artifact_path(name, version):
    return os.path.join(MODELS_DIR, *artifact_relpath(name, version).split("/"))


def _archive_artifact(name, version, source):
    """把当前缓存复制为不可变版本归档；已存在且大小一致则跳过。"""
    dest = artifact_path(name, version)
    if os.path.isfile(dest) and os.path.getsize(dest) == os.path.getsize(source):
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".tmp"
    shutil.copy2(source, tmp)
    os.replace(tmp, dest)
    return dest


def _current_data_version():
    """当前训练集的数据集版本号；未登记时返回空串。

    数据集版本由 algorithm/datasets/versioning.py 维护：导入新数据会登记新版本，
    这里读取最近一版，使模型版本与数据版本形成可追溯的对应关系。
    """
    try:
        import sys
        datasets_dir = os.path.join(SYSTEM_ROOT, "algorithm", "datasets")
        if datasets_dir not in sys.path:
            sys.path.insert(0, datasets_dir)
        import versioning
        return versioning.current_version("douyin")
    except Exception:
        return ""


def _read_registry():
    if os.path.isfile(REGISTRY):
        try:
            with open(REGISTRY, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("models"), dict):
                return data
        except Exception:
            pass
    return {"updatedAt": None, "models": {}}


def sync():
    """扫描模型缓存，合并进注册表；新版本默认 staging，原 production 保持不变。"""
    import joblib

    reg = _read_registry()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for name in MODELS:
        path = os.path.join(CACHE_DIR, "predict_%s.joblib" % name)
        if not os.path.isfile(path):
            continue
        try:
            bundle = joblib.load(path)
        except Exception:
            continue
        if not isinstance(bundle, dict):
            continue
        version = _version_of(path, bundle)
        # 将当前缓存归档为不可变版本文件，使 promote/rollback 真正能加载到对应权重
        _archive_artifact(name, version, path)
        entry = reg["models"].setdefault(name, {"versions": []})
        known = {v["version"] for v in entry["versions"]}
        if version not in known:
            metrics = bundle.get("metrics") or {}
            entry["versions"].append({
                "version": version,
                "stage": "staging",
                "featureVersion": bundle.get("feature_version", P.FEATURE_VERSION),
                # 训练时所用数据集的版本号，用于回答"指标变了是模型改坏了还是数据换了"
                "dataVersion": bundle.get("data_version") or _current_data_version(),
                "r2": metrics.get("r2"),
                "mae": metrics.get("mae"),
                "rmse": metrics.get("rmse"),
                "sizeMB": round(os.path.getsize(path) / 1024.0 / 1024.0, 2),
                "trainedAt": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S"),
                "artifact": artifact_relpath(name, version),
            })
            entry["versions"].sort(key=lambda v: v["trainedAt"])
        else:
            # 历史版本补充归档字段，避免旧注册表无法定位权重
            for v in entry["versions"]:
                if v["version"] == version:
                    v["artifact"] = artifact_relpath(name, version)
                    break

        # 迁移策略：若 active 指向的历史版本没有归档文件或特征体系已过期，说明它无法被真实加载。
        # 此时把"当前缓存"登记为线上版本，保证注册表描述的就是系统实际服务所用的模型。
        active = entry.get("active")
        active_ok = (bool(active)
                     and os.path.isfile(artifact_path(name, active))
                     and _feature_version_of(entry, active) == P.FEATURE_VERSION)
        current_compatible = bundle.get("feature_version", P.FEATURE_VERSION) == P.FEATURE_VERSION
        if not active_ok:
            if current_compatible:
                entry["active"] = version
                for v in entry["versions"]:
                    v["stage"] = "production" if v["version"] == version else "archived"
            else:
                # 当前缓存也属于旧特征体系：不指向任何线上版本，等首次推理重训后自动登记
                entry["active"] = None
                for v in entry["versions"]:
                    if v.get("stage") == "production":
                        v["stage"] = "archived"
        else:
            if not any(v["stage"] == "production" for v in entry["versions"]):
                for v in entry["versions"]:
                    if v["version"] == active:
                        v["stage"] = "production"
                        break
            entry["active"] = active

    reg["featureVersion"] = P.FEATURE_VERSION
    reg["updatedAt"] = now
    os.makedirs(os.path.dirname(REGISTRY), exist_ok=True)
    tmp = REGISTRY + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, REGISTRY)
    return reg


def _feature_version_of(entry, version):
    """版本登记的特征体系版本；未登记时按当前版本处理（兼容旧注册表）。"""
    for v in entry.get("versions") or []:
        if str(v.get("version")) == str(version):
            fv = v.get("featureVersion")
            return int(fv) if fv is not None else P.FEATURE_VERSION
    return P.FEATURE_VERSION


def _artifact_available(name, version, entry):
    rel = entry.get("artifact")
    path = os.path.join(MODELS_DIR, *rel.split("/")) if rel else artifact_path(name, version)
    return os.path.isfile(path)


def summary(reg):
    out = []
    for name, entry in sorted(reg.get("models", {}).items()):
        versions = entry.get("versions", [])
        active = entry.get("active")
        cur = next((v for v in versions if v["version"] == active), versions[-1] if versions else {})
        out.append({
            "model": name,
            "activeVersion": active,
            "versionCount": len(versions),
            "activeArtifactAvailable": bool(active) and _artifact_available(name, active, cur),
            # 历史版本清单（新→旧），供前端做版本切换与回滚
            "versions": [
                {
                    "version": v.get("version"),
                    "stage": v.get("stage"),
                    "r2": v.get("r2"),
                    "trainedAt": v.get("trainedAt"),
                    # 训练所用数据集版本：指标变化时可区分是模型改动还是数据替换
                    "dataVersion": v.get("dataVersion"),
                    # 归档文件是否存在；不存在的旧版本只能查看、不能上线或回滚
                    "artifactAvailable": _artifact_available(name, v.get("version"), v),
                }
                for v in reversed(versions)
            ],
            "stage": cur.get("stage"),
            "r2": cur.get("r2"),
            "mae": cur.get("mae"),
            "rmse": cur.get("rmse"),
            "featureVersion": cur.get("featureVersion"),
            "trainedAt": cur.get("trainedAt"),
            "sizeMB": cur.get("sizeMB"),
        })
    return out


def main():
    ap = argparse.ArgumentParser(description="模型注册表同步（版本 + 阶段）")
    ap.add_argument("--sync", action="store_true", help="扫描 model_cache 并写入注册表")
    ap.add_argument("--list", action="store_true", help="只输出当前注册表摘要")
    args = ap.parse_args()
    try:
        if args.sync or not args.list:
            reg = sync()
        else:
            reg = _read_registry()
        print(json.dumps({"mode": "model-registry", "updatedAt": reg.get("updatedAt"),
                          "models": summary(reg)}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc(),
                          "trace_id": os.environ.get("TRACE_ID")}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
