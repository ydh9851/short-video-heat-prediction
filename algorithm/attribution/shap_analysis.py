# -*- coding: utf-8 -*-
"""
shap_analysis.py —— 短视频热度归因分析（SHAP 可解释性）
========================================================
本模块是本系统的核心创新点：在「预测热度」之外，回答「为什么这条视频会火 / 不火」。

复用 prediction/predict_api.py 的特征编码与模型缓存，保证归因与预测同源同口径。
SHAP 值均在 **log1p 空间** 上计算（与模型训练目标一致），解读时按对数贡献理解。

三种模式（CLI，供 Java 后端 ProcessBuilder 调用；输出单行 JSON）：
    --mode global   全局特征重要性：LightGBM 增益重要性 + SHAP 平均绝对贡献
                    -> figures/global_importance.png / shap_summary.png
    --mode explain  单样本归因：给定一条视频的先验特征，输出各特征对预测值的
                    推高/拉低贡献（瀑布图 figures/shap_waterfall.png）+ 运营建议
    --mode pdp      部分依赖图：某特征（如作者粉丝数 / 发布小时）变化如何影响平均热度
                    -> figures/pdp_<feature>.png

用法示例：
    python shap_analysis.py --mode global
    python shap_analysis.py --mode explain --category 美食 --fans 50000 --hour 20 --weekday 5 --month 3
    python shap_analysis.py --mode pdp --feature author_fans_log
"""

import argparse
import json
import os
import sys
import traceback
import warnings

warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# 中文字体（Windows 自带），避免图内中文标题乱码
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.abspath(__file__))            # .../algorithm/attribution
ALGO_DIR = os.path.dirname(BASE)                             # .../algorithm
SYSTEM_ROOT = os.path.dirname(ALGO_DIR)
PRED_DIR = os.path.join(ALGO_DIR, "prediction")
FIG_DIR = os.path.join(BASE, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

# 复用预测模块的特征定义与编码逻辑（单一事实来源，避免两处不一致）
sys.path.insert(0, PRED_DIR)
import predict_api as P  # noqa: E402

FEATURE_CN = {
    "author_fans_log": "作者粉丝数(log)",
    "publish_hour": "发布小时",
    "publish_weekday": "发布星期",
    "publish_month": "发布月份",
    "is_weekend": "是否周末",
    "video_category": "视频类别",
    "hour_bucket": "发布时段",
    "play_cnt": "播放量",
}

# 单样本归因最多展示的特征数（瀑布图可读性）
TOP_K = 7
GLOBAL_SAMPLE = 2000   # 全局 SHAP 采样行数（控制耗时）


def _stdout_reconfigure():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _get_model():
    """加载（必要时训练）LightGBM 缓存模型。"""
    bundle, _ = P.load_or_train("lgbm")
    return bundle


def _tree_shap(explainer, X):
    """统一取 SHAP 值矩阵（不同版本 / 回归多输出的返回形状差异）。"""
    sv = explainer.shap_values(X)
    sv = np.asarray(sv, dtype=float)
    if sv.ndim == 3:            # (n, features, outputs) -> 取第一个输出
        sv = sv[:, :, 0]
    if sv.ndim == 1:            # 单样本
        sv = sv.reshape(1, -1)
    return sv


# --------------------------------------------------------------------------- #
# 运营建议规则（归因 -> 可执行建议），论文第 5 章"归因到决策"的落地
# --------------------------------------------------------------------------- #
def build_advice(row, contributions):
    """依据输入特征与 SHAP 贡献生成运营建议文本列表。"""
    advice = []
    pos = [c for c in contributions if c["shap"] > 0]
    neg = [c for c in contributions if c["shap"] < 0]

    # 1. 粉丝基数
    fans = row.get("author_fans", 0)
    if fans < 1000:
        advice.append("作者粉丝基数偏低（<1000），建议先通过矩阵号导流/合拍联动提升账号权重，"
                      "或选择更易破圈的垂类话题降低冷启动难度。")
    elif fans > 100000:
        advice.append("作者粉丝基数较高，具备自然流量托底，可将重心放在内容质量与完播率上。")

    # 2. 发布时段
    hour = int(row.get("publish_hour", -1))
    if 0 <= hour < 6:
        advice.append("发布时段处于凌晨（0-5点），大盘活跃度低，建议调整到晚间 18-23 点高峰时段发布。")
    elif 18 <= hour <= 23:
        advice.append("发布时段处于晚间高峰（18-23点），有利于冷启动期获得更高初始曝光，可保持。")
    else:
        advice.append("发布时段为常规时段，若数据表现一般，可尝试向晚间高峰迁移对比效果。")

    # 3. 周末效应
    if int(row.get("is_weekend", 0)) == 1:
        advice.append("周末发布，用户休闲时长更充裕，适合发布偏娱乐/长内容。")

    # 4. 类别
    advice.append(f"当前视频类别为「{row.get('video_category')}」，"
                  "可结合同类目高热视频的共性（选题/封面/前3秒钩子）做对标优化。")

    # 5. 由 SHAP 主导项给出的重点
    if pos:
        top = pos[0]
        advice.append(f"本条的预测热度主要由「{FEATURE_CN.get(top['feature'], top['feature'])}」"
                      f"正向拉动，建议在后续选题中继续强化该优势。")
    if neg:
        bottom = neg[0]
        advice.append(f"「{FEATURE_CN.get(bottom['feature'], bottom['feature'])}」"
                      f"是主要拖累项，是当前最值得优先改善的方向。")
    return advice


# --------------------------------------------------------------------------- #
# 三种模式
# --------------------------------------------------------------------------- #
def mode_global():
    import shap
    bundle = _get_model()
    model = bundle["model"]
    X_train, y_train, X_test, y_test, meta = P._prepare()

    n = min(GLOBAL_SAMPLE, len(X_train))
    X_smp = X_train.sample(n=n, random_state=42)
    explainer = shap.TreeExplainer(model)
    sv = _tree_shap(explainer, X_smp)

    # 1) SHAP 平均绝对贡献条形图
    mean_abs = np.abs(sv).mean(axis=0)
    order = np.argsort(mean_abs)[::-1]
    names = [FEATURE_CN.get(P.FEATURE_NAMES[i], P.FEATURE_NAMES[i]) for i in order]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(range(len(order)), mean_abs[order][::-1], color="#4C72B0")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(names[::-1])
    ax.set_xlabel("平均 |SHAP| 贡献（log 空间）")
    ax.set_title("全局特征重要性（SHAP）")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "global_importance.png"), dpi=130)
    plt.close(fig)

    # 2) SHAP summary（beeswarm）
    fig = plt.figure(figsize=(9, 6))
    shap.summary_plot(sv, X_smp, feature_names=[FEATURE_CN.get(f, f) for f in P.FEATURE_NAMES], show=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "shap_summary.png"), dpi=130)
    plt.close(fig)

    top = [{"feature": P.FEATURE_NAMES[i], "feature_cn": FEATURE_CN.get(P.FEATURE_NAMES[i], P.FEATURE_NAMES[i]),
            "importance": float(mean_abs[i])} for i in order]
    return {
        "mode": "global",
        "figures": ["global_importance.png", "shap_summary.png"],
        "top_features": top,
    }


def mode_explain(category, fans, hour, weekday, month):
    import shap
    bundle = _get_model()
    model = bundle["model"]
    meta = bundle["meta"]

    row = pd.DataFrame([{
        "video_category": str(category),
        "hour_bucket": P._hour_bucket(hour),
        "author_fans_log": float(np.log1p(max(float(fans), 0.0))),
        "publish_hour": float(hour),
        "publish_weekday": float(weekday),
        "publish_month": float(month),
        "is_weekend": 1 if int(weekday) in (5, 6) else 0,
    }])
    X = P._encode_frame(row, meta["cat_maps"], meta["cat_modes"])

    explainer = shap.TreeExplainer(model)
    sv = _tree_shap(explainer, X)[0]
    base = explainer.expected_value
    base = float(np.asarray(base).reshape(-1)[0])
    pred_log = float(model.predict(X)[0])

    contribs = []
    for i, f in enumerate(P.FEATURE_NAMES):
        contribs.append({
            "feature": f,
            "feature_cn": FEATURE_CN.get(f, f),
            "value": float(X.iloc[0, i]),
            "shap": float(sv[i]),
        })
    contribs.sort(key=lambda c: -abs(c["shap"]))
    top_contribs = contribs[:TOP_K]

    # 瀑布图（仅展示 Top-K，其余归入 other）
    fig = plt.figure(figsize=(9, 6))
    exp = shap.Explanation(
        values=np.array([c["shap"] for c in top_contribs]),
        base_values=base,
        data=np.array([c["value"] for c in top_contribs]),
        feature_names=[c["feature_cn"] for c in top_contribs],
    )
    shap.plots.waterfall(exp, show=False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "shap_waterfall.png"), dpi=130)
    plt.close(fig)

    advice = build_advice({**row.iloc[0].to_dict(), "video_category": str(category),
                           "author_fans": fans, "publish_hour": hour,
                           "is_weekend": 1 if int(weekday) in (5, 6) else 0}, contribs)
    return {
        "mode": "explain",
        "figure": "shap_waterfall.png",
        "base_value": base,
        "prediction_log": pred_log,
        "prediction": float(np.expm1(pred_log)),
        "contributions": top_contribs,
        "top_positive": [c for c in contribs if c["shap"] > 0][:3],
        "top_negative": [c for c in contribs if c["shap"] < 0][:3],
        "advice": advice,
    }


def mode_pdp(feature, grid_size=20):
    bundle = _get_model()
    model = bundle["model"]
    X_train, y_train, X_test, y_test, meta = P._prepare()

    if feature not in P.FEATURE_NAMES:
        raise ValueError("feature 仅支持: %s" % P.FEATURE_NAMES)

    n = min(GLOBAL_SAMPLE, len(X_train))
    X_smp = X_train.sample(n=n, random_state=42).copy()
    col = X_smp[feature].values.astype(float)
    lo, hi = float(np.nanmin(col)), float(np.nanmax(col))
    if lo == hi:
        grid = np.array([lo])
    else:
        is_int_feature = feature in ("publish_hour", "publish_weekday", "publish_month",
                                     "is_weekend", "video_category", "hour_bucket")
        grid = np.linspace(lo, hi, grid_size)
        if is_int_feature:
            grid = np.unique(np.round(grid))

    avg = []
    for g in grid:
        tmp = X_smp.copy()
        tmp[feature] = g
        avg.append(float(np.expm1(model.predict(tmp)).mean()))   # 原始热度空间均值

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(grid, avg, marker="o", color="#DD8452")
    ax.set_xlabel(FEATURE_CN.get(feature, feature))
    ax.set_ylabel("平均预测热度")
    ax.set_title(f"部分依赖图 PDP：{FEATURE_CN.get(feature, feature)} → 平均热度")
    fig.tight_layout()
    fname = "pdp_%s.png" % feature
    fig.savefig(os.path.join(FIG_DIR, fname), dpi=130)
    plt.close(fig)

    idx_max = int(np.argmax(avg))
    return {
        "mode": "pdp",
        "feature": feature,
        "feature_cn": FEATURE_CN.get(feature, feature),
        "figure": fname,
        "grid": [float(x) for x in grid],
        "avg_heat": avg,
        "best_point": {"x": float(grid[idx_max]), "avg_heat": avg[idx_max]},
    }


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main():
    try:
        parser = _Parser(prog="shap_analysis.py")
        parser.add_argument("--mode", default="global", choices=["global", "explain", "pdp"])
        parser.add_argument("--category", default="美食")
        parser.add_argument("--fans", type=float, default=1000.0)
        parser.add_argument("--hour", type=int, default=20)
        parser.add_argument("--weekday", type=int, default=5)
        parser.add_argument("--month", type=int, default=6)
        parser.add_argument("--feature", default="author_fans_log")
        args = parser.parse_args()

        # 与 predict_api 一致的 URL 解码（Java 端传参为 ASCII 安全形式）
        from urllib.parse import unquote_plus
        category = unquote_plus(args.category) if "%" in args.category else args.category

        if args.mode == "global":
            out = mode_global()
        elif args.mode == "pdp":
            out = mode_pdp(args.feature)
        else:
            out = mode_explain(category, args.fans, args.hour, args.weekday, args.month)

        print(json.dumps(out, ensure_ascii=False))
        sys.exit(0)
    except BaseException as exc:  # noqa: BLE001 - 统一转成契约 JSON
        if isinstance(exc, SystemExit) and exc.code == 0:
            raise
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc()}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    _stdout_reconfigure()
    main()
