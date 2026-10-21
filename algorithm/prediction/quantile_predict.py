# -*- coding: utf-8 -*-
"""
quantile_predict.py —— 热度预测区间（LightGBM 分位数回归）
==========================================================
常规回归只给出一个点估计（P50）。业务上更需要「最坏 / 中性 / 最好」三档区间，
因此本模块用 LightGBM 的 quantile 目标分别训练 P10 / P50 / P90 三个模型：

    * P10 —— 保守估计：大概率不会低于此值（可用于投放预算下限）
    * P50 —— 中位估计：最可能的水平
    * P90 —— 乐观估计：运气好时可能达到的上限

与 predict_api.py 完全同源（同一套特征工程与类别编码），保证与点预测口径一致。
模型按 alpha 缓存到 model_cache/quantile_lgbm_<alpha>.joblib，首次训练后秒级加载。

用法:
    python quantile_predict.py --train                                   # 预热三个分位模型
    python quantile_predict.py --category 美食 --fans 50000 --hour 20 --weekday 5 --month 6

输出（单行 JSON）:
    {"mode":"quantile","interval":{"p10":...,"p50":...,"p90":...},
     "width":...,"ratio":...,"grade":"中热度",...}
"""

import argparse
import json
import os
import sys
import traceback
import warnings

warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))          # .../algorithm/prediction
ALGO_DIR = os.path.dirname(BASE)
SYSTEM_ROOT = os.path.dirname(ALGO_DIR)
PRED_DIR = BASE
sys.path.insert(0, PRED_DIR)

import predict_api as P  # noqa: E402

CACHE_DIR = os.path.join(BASE, "model_cache")
ALPHAS = (0.1, 0.5, 0.9)
ROUNDS = 500


def _stdout_reconfigure():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def cache_path(alpha):
    return os.path.join(CACHE_DIR, "quantile_lgbm_p%02d.joblib" % int(round(alpha * 100)))


def train_quantile(alpha):
    """训练单个分位模型并缓存。"""
    import joblib
    import lightgbm as lgb

    X_train, y_train, X_test, y_test, meta = P._prepare()
    params = {
        "objective": "quantile",
        "alpha": float(alpha),
        "metric": "quantile",
        "boosting_type": "gbdt",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
        "seed": 42,
    }
    ds = lgb.Dataset(X_train, label=y_train, categorical_feature=P.CAT_IDX, free_raw_data=False)
    model = lgb.train(params, ds, num_boost_round=ROUNDS)

    # 区间覆盖率统一在主流程 coverage_report() 中评估（需要三个分位模型同时在场）
    os.makedirs(CACHE_DIR, exist_ok=True)
    joblib.dump({"model": model, "alpha": float(alpha), "meta": meta,
                 "feature_names": P.FEATURE_NAMES},
                cache_path(alpha), compress=3)
    return model, meta


def load_or_train(alpha):
    import joblib
    p = cache_path(alpha)
    if os.path.exists(p):
        b = joblib.load(p)
        return b, False
    train_quantile(alpha)
    b = joblib.load(p)
    return b, True


def _build_row(category, fans, hour, weekday, month):
    import pandas as pd
    return pd.DataFrame([{
        "video_category": str(category),
        "hour_bucket": P._hour_bucket(hour),
        "author_fans_log": float(np.log1p(max(float(fans), 0.0))),
        "publish_hour": float(hour),
        "publish_weekday": float(weekday),
        "publish_month": float(month),
        "is_weekend": 1 if int(weekday) in (5, 6) else 0,
    }])


def predict_interval(category, fans, hour, weekday, month):
    row = _build_row(category, fans, hour, weekday, month)
    out = {}
    trained_now = False
    meta = None
    for a in ALPHAS:
        bundle, tn = load_or_train(a)
        trained_now = trained_now or tn
        meta = bundle["meta"]
        X = P._encode_frame(row, meta["cat_maps"], meta["cat_modes"])
        out[int(round(a * 100))] = float(np.expm1(bundle["model"].predict(X)[0]))

    p10, p50, p90 = out[10], out[50], out[90]
    # 分位模型独立训练可能出现轻微交叉（P10>P50），做单调化修正
    p10, p50, p90 = min(p10, p50, p90), sorted([p10, p50, p90])[1], max(p10, p50, p90)
    width = p90 - p10
    return {
        "mode": "quantile",
        "interval": {"p10": p10, "p50": p50, "p90": p90},
        "width": width,
        "ratio": (width / p50) if p50 else None,
        "grade": P.grade_of(p50),
        "trained_now": trained_now,
    }


def coverage_report():
    """区间覆盖率：在测试集上统计真实热度落入 [P10, P90] 的比例（理想 ≈ 80%）。"""
    import joblib
    X_train, y_train, X_test, y_test, meta = P._prepare()
    if X_test is None or not len(X_test):
        return None
    preds = {}
    for a in ALPHAS:
        p = cache_path(a)
        if not os.path.exists(p):
            return None
        preds[a] = np.expm1(joblib.load(p)["model"].predict(X_test))
    y_raw = np.expm1(y_test)
    inside = (y_raw >= preds[0.1]) & (y_raw <= preds[0.9])
    return {
        "coverage": float(inside.mean()),
        "n": int(len(y_raw)),
        "mean_width": float(np.mean(preds[0.9] - preds[0.1])),
        "median_width": float(np.median(preds[0.9] - preds[0.1])),
    }


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main():
    try:
        parser = _Parser(prog="quantile_predict.py")
        parser.add_argument("--category", default="美食")
        parser.add_argument("--fans", type=float, default=1000.0)
        parser.add_argument("--hour", type=int, default=20)
        parser.add_argument("--weekday", type=int, default=5)
        parser.add_argument("--month", type=int, default=6)
        parser.add_argument("--train", action="store_true", help="仅训练并缓存三个分位模型")
        parser.add_argument("--coverage", action="store_true", help="输出测试集区间覆盖率")
        args = parser.parse_args()

        from urllib.parse import unquote_plus
        category = unquote_plus(args.category) if "%" in args.category else args.category

        if args.train:
            for a in ALPHAS:
                train_quantile(a)
            print(json.dumps({"mode": "quantile", "trained": True,
                              "alphas": list(ALPHAS)}, ensure_ascii=False))
            sys.exit(0)

        if args.coverage:
            rep = coverage_report()
            print(json.dumps({"mode": "quantile-coverage", **(rep or {})}, ensure_ascii=False))
            sys.exit(0)

        result = predict_interval(category, args.fans, args.hour, args.weekday, args.month)
        result["coverage_report"] = coverage_report()
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)
    except BaseException as exc:  # noqa: BLE001
        if isinstance(exc, SystemExit) and exc.code == 0:
            raise
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc()}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    _stdout_reconfigure()
    main()
