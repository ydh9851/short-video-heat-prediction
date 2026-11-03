#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""交互式 what-if：扫描某个参数的取值，给出预测值曲线与最优建议。

运营问「这条视频改成晚上 8 点发、或者换到美食赛道，热度能高多少？」
本脚本在同一个已训练模型上扫描该参数的候选取值，一次调用返回完整序列
（预测值、热度等级、相对当前值的增益），前端直接画曲线。

与反事实分析（attribution/refutation.py）的区别：
    - 反事实：给出「把某个特征改到某个取值」的推荐与稳健性检验；
    - what-if：把「改这个特征的全部取值」一次性列出，用于交互式探索。

用法：
    python what_if.py --dimension publishHour --fans 50000 --category 美食
    python what_if.py --dimension videoCategory --fans 50000 --hour 20
"""
import argparse
import json
import os
import sys
import traceback

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import predict_api as P  # noqa: E402

CATEGORIES = ["美食", "游戏", "知识", "运动", "音乐", "影视", "生活", "科技", "动物", "汽车"]


def _row(category, fans, hour, weekday, month):
    return {
        "video_category": str(category),
        "hour_bucket": P._hour_bucket(hour),
        "author_fans_log": np.log1p(max(float(fans or 0.0), 0.0)),
        "publish_hour": float(hour),
        "publish_weekday": float(weekday),
        "publish_month": float(month),
        "is_weekend": 1 if int(weekday) in (5, 6) else 0,
    }


def _grade(heat):
    try:
        return P.grade_of(heat)
    except Exception:
        return "-"


def _candidates(dimension, category, fans, hour, weekday, month):
    """返回该维度上要扫描的 (取值, 展示标签) 列表。"""
    if dimension == "publishHour":
        return list(range(24)), ["%d:00" % v for v in range(24)]
    if dimension == "publishWeekday":
        return list(range(7)), ["周%d" % (v + 1) for v in range(7)]
    if dimension == "publishMonth":
        return list(range(1, 13)), ["%d 月" % v for v in range(1, 13)]
    return CATEGORIES, list(CATEGORIES)


def run(dimension="publishHour", category="美食", fans=50000,
        hour=20, weekday=5, month=6, model_name="lgbm"):
    X_train, y_train, _X_test, _y_test, meta = P._prepare(platform=None)
    if len(y_train) == 0:
        return {"mode": "what-if", "error": "当前平台没有训练数据"}

    mdl = P.build_model(model_name, X_train, y_train)
    values, labels = _candidates(dimension, category, fans, hour, weekday, month)

    rows = []
    for v in values:
        rows.append(_row(
            v if dimension == "videoCategory" else category,
            fans,
            v if dimension == "publishHour" else hour,
            v if dimension == "publishWeekday" else weekday,
            v if dimension == "publishMonth" else month))
    frame = pd.DataFrame(rows)
    X = P._encode_frame(frame, meta["cat_maps"], meta["cat_modes"])
    heats = np.expm1(mdl.predict(X))

    base_X = P._encode_frame(pd.DataFrame([_row(category, fans, hour, weekday, month)]),
                             meta["cat_maps"], meta["cat_modes"])
    baseline = float(np.expm1(mdl.predict(base_X)[0]))

    candidates = []
    for v, label, heat in zip(values, labels, heats):
        heat = float(heat)
        candidates.append({
            "value": v,
            "label": label,
            "prediction": heat,
            "grade": _grade(heat),
            "gain": heat - baseline,
            "gain_pct": (heat - baseline) / baseline if baseline else 0.0,
        })

    best = max(candidates, key=lambda c: c["prediction"])
    current_value = {"publishHour": hour, "publishWeekday": weekday,
                     "publishMonth": month, "videoCategory": category}.get(dimension)
    current_label = None
    for c in candidates:
        if c["value"] == current_value:
            current_label = c["label"]

    return {
        "mode": "what-if",
        "model": model_name,
        "dimension": dimension,
        "current_value": current_value,
        "current_label": current_label,
        "baseline": baseline,
        "baseline_grade": _grade(baseline),
        "candidates": candidates,
        "best": {"value": best["value"], "label": best["label"],
                 "prediction": best["prediction"], "gain": best["gain"],
                 "gain_pct": best["gain_pct"]},
        "note": "同一模型上扫描该维度的全部候选取值；gain 为相对当前取值的绝对增量。"
                "该结果是模型在输入空间上的响应，并非因果效应——因果解读需结合反事实稳健性检验。",
    }


def main():
    ap = argparse.ArgumentParser(description="交互式 what-if：扫描参数取值给出热度响应曲线")
    ap.add_argument("--dimension", default="publishHour",
                    choices=["publishHour", "publishWeekday", "publishMonth", "videoCategory"])
    ap.add_argument("--category", default="美食")
    ap.add_argument("--fans", type=float, default=50000.0)
    ap.add_argument("--hour", type=int, default=20)
    ap.add_argument("--weekday", type=int, default=5)
    ap.add_argument("--month", type=int, default=6)
    ap.add_argument("--model", default="lgbm")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        result = run(dimension=args.dimension, category=args.category, fans=args.fans,
                     hour=args.hour, weekday=args.weekday, month=args.month,
                     model_name=args.model)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc(),
                          "trace_id": os.environ.get("TRACE_ID")}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
