#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""目标口径对照实验：加权热度 vs 播放量。

同一份数据、同一套特征、同一个 LightGBM、同一测试集，只改变预测目标，量化两件事：
1. 拟合难度差异（R2 / RMSE / 相对误差）；
2. 归因结论差异（各特征贡献排名是否改变）——若改变，则"归因结论依赖于目标口径"。
"""
import argparse
import json
import os
import sys
import traceback

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.join(os.path.dirname(HERE), "prediction")
if PRED_DIR not in sys.path:
    sys.path.insert(0, PRED_DIR)
import predict_api as P  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
TRAIN_CSV = os.path.join(ROOT, "data", "processed", "train_clean.csv")
TEST_CSV = os.path.join(ROOT, "data", "processed", "test_clean.csv")


def load_frames():
    train = pd.read_csv(TRAIN_CSV)
    test = pd.read_csv(TEST_CSV)
    maps, modes = P._fit_cat_maps(train)
    return train, test, maps, modes


def build_xy(df, maps, modes, target):
    X = P._encode_frame(df, maps, modes)
    column = "heat" if target == "heat" else "play_cnt"
    raw = df[column].astype(float).values
    return X, np.log1p(raw), raw


def fit_and_eval(X_train, y_train_log, X_test, y_test_log, y_test_raw, model_name="lgbm"):
    model = P.build_model(model_name, X_train, y_train_log)
    pred_log = model.predict(X_test)
    pred_raw = np.expm1(pred_log)
    ss_res = float(np.sum((y_test_log - pred_log) ** 2))
    ss_tot = float(np.sum((y_test_log - np.mean(y_test_log)) ** 2))
    rel = np.abs(pred_raw - y_test_raw) / np.maximum(np.abs(y_test_raw), 1.0)
    return model, {
        "r2": 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
        "rmse": float(np.sqrt(np.mean((y_test_log - pred_log) ** 2))),
        "mae": float(np.mean(np.abs(y_test_log - pred_log))),
        "rel_err_p50": float(np.median(rel)),
    }


def top_features(model, X_test, names, top_k=6):
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        sample = X_test[:400] if len(X_test) > 400 else X_test
        values = explainer.shap_values(sample)
        if hasattr(values, "ndim") and values.ndim == 3:
            values = values[:, :, 0]
        mean_abs = np.abs(values).mean(axis=0)
    except Exception:
        imp = getattr(model, "feature_importances_", None)
        if imp is None:
            booster = getattr(model, "booster_", None)
            imp = booster.feature_importance("gain") if booster is not None else None
        if imp is None:
            return []
        mean_abs = np.asarray(imp, dtype=float)
    order = np.argsort(-mean_abs)[:top_k]
    total = float(np.sum(mean_abs)) or 1.0
    return [{"feature": names[i] if i < len(names) else "f%d" % i,
             "share": float(mean_abs[i] / total)} for i in order]


def run():
    train, test, maps, modes = load_frames()
    names = list(P.FEATURE_NAMES)

    X_train, y_train_heat, _ = build_xy(train, maps, modes, "heat")
    X_test, y_test_heat_log, y_test_heat_raw = build_xy(test, maps, modes, "heat")
    _, y_train_play, _ = build_xy(train, maps, modes, "play")
    _, y_test_play_log, y_test_play_raw = build_xy(test, maps, modes, "play")

    specs = [
        ("heat", "加权热度（播放 + 3×点赞 + 5×评论 + 8×转发）", y_train_heat, y_test_heat_log, y_test_heat_raw),
        ("play", "播放量（log1p，仅观看规模）", y_train_play, y_test_play_log, y_test_play_raw),
    ]
    rows = []
    feature_lists = {}
    for key, desc, ytr, yte_log, yte_raw in specs:
        model, metrics = fit_and_eval(X_train, ytr, X_test, yte_log, yte_raw)
        feats = top_features(model, X_test, names)
        feature_lists[key] = feats
        row = {"target": key, "target_desc": desc}
        row.update(metrics)
        row["top_features"] = feats
        rows.append(row)

    corr = float(np.corrcoef(y_test_heat_log, y_test_play_log)[0, 1])
    rank_heat = {f["feature"]: i + 1 for i, f in enumerate(feature_lists.get("heat", []))}
    rank_play = {f["feature"]: i + 1 for i, f in enumerate(feature_lists.get("play", []))}
    shifts = [{"feature": n, "rank_heat": rank_heat[n], "rank_play": rank_play[n],
               "delta": rank_play[n] - rank_heat[n]}
              for n in sorted(set(rank_heat) & set(rank_play))]
    shifts.sort(key=lambda x: -abs(x["delta"]))

    return {
        "mode": "target-compare",
        "platform": "douyin",
        "rows": rows,
        "target_corr": corr,
        "feature_shift": shifts,
        "note": "同一份数据、同一套 7 维特征、同一个 LightGBM、同一测试集，只改变预测目标；"
                "delta 为该特征在两种口径下的贡献排名位移",
    }


def main():
    ap = argparse.ArgumentParser(description="目标口径对照实验：加权热度 vs 播放量")
    ap.add_argument("--mode", default="target-compare", choices=["target-compare"])
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        print(json.dumps(run(), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc(),
                          "trace_id": os.environ.get("TRACE_ID")}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
