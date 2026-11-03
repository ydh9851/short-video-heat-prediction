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
import sys
import traceback
from datetime import datetime

PRED_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_ROOT = os.path.dirname(os.path.dirname(PRED_DIR))
CACHE_DIR = os.path.join(PRED_DIR, "model_cache")
REGISTRY = os.path.join(SYSTEM_ROOT, "data", "models", "model_registry.json")

sys.path.insert(0, PRED_DIR)
import predict_api as P  # noqa: E402

MODELS = ["lgbm", "xgb", "rf", "lr", "knn", "svm", "dt"]


def _version_of(path, bundle):
    """版本号 = 特征版本 + 文件时间戳：特征变了或模型重训了，版本号必然变化。"""
    fv = bundle.get("feature_version", P.FEATURE_VERSION) if isinstance(bundle, dict) else P.FEATURE_VERSION
    stamp = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y%m%d_%H%M%S")
    return "v%s-%s" % (fv, stamp)


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
            })
            entry["versions"].sort(key=lambda v: v["trainedAt"])
        # 若该模型还没有 production 版本，把最早的设为 production，保证系统始终有线上模型
        if not any(v["stage"] == "production" for v in entry["versions"]):
            entry["versions"][0]["stage"] = "production"
        entry["active"] = next((v["version"] for v in entry["versions"] if v["stage"] == "production"),
                               entry["versions"][-1]["version"])

    reg["updatedAt"] = now
    os.makedirs(os.path.dirname(REGISTRY), exist_ok=True)
    with open(REGISTRY, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    return reg


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
            # 历史版本清单（新→旧），供前端做版本切换与回滚
            "versions": [
                {
                    "version": v.get("version"),
                    "stage": v.get("stage"),
                    "r2": v.get("r2"),
                    "trainedAt": v.get("trainedAt"),
                    # 训练所用数据集版本：指标变化时可区分是模型改动还是数据替换
                    "dataVersion": v.get("dataVersion"),
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
