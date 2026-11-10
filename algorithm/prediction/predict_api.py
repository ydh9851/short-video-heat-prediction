# -*- coding: utf-8 -*-
"""
predict_api.py —— 短视频热度预测命令行封装
==========================================
把 LightGBM 热度预测模型封装成 CLI，供 Java 后端通过 ProcessBuilder 调用
（与 movie-system 的 predict_api.py 保持同一契约风格）。

输入特征（发布时即可获得的先验信息，详见 FeatureEDA/preprocess.py 的防泄漏说明）：
    video_category(视频类别) / author_fans(作者粉丝数) / publish_hour(小时) /
    publish_weekday(星期) / publish_month(月份)
    -> 派生 is_weekend / hour_bucket / author_fans_log

预测目标：heat = 播放量 + 3×点赞 + 5×评论 + 8×转发（log1p 训练，expm1 还原）

模型按 --model 训练并缓存到 model_cache/predict_<model>.joblib：
    - 首次调用自动训练并缓存（lightgbm/xgboost 约 10~60 秒，其余更快）；
    - 之后直接加载缓存，秒级返回。

用法:
    # 单条预测（首次会自动训练）
    python predict_api.py --model lgbm --category 美食 --fans 50000 --hour 20 --weekday 5 --month 3

    # 仅预训练并缓存指定模型（部署后先跑一次预热）
    python predict_api.py --train --model lgbm

成功输出（单行 JSON）:
    {"model":"lgbm","prediction":12345.6,"prediction_log":9.42,"trained_now":false,
     "cache_file":"...","metrics":{"rmse":...,"mae":...,"r2":...},
     "metrics_raw":{"rmse":...,"mae":...,"r2":...}}

失败输出（单行 JSON，退出码非 0）:
    {"model":"...","error":"...","trace":"..."}
"""

import argparse
import contextlib
import json
import os
import shutil
import sys
import traceback
import warnings
from datetime import datetime
from urllib.parse import unquote_plus

warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
SYSTEM_ROOT = os.path.dirname(os.path.dirname(BASE))   # 系统工程根目录
PROCESSED_DIR = os.path.join(SYSTEM_ROOT, "data", "processed")
TRAIN_CSV = os.path.join(PROCESSED_DIR, "train_clean.csv")
TEST_CSV = os.path.join(PROCESSED_DIR, "test_clean.csv")
CACHE_DIR = os.path.join(BASE, "model_cache")
# 模型治理：注册表与不可变版本归档目录
MODELS_DIR = os.path.join(SYSTEM_ROOT, "data", "models")
VERSIONS_DIR = os.path.join(MODELS_DIR, "versions")
REGISTRY_FILE = os.path.join(MODELS_DIR, "model_registry.json")

CAT_FEATURES = ["video_category", "hour_bucket"]
NUM_FEATURES = ["author_fans_log", "publish_hour", "publish_weekday", "publish_month", "is_weekend"]
FEATURE_NAMES = NUM_FEATURES + CAT_FEATURES
CAT_IDX = [FEATURE_NAMES.index(c) for c in CAT_FEATURES]
TARGET_LOG = "heat_log"

MODELS = ["lr", "knn", "svm", "dt", "rf", "lgbm", "xgb"]

# 特征体系版本号：特征列、类别编码规则、目标变换或训练数据口径发生任何变化都必须 +1。
# 加载缓存时校验该版本，不一致则作废重训，避免旧 joblib 静默给出错误预测。
# v4：未知类别映射到预留码 N（len(m)），不再与众数（0）共用编码——
#     此前「从未见过的类别」会被当成最强类别信号，语义错误（P1-6）。
FEATURE_VERSION = 4


def _current_data_version():
    """当前训练集的数据集版本号（由 datasets/versioning.py 维护）；取不到时返回空串。"""
    try:
        import sys
        datasets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "datasets")
        if datasets_dir not in sys.path:
            sys.path.insert(0, datasets_dir)
        import versioning
        return versioning.current_version("douyin")
    except Exception:
        return ""


def _stdout_reconfigure():
    """Windows 管道下统一 UTF-8 输出，Java 端按 UTF-8 解码。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _hour_bucket(hour):
    h = int(hour)
    if 0 <= h < 6:
        return "凌晨(0-5)"
    if 6 <= h < 12:
        return "上午(6-11)"
    if 12 <= h < 18:
        return "下午(12-17)"
    return "晚间(18-23)"


def _load_frames(platform=None):
    """加载训练/测试集。

    platform 为 None 时，回退行为：
      读 data/processed/train_clean.csv 和 test_clean.csv（抖音原始预切分）。
    platform 指定时：
      读 data/processed/<platform>_clean.csv，按 publish_time 升序前 80% 作训练，
      后 20% 作测试。
    """
    if platform is None or platform == "douyin":
        if not os.path.exists(TRAIN_CSV):
            raise FileNotFoundError(
                "未找到清洗数据，请先运行 algorithm/FeatureEDA/preprocess.py 生成 " + TRAIN_CSV)
        train = pd.read_csv(TRAIN_CSV)
        test = pd.read_csv(TEST_CSV) if os.path.exists(TEST_CSV) else train.iloc[:0].copy()
        return train, test

    platform_csv = os.path.join(PROCESSED_DIR, f"{platform}_clean.csv")
    if not os.path.exists(platform_csv):
        raise FileNotFoundError(
            f"未找到平台 {platform} 的清洗数据：{platform_csv}，请先执行 ingest.py --platform {platform}")

    df = pd.read_csv(platform_csv)
    # 按发布时间排序，前 80% 训练、后 20% 测试（时间切分更贴近真实业务时序）
    df = df.sort_values("publish_time").reset_index(drop=True)
    cut = int(len(df) * 0.8)
    train = df.iloc[:cut].copy()
    test = df.iloc[cut:].copy()
    return train, test


def _fit_cat_maps(train):
    """基于训练集为每个类别特征建立 {取值: 编码} 映射：众数固定编码 0，其余顺序编码 1..N-1。

    编码规则（v4）：
    - 众数（最强类别信号）→ 0
    - 其余已见类别 → 1..N-1
    - 未知类别 → N（预留码，= len(m)），与众数/已知类别均不共用编码。
      此前未知类别回退众数（0），会把「从未见过的类别」当成最强类别处理，语义错误。
    """
    maps, modes = {}, {}
    for col in CAT_FEATURES:
        vals = train[col].astype(str)
        mode_val = vals.mode()[0]
        uniq = [v for v in dict.fromkeys(vals.tolist()) if v != mode_val]
        m = {mode_val: 0}
        m.update({v: i + 1 for i, v in enumerate(uniq)})
        maps[col] = m
        modes[col] = mode_val
    return maps, modes


def _encode_frame(df, maps, modes):
    out = df.copy()
    for col in CAT_FEATURES:
        m = maps[col]
        unknown_code = len(m)  # 预留码 N：未知类别专属，与众数(0)及已知类别(1..N-1)区分开
        out[col] = out[col].astype(str).map(lambda v: m.get(v, unknown_code))
    out["author_fans_log"] = pd.to_numeric(out["author_fans_log"], errors="coerce").fillna(0.0)
    for col in ["publish_hour", "publish_weekday", "publish_month", "is_weekend"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(-1)
    return out[FEATURE_NAMES].astype(float)


def _prepare(platform=None):
    train, test = _load_frames(platform=platform)
    maps, modes = _fit_cat_maps(train)
    X_train = _encode_frame(train, maps, modes)
    y_train = train[TARGET_LOG].astype(float).values
    X_test = _encode_frame(test, maps, modes) if len(test) else None
    y_test = test[TARGET_LOG].astype(float).values if len(test) else None
    meta = {"cat_maps": maps, "cat_modes": modes, "feature_names": FEATURE_NAMES}
    return X_train, y_train, X_test, y_test, meta


def build_model(name, X_train, y_train):
    if name == "lgbm":
        import lightgbm as lgb
        params = {
            "objective": "regression",
            "metric": "rmse",
            "boosting_type": "gbdt",
            "learning_rate": 0.05,
            "num_leaves": 31,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
        }
        ds = lgb.Dataset(X_train, label=y_train, categorical_feature=CAT_IDX, free_raw_data=False)
        return lgb.train(params, ds, num_boost_round=500)
    if name == "xgb":
        from xgboost import XGBRegressor
        return XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=6,
                            subsample=0.8, colsample_bytree=0.8, random_state=42,
                            n_jobs=-1).fit(X_train, y_train)
    if name == "rf":
        from sklearn.ensemble import RandomForestRegressor
        # 限制树深与叶样本数，避免模型缓存过大（深度学习式无剪枝森林可达数百 MB）
        return RandomForestRegressor(n_estimators=120, max_depth=16, min_samples_leaf=5,
                                     random_state=42, n_jobs=-1).fit(X_train, y_train)
    if name == "lr":
        from sklearn.linear_model import LinearRegression
        return LinearRegression().fit(X_train, y_train)
    if name == "knn":
        from sklearn.neighbors import KNeighborsRegressor
        return KNeighborsRegressor(n_neighbors=5, weights="distance", n_jobs=-1).fit(X_train, y_train)
    if name == "svm":
        from sklearn.svm import SVR
        return SVR(kernel="rbf", C=10.0, gamma="scale", epsilon=0.1).fit(X_train, y_train)
    if name == "dt":
        from sklearn.tree import DecisionTreeRegressor
        return DecisionTreeRegressor(random_state=42).fit(X_train, y_train)
    raise ValueError("unknown model: %s" % name)


def _fit(name, X_train, y_train):
    """统一 fit：LightGBM 走 lgb.train，其余 sklearn。"""
    if name == "lgbm":
        return build_model(name, X_train, y_train)
    return build_model(name, X_train, y_train)


def calc_metrics(model, X_test, y_test):
    """在 log 空间与原始热度空间分别评估（log 空间更稳定，原始空间更贴近业务）。"""
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    pred_log = model.predict(X_test)
    pred_raw = np.expm1(pred_log)
    y_raw = np.expm1(y_test)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_test, pred_log))),
        "mae": float(mean_absolute_error(y_test, pred_log)),
        "r2": float(r2_score(y_test, pred_log)),
    }, {
        "rmse": float(np.sqrt(mean_squared_error(y_raw, pred_raw))),
        "mae": float(mean_absolute_error(y_raw, pred_raw)),
        "r2": float(r2_score(y_raw, pred_raw)),
    }


def cache_path(name, platform=None):
    """模型缓存路径。

    platform 为空 / douyin 时沿用 predict_<name>.joblib（与既有缓存兼容）；
    指定其它平台时使用 predict_<name>_<platform>.joblib，实现"一平台一模型"。
    """
    if platform is None or platform == "douyin":
        return os.path.join(CACHE_DIR, "predict_%s.joblib" % name)
    return os.path.join(CACHE_DIR, "predict_%s_%s.joblib" % (name, platform))


def _read_registry():
    try:
        with open(REGISTRY_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _version_entry(name, version):
    entry = (_read_registry().get("models") or {}).get(name) or {}
    for item in entry.get("versions") or []:
        if str(item.get("version")) == str(version):
            return item
    return {}


def version_artifact(name, version):
    """返回版本归档文件路径；注册表里有 artifact 字段时以其为准。"""
    entry = _version_entry(name, version)
    rel = str(entry.get("artifact") or "").strip()
    if rel:
        return os.path.join(MODELS_DIR, *rel.split("/"))
    return os.path.join(VERSIONS_DIR, name, "%s.joblib" % version)


def active_version(name):
    """返回可真实加载的线上版本号。

    同时要求：归档文件存在，且登记的特征版本与当前代码一致；
    否则返回 None（回退当前缓存 / 触发重训），避免把旧特征体系的权重当线上模型。
    """
    entry = (_read_registry().get("models") or {}).get(name) or {}
    active = entry.get("active")
    if not active:
        return None
    item = next((v for v in entry.get("versions") or []
                 if str(v.get("version")) == str(active)), {})
    fv = item.get("featureVersion")
    if fv is not None and int(fv) != FEATURE_VERSION:
        return None
    return str(active) if os.path.isfile(version_artifact(name, active)) else None


def _write_registry(reg):
    """原子写注册表：先写临时文件再替换，避免并发读到半截 JSON。"""
    os.makedirs(MODELS_DIR, exist_ok=True)
    tmp = REGISTRY_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, REGISTRY_FILE)


def _register_version(name, version, bundle, path):
    """训练完成后立即把新版本登记为线上版本。

    否则会出现"缓存已重训、注册表还指着旧版本"的窗口期，治理页展示的线上版本与实际推理不符。
    """
    reg = _read_registry()
    models = reg.setdefault("models", {})
    entry = models.setdefault(name, {"versions": []})
    versions = entry.setdefault("versions", [])
    metrics = bundle.get("metrics") or {}
    item = {
        "version": version,
        "stage": "production",
        "featureVersion": bundle.get("feature_version", FEATURE_VERSION),
        "dataVersion": bundle.get("data_version") or _current_data_version(),
        "r2": metrics.get("r2"),
        "mae": metrics.get("mae"),
        "rmse": metrics.get("rmse"),
        "sizeMB": round(os.path.getsize(path) / 1024.0 / 1024.0, 2),
        "trainedAt": bundle.get("trained_at")
        or datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S"),
        "artifact": "versions/%s/%s.joblib" % (name, version),
    }
    existing = next((v for v in versions if str(v.get("version")) == version), None)
    if existing is None:
        versions.append(item)
    else:
        existing.update(item)
    versions.sort(key=lambda v: v.get("trainedAt") or "")
    for v in versions:
        v["stage"] = "production" if str(v.get("version")) == version else "archived"
    entry["active"] = version
    reg["featureVersion"] = FEATURE_VERSION
    reg["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _write_registry(reg)


def _archive_bundle(name, version, source):
    dest = os.path.join(VERSIONS_DIR, name, "%s.joblib" % version)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".tmp"
    shutil.copy2(source, tmp)
    os.replace(tmp, dest)
    return dest


@contextlib.contextmanager
def _file_lock(lock_path):
    """跨进程互斥锁：防止 CLI 与常驻引擎 / 多个 HTTP 请求同时训练并写坏同一个 joblib。

    Windows 用 msvcrt.locking，Linux/macOS 用 fcntl.flock；不引入额外依赖。
    """
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    f = open(lock_path, "a+b")
    try:
        if os.name == "nt":
            import msvcrt
            # LK_LOCK 会阻塞到拿到锁
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_UN)
        finally:
            f.close()


def train_and_cache(name, platform=None):
    import joblib
    X_train, y_train, X_test, y_test, meta = _prepare(platform=platform)
    model = _fit(name, X_train, y_train)
    metrics_log, metrics_raw = calc_metrics(model, X_test, y_test)
    os.makedirs(CACHE_DIR, exist_ok=True)
    now = datetime.now()
    version = "v%s-%s" % (FEATURE_VERSION, now.strftime("%Y%m%d_%H%M%S_%f"))
    bundle = {
        "model": model, "metrics": metrics_log, "metrics_raw": metrics_raw,
        "feature_names": FEATURE_NAMES, "meta": meta,
        "feature_version": FEATURE_VERSION,
        "model_version": version,
        "trained_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        # 训练所用数据集的版本号：指标变化时可区分是模型改动还是数据替换
        "data_version": _current_data_version(),
    }
    path = cache_path(name, platform)
    tmp = path + ".tmp"
    joblib.dump(bundle, tmp, compress=3)
    os.replace(tmp, path)
    # 每次训练都沉淀一份不可变归档，供 promote/rollback 使用
    artifact_name = name if (platform is None or platform == "douyin") else "%s_%s" % (name, platform)
    _archive_bundle(artifact_name, version, path)
    # 主平台训练完成后立即同步注册表，避免"缓存已换、线上版本未变"的窗口期
    if platform is None or platform == "douyin":
        _register_version(name, version, bundle, path)
    return metrics_log, metrics_raw, version


def bundle_compatible(bundle):
    """缓存兼容性校验：特征版本 + 特征列顺序 + 训练数据版本必须与当前一致，否则视为脏缓存。

    数据版本仅在两侧都非空时才校验：数据集版本体系未启用时不误判旧缓存。
    """
    if not isinstance(bundle, dict):
        return False
    if bundle.get("feature_version") != FEATURE_VERSION:
        return False
    if list(bundle.get("feature_names") or []) != FEATURE_NAMES:
        return False
    cached_dv = str(bundle.get("data_version") or "")
    current_dv = str(_current_data_version() or "")
    if cached_dv and current_dv and cached_dv != current_dv:
        return False
    return True


def load_or_train(name, platform=None, version=None):
    """加载模型：优先使用显式版本 / 线上版本归档，其次当前缓存，最后自动重训。"""
    import joblib
    if platform is None or platform == "douyin":
        if version is None:
            version = active_version(name)
        if version:
            artifact = version_artifact(name, version)
            if os.path.isfile(artifact):
                bundle = joblib.load(artifact)
                if bundle_compatible(bundle):
                    bundle.setdefault("model_version", version)
                    return bundle, False
                # 特征版本不一致：无论显式指定还是自动解析，都回退当前缓存并触发重训，
                # 避免升级特征体系后线上直接不可用（注册表由重训后的 _register_version 纠正）
    path = cache_path(name, platform)
    if os.path.exists(path):
        bundle = None
        try:
            bundle = joblib.load(path)
        except Exception:
            bundle = None
        if bundle_compatible(bundle):
            return bundle, False
        # 旧版本 / 特征不一致 / 文件损坏：静默作废并重训，避免用错模型作答
        try:
            os.remove(path)
        except OSError:
            pass
    # 训练需跨进程互斥：两个请求同时进来只训练一次，另一个拿到锁后直接加载新缓存
    with _file_lock(path + ".lock"):
        if os.path.exists(path):
            try:
                bundle = joblib.load(path)
                if bundle_compatible(bundle):
                    return bundle, False
            except Exception:
                pass
        train_and_cache(name, platform)
    return joblib.load(path), True


def predict(name, category, fans, hour, weekday, month, version=None):
    bundle, trained_now = load_or_train(name, version=version)
    model, meta = bundle["model"], bundle["meta"]
    row = pd.DataFrame([{
        "video_category": str(category),
        "hour_bucket": _hour_bucket(hour),
        "author_fans_log": np.log1p(max(float(fans), 0.0)),
        "publish_hour": float(hour),
        "publish_weekday": float(weekday),
        "publish_month": float(month),
        "is_weekend": 1 if int(weekday) in (5, 6) else 0,
    }])
    X = _encode_frame(row, meta["cat_maps"], meta["cat_modes"])
    pred_log = float(model.predict(X)[0])
    return pred_log, float(np.expm1(pred_log)), trained_now, bundle


# 与 grading 模块一致的热度分级阈值（K-Means k=3）
GRADE_THRESHOLDS = (684.0, 15661.0)


def grade_of(heat):
    """按分级阈值给出热度等级名称。"""
    if heat < GRADE_THRESHOLDS[0]:
        return "低热度"
    if heat < GRADE_THRESHOLDS[1]:
        return "中热度"
    return "高热度"


def predict_batch(name, items, version=None):
    """
    批量预测：一次加载模型，对多条视频先验特征做预测。
    items 为 dict 列表，每项字段：category / fans / hour / weekday / month。
    """
    bundle, trained_now = load_or_train(name, version=version)
    model, meta = bundle["model"], bundle["meta"]

    rows = []
    for it in items:
        hour = int(it.get("hour", 20))
        weekday = int(it.get("weekday", 5))
        rows.append({
            "video_category": str(it.get("category") or "美食"),
            "hour_bucket": _hour_bucket(hour),
            "author_fans_log": float(np.log1p(max(float(it.get("fans") or 0), 0.0))),
            "publish_hour": float(hour),
            "publish_weekday": float(weekday),
            "publish_month": float(it.get("month", 6)),
            "is_weekend": 1 if weekday in (5, 6) else 0,
        })
    X = _encode_frame(pd.DataFrame(rows), meta["cat_maps"], meta["cat_modes"])
    preds_log = np.asarray(model.predict(X), dtype=float).ravel()

    results = []
    for it, p in zip(items, preds_log):
        heat = float(np.expm1(p))
        results.append({
            "video_category": str(it.get("category") or "美食"),
            "author_fans": float(it.get("fans") or 0),
            "prediction": heat,
            "prediction_log": float(p),
            "grade": grade_of(heat),
        })
    return results, trained_now, bundle


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main():
    model_name = None
    try:
        parser = _Parser(prog="predict_api.py")
        parser.add_argument("--model", default="lgbm", choices=MODELS)
        parser.add_argument("--category", default="美食", help="视频类别，如 美食/音乐/旅行")
        parser.add_argument("--fans", type=float, default=1000.0, help="作者粉丝数")
        parser.add_argument("--hour", type=int, default=20, help="发布小时 0-23")
        parser.add_argument("--weekday", type=int, default=5, help="发布星期 0-6（0=周一）")
        parser.add_argument("--month", type=int, default=6, help="发布月份 1-12")
        parser.add_argument("--train", action="store_true", help="仅训练并缓存模型后退出")
        parser.add_argument("--batch", default=None,
                            help="批量预测：输入 JSON 文件路径（数组，每项含 category/fans/hour/weekday/month）")
        parser.add_argument("--metrics", action="store_true",
                            help="输出各已缓存模型的评估指标（多模型对照）")
        parser.add_argument("--version", default=None,
                            help="指定模型版本（如 v3-20261107_120000_123456）；缺省使用注册表线上的可加载版本")
        args = parser.parse_args()

        # 中文类别参数在 Java(JDK17/中文Windows) 的 ProcessBuilder argv 中会被按 GBK 破坏，
        # 故 Java 侧对类别做 URL 编码（纯 ASCII 传输），此处解码；
        # 手动命令行直接输入中文（不含 %）时原样使用。
        category = unquote_plus(args.category) if "%" in args.category else args.category

        model_name = args.model
        if args.metrics:
            import joblib
            models = []
            for m in MODELS:
                p = cache_path(m)
                if os.path.exists(p):
                    try:
                        b = joblib.load(p)
                    except Exception:
                        b = None
                    if not bundle_compatible(b):
                        # 版本不符的旧缓存不计入对照表，等首次调用时自动重训
                        models.append({"model": m, "trained": False, "stale": True})
                        continue
                    item = {"model": m, "trained": True}
                    item.update(b.get("metrics") or {})
                    item["r2_raw"] = (b.get("metrics_raw") or {}).get("r2")
                    item["size_mb"] = round(os.path.getsize(p) / 1024.0 / 1024.0, 2)
                    models.append(item)
                else:
                    models.append({"model": m, "trained": False})
            models.sort(key=lambda x: -(x.get("r2") if x.get("r2") is not None else -1))
            print(json.dumps({"mode": "metrics", "models": models}, ensure_ascii=False))
            sys.exit(0)
        if args.batch:
            with open(args.batch, encoding="utf-8") as f:
                items = json.load(f)
            results, trained_now, bundle = predict_batch(model_name, items, version=args.version)
            print(json.dumps({
                "mode": "batch", "model": model_name, "count": len(results),
                "trained_now": trained_now, "results": results,
                "model_version": bundle.get("model_version"),
                "metrics": bundle["metrics"], "metrics_raw": bundle.get("metrics_raw"),
            }, ensure_ascii=False))
            sys.exit(0)
        if args.train:
            met_log, met_raw, version = train_and_cache(model_name)
            print(json.dumps({
                "model": model_name, "trained": True,
                "model_version": version,
                "cache_file": cache_path(model_name),
                "metrics": met_log, "metrics_raw": met_raw,
            }, ensure_ascii=False))
            sys.exit(0)

        pred_log, pred, trained_now, bundle = predict(
            model_name, category, args.fans, args.hour, args.weekday, args.month, version=args.version)
        print(json.dumps({
            "model": model_name,
            "model_version": bundle.get("model_version"),
            "prediction": pred,
            "prediction_log": pred_log,
            "trained_now": trained_now,
            "cache_file": cache_path(model_name),
            "metrics": bundle["metrics"],
            "metrics_raw": bundle.get("metrics_raw"),
        }, ensure_ascii=False))
        sys.exit(0)
    except BaseException as exc:  # noqa: BLE001 - 统一转成契约 JSON
        if isinstance(exc, SystemExit) and exc.code == 0:
            raise
        print(json.dumps({
            "model": model_name, "error": str(exc), "trace": traceback.format_exc(),
            "trace_id": os.environ.get("TRACE_ID"),
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    _stdout_reconfigure()
    main()
