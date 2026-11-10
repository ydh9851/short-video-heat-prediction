# -*- coding: utf-8 -*-
"""
rehearsal.py —— 上线预演（Release Rehearsal）
============================================
在真正切换线上模型版本之前，用**真实数据采样**让「候选版本」与「当前线上版本」
并行打分，量化两者的输出差异，给出是否允许上线的结论。

为什么不直接看离线指标（R²/MAE）：
    离线指标相同分布下计算，无法暴露「换版本后线上输出跳变」的风险；
    预演关心的是**与当前线上行为的偏差**，即使候选模型离线指标更好，
    输出大面积跳变也意味着下游（缓存、归因、阈值分级、用户预期）全部要重估。

判定阈值（与影子模式互补：影子用真实流量，预演用历史采样）：
    meanAbsDiffPct <= 10%  且  pearsonCorr(log) >= 0.95  且  top10%Overlap >= 0.7

用法:
    python rehearsal.py --model lgbm --version v4-20261107_120000_123456 [--sample 300] [--seed 42]

成功输出（单行 JSON）:
    {"mode":"rehearsal","model":"lgbm","activeVersion":"...","candidateVersion":"...",
     "sampleSize":300,"meanAbsDiffPct":3.2,...,"passed":true,"worstCases":[...]}

失败输出（单行 JSON，退出码非 0）:
    {"error":"...","trace":"..."}
"""

import argparse
import json
import os
import sys
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import predict_api as pa  # noqa: E402

# 预演采样基准平台：与漂移检测一致，以抖音（训练数据主平台）为参照
REFERENCE_PLATFORM = "douyin"

# 通过阈值：任一指标不达标即不允许直接上线（可人工强制）
THRESHOLDS = {"meanAbsDiffPct": 10.0, "pearsonCorr": 0.95, "top10Overlap": 0.7}


def _load_sample(n, seed):
    """从参照平台清洗数据采样真实先验特征，避免人造数据分布偏离线上。"""
    path = os.path.join(pa.PROCESSED_DIR, "%s_clean.csv" % REFERENCE_PLATFORM)
    df = pd.read_csv(path)
    n = min(n, len(df))
    sample = df.sample(n=n, random_state=seed)
    items = []
    for _, row in sample.iterrows():
        items.append({
            "category": str(row.get("video_category") or "美食"),
            "fans": float(row.get("author_fans") or 0),
            "hour": int(row.get("publish_hour") or 20),
            "weekday": int(row.get("publish_weekday") or 5),
            "month": int(row.get("publish_month") or 6),
        })
    return items


def run(model, candidate, n=300, seed=42):
    active = pa.active_version(model)
    if not active:
        raise ValueError("模型 %s 当前没有可加载的线上版本，请先同步注册表" % model)
    if candidate == active:
        raise ValueError("候选版本与线上版本相同（%s），无需预演" % active)

    items = _load_sample(n, seed)
    res_active, _, bundle_a = pa.predict_batch(model, items, version=active)
    res_candidate, _, bundle_c = pa.predict_batch(model, items, version=candidate)

    # 防"假预演"：候选版本若因归档缺失 / 特征体系不一致被静默回退到当前缓存，
    # 比较的就变成"自己比自己"（偏差恒为 0），结论毫无意义，必须显式报错
    loaded_a = str(bundle_a.get("model_version") or "")
    loaded_c = str(bundle_c.get("model_version") or "")
    if loaded_a != str(active):
        raise ValueError("线上版本 %s 未能真实加载（实际加载 %s），请先同步注册表" % (active, loaded_a))
    if loaded_c != str(candidate):
        raise ValueError(
            "候选版本 %s 未能真实加载（特征体系不一致或归档损坏，实际加载 %s），请重新训练后再预演"
            % (candidate, loaded_c))

    pa_arr = np.array([r["prediction"] for r in res_active], dtype=float)
    pc_arr = np.array([r["prediction"] for r in res_candidate], dtype=float)

    # 相对偏差：以线上预测为基准；线上为 0 的样本按绝对差处理（避免除零）
    denom = np.where(pa_arr == 0, 1.0, np.abs(pa_arr))
    diff_pct = (pc_arr - pa_arr) / denom * 100.0
    abs_diff = np.abs(diff_pct)

    # 相关性用 log1p 尺度：热度是重尾分布，原始尺度的相关系数会被超高热度样本主导
    corr = float(np.corrcoef(np.log1p(np.maximum(pa_arr, 0)),
                             np.log1p(np.maximum(pc_arr, 0)))[0, 1])

    # 头部命中集合重合度：运营最关心「哪些视频会爆」，头部名单不能大换血
    k = max(1, len(items) // 10)
    top_active = set(np.argsort(-pa_arr)[:k].tolist())
    top_candidate = set(np.argsort(-pc_arr)[:k].tolist())
    overlap = len(top_active & top_candidate) / float(k)

    mean_abs = float(abs_diff.mean())
    passed = (mean_abs <= THRESHOLDS["meanAbsDiffPct"]
              and corr >= THRESHOLDS["pearsonCorr"]
              and overlap >= THRESHOLDS["top10Overlap"])

    # 偏差最大的 5 个样本：预演未通过时供人工判断是个案还是系统性偏移
    worst_idx = np.argsort(-abs_diff)[:5]
    worst_cases = [{
        "input": items[int(i)],
        "activePrediction": round(float(pa_arr[int(i)]), 2),
        "candidatePrediction": round(float(pc_arr[int(i)]), 2),
        "diffPct": round(float(diff_pct[int(i)]), 2),
    } for i in worst_idx]

    return {
        "mode": "rehearsal",
        "model": model,
        "activeVersion": active,
        "candidateVersion": candidate,
        "sampleSize": len(items),
        "meanAbsDiffPct": round(mean_abs, 3),
        "p50AbsDiffPct": round(float(np.percentile(abs_diff, 50)), 3),
        "p90AbsDiffPct": round(float(np.percentile(abs_diff, 90)), 3),
        "maxAbsDiffPct": round(float(abs_diff.max()), 3),
        "pearsonCorr": round(corr, 4),
        "top10Overlap": round(overlap, 4),
        "passed": bool(passed),
        "thresholds": THRESHOLDS,
        "worstCases": worst_cases,
    }


def _stdout_reconfigure():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    try:
        parser = argparse.ArgumentParser(prog="rehearsal.py")
        parser.add_argument("--model", required=True, choices=pa.MODELS)
        parser.add_argument("--version", required=True, help="候选版本号")
        parser.add_argument("--sample", type=int, default=300, help="采样条数（默认 300）")
        parser.add_argument("--seed", type=int, default=42, help="采样随机种子（结果可复现）")
        args = parser.parse_args()
        out = run(args.model, args.version, n=args.sample, seed=args.seed)
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(0)
    except BaseException as exc:  # noqa: BLE001
        if isinstance(exc, SystemExit) and exc.code == 0:
            raise
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc(),
                          "trace_id": os.environ.get("TRACE_ID")}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    _stdout_reconfigure()
    main()
