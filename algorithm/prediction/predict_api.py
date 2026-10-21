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
import json
import os
import sys
import traceback
import warnings
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

CAT_FEATURES = ["video_category", "hour_bucket"]
NUM_FEATURES = ["author_fans_log", "publish_hour", "publish_weekday", "publish_month", "is_weekend"]
FEATURE_NAMES = NUM_FEATURES + CAT_FEATURES
CAT_IDX = [FEATURE_NAMES.index(c) for c in CAT_FEATURES]
TARGET_LOG = "heat_log"

MODELS = ["lr", "knn", "svm", "dt", "rf", "lgbm", "xgb"]


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
    """基于训练集为每个类别特征建立 {取值: 编码} 映射（未见取值回退到众数）+ 众数类别。"""
    maps, modes = {}, {}
    for col in CAT_FEATURES:
        vals = train[col].astype(str)
        mode_val = vals.mode()[0]
        uniq = list(dict.fromkeys(vals.tolist()))
        if mode_val in uniq:
            uniq.remove(mode_val)
        maps[col] = {v: i for i, v in enumerate(uniq)}
        modes[col] = mode_val
    return maps, modes


def _encode_frame(df, maps, modes):
    out = df.copy()
    for col in CAT_FEATURES:
        m, mode_val = maps[col], modes[col]
        out[col] = out[col].astype(str).map(lambda v: m.get(v, len(m)))  # 未知 -> 新编码
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


def train_and_cache(name, platform=None):
    import joblib
    X_train, y_train, X_test, y_test, meta = _prepare(platform=platform)
    model = _fit(name, X_train, y_train)
    metrics_log, metrics_raw = calc_metrics(model, X_test, y_test)
    os.makedirs(CACHE_DIR, exist_ok=True)
    bundle = {
        "model": model, "metrics": metrics_log, "metrics_raw": metrics_raw,
        "feature_names": FEATURE_NAMES, "meta": meta,
    }
    joblib.dump(bundle, cache_path(name, platform), compress=3)
    return metrics_log, metrics_raw


def load_or_train(name, platform=None):
    import joblib
    path = cache_path(name, platform)
    if os.path.exists(path):
        return joblib.load(path), False
    train_and_cache(name, platform)
    return joblib.load(path), True


def predict(name, category, fans, hour, weekday, month):
    bundle, trained_now = load_or_train(name)
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
    return pred_log, float(np.expm1(pred_log)), trained_now


# 与 grading 模块一致的热度分级阈值（K-Means k=3）
GRADE_THRESHOLDS = (684.0, 15661.0)


def grade_of(heat):
    """按分级阈值给出热度等级名称。"""
    if heat < GRADE_THRESHOLDS[0]:
        return "低热度"
    if heat < GRADE_THRESHOLDS[1]:
        return "中热度"
    return "高热度"


def predict_batch(name, items):
    """
    批量预测：一次加载模型，对多条视频先验特征做预测。
    items 为 dict 列表，每项字段：category / fans / hour / weekday / month。
    """
    bundle, trained_now = load_or_train(name)
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
                    b = joblib.load(p)
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
            results, trained_now, bundle = predict_batch(model_name, items)
            print(json.dumps({
                "mode": "batch", "model": model_name, "count": len(results),
                "trained_now": trained_now, "results": results,
                "metrics": bundle["metrics"], "metrics_raw": bundle.get("metrics_raw"),
            }, ensure_ascii=False))
            sys.exit(0)
        if args.train:
            met_log, met_raw = train_and_cache(model_name)
            print(json.dumps({
                "model": model_name, "trained": True,
                "cache_file": cache_path(model_name),
                "metrics": met_log, "metrics_raw": met_raw,
            }, ensure_ascii=False))
            sys.exit(0)

        pred_log, pred, trained_now = predict(
            model_name, category, args.fans, args.hour, args.weekday, args.month)
        bundle = load_or_train(model_name)[0]
        print(json.dumps({
            "model": model_name,
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
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    _stdout_reconfigure()
    main()
