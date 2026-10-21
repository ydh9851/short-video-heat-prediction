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


def mode_interaction(sample=300, top=8):
    """
    SHAP 交互效应：量化「两个特征共同作用」带来的额外贡献。
    输出交互强度最高的特征对（对角线为各特征主效应强度），用于回答
    "粉丝数之外，是否还存在组合效应"（如 类别 × 发布时段）。
    """
    import shap
    bundle = _get_model()
    model = bundle["model"]
    X_train, y_train, X_test, y_test, meta = P._prepare()

    n = min(sample, len(X_train))
    X_smp = X_train.sample(n=n, random_state=42)
    explainer = shap.TreeExplainer(model)

    inter = np.asarray(explainer.shap_interaction_values(X_smp), dtype=float)
    if inter.ndim == 4:          # (n, F, F, outputs) -> 取第一个输出
        inter = inter[:, :, :, 0]
    mean_abs = np.abs(inter).mean(axis=0)      # (F, F)

    F = len(P.FEATURE_NAMES)
    pairs = []
    for i in range(F):
        for j in range(i, F):
            is_diag = (i == j)
            pairs.append({
                "feature_a": P.FEATURE_NAMES[i],
                "feature_b": P.FEATURE_NAMES[j],
                "feature_a_cn": FEATURE_CN.get(P.FEATURE_NAMES[i], P.FEATURE_NAMES[i]),
                "feature_b_cn": FEATURE_CN.get(P.FEATURE_NAMES[j], P.FEATURE_NAMES[j]),
                "is_main_effect": bool(is_diag),
                "interaction": float(mean_abs[i, j]),
            })
    pairs.sort(key=lambda p: -p["interaction"])

    # 只保留"真正的两两交互"（排除主效应）用于排序展示
    cross = [p for p in pairs if not p["is_main_effect"]]
    diag = [{"feature": p["feature_a"], "feature_cn": p["feature_a_cn"],
             "main_effect": p["interaction"]} for p in pairs if p["is_main_effect"]]

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    labels = [f"{p['feature_a_cn']} × {p['feature_b_cn']}" for p in cross[:top]][::-1]
    vals = [p["interaction"] for p in cross[:top]][::-1]
    ax.barh(range(len(vals)), vals, color="#8b5cf6")
    ax.set_yticks(range(len(vals)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("平均 |SHAP 交互值|（log 空间）")
    ax.set_title("特征交互效应 Top 组合")
    ax.grid(axis="x", alpha=.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "shap_interaction.png"), dpi=130)
    plt.close(fig)

    strongest = cross[0] if cross else None
    return {
        "mode": "interaction",
        "figure": "shap_interaction.png",
        "top_pairs": cross[:top],
        "main_effects": sorted(diag, key=lambda d: -d["main_effect"]),
        "strongest_pair": strongest,
        "note": "对角线为主效应强度；两两交互值普遍远小于主效应，说明本模型以单特征效应为主。",
    }


# 反事实搜索空间（仅选"运营方可直接调整"的维度）
_MUT_HOURS = list(range(24))
_MUT_WEEKDAYS = list(range(7))
_MUT_MONTHS = list(range(1, 13))


def mode_counterfactual(category, fans, hour, weekday, month):
    """
    反事实分析：固定其他条件，把某个可调整维度改到"最优取值"后，热度预计变化多少。
    这是「归因 → 运营决策」闭环的直接量化形式。
    """
    bundle = _get_model()
    model = bundle["model"]
    meta = bundle["meta"]
    train, _ = P._load_frames()
    categories = sorted(train["video_category"].astype(str).unique().tolist())

    def heat_of(cat, fans_, hour_, wd_, mon_):
        row = pd.DataFrame([{
            "video_category": str(cat),
            "hour_bucket": P._hour_bucket(hour_),
            "author_fans_log": float(np.log1p(max(float(fans_), 0.0))),
            "publish_hour": float(hour_),
            "publish_weekday": float(wd_),
            "publish_month": float(mon_),
            "is_weekend": 1 if int(wd_) in (5, 6) else 0,
        }])
        X = P._encode_frame(row, meta["cat_maps"], meta["cat_modes"])
        return float(np.expm1(model.predict(X)[0]))

    base = heat_of(category, fans, hour, weekday, month)
    suggestions = []

    # (1) 发布小时
    scored = [(heat_of(category, fans, h, weekday, month), h) for h in _MUT_HOURS]
    scored.sort(reverse=True)
    best_h = scored[0][1]
    if best_h != int(hour):
        suggestions.append({"dimension": "发布小时", "from": int(hour), "to": int(best_h),
                            "heat": scored[0][0], "delta": scored[0][0] - base})
    # (2) 发布星期
    scored = [(heat_of(category, fans, hour, w, month), w) for w in _MUT_WEEKDAYS]
    scored.sort(reverse=True)
    wd_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    if scored[0][1] != int(weekday):
        suggestions.append({"dimension": "发布星期", "from": wd_cn[int(weekday)], "to": wd_cn[scored[0][1]],
                            "heat": scored[0][0], "delta": scored[0][0] - base})
    # (3) 发布月份
    scored = [(heat_of(category, fans, hour, weekday, m), m) for m in _MUT_MONTHS]
    scored.sort(reverse=True)
    if scored[0][1] != int(month):
        suggestions.append({"dimension": "发布月份", "from": f"{int(month)} 月", "to": f"{scored[0][1]} 月",
                            "heat": scored[0][0], "delta": scored[0][0] - base})
    # (4) 视频类别（换赛道）
    scored = [(heat_of(c, fans, hour, weekday, month), c) for c in categories]
    scored.sort(reverse=True)
    if str(scored[0][1]) != str(category):
        suggestions.append({"dimension": "视频类别", "from": str(category), "to": str(scored[0][1]),
                            "heat": scored[0][0], "delta": scored[0][0] - base})

    for s in suggestions:
        s["delta_pct"] = (s["delta"] / base * 100.0) if base else 0.0
        s["grade"] = P.grade_of(s["heat"])
    suggestions.sort(key=lambda s: -s["delta"])

    # 可视化：各"最优调整"相对基准的提升幅度
    if suggestions:
        fig, ax = plt.subplots(figsize=(8, 4.2))
        labels = [f"{s['dimension']}: {s['from']} → {s['to']}" for s in suggestions][::-1]
        vals = [s["delta_pct"] for s in suggestions][::-1]
        colors = ["#10b981" if v > 0 else "#94a3b8" for v in vals]
        ax.barh(range(len(vals)), vals, color=colors)
        ax.set_yticks(range(len(vals)))
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel("预计热度变化（%，相对当前条件）")
        ax.set_title("反事实分析：可调整维度对热度的提升空间")
        ax.grid(axis="x", alpha=.25)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG_DIR, "counterfactual.png"), dpi=130)
        plt.close(fig)

    return {
        "mode": "counterfactual",
        "base_heat": base,
        "base_grade": P.grade_of(base),
        "figure": "counterfactual.png" if suggestions else None,
        "suggestions": suggestions,
        "non_mutable": [{
            "dimension": "作者粉丝数",
            "value": float(fans),
            "note": "粉丝基数无法在单条内容层面直接改变，需通过账号长期运营/矩阵号导流积累。",
        }],
    }


# 4 个真实平台（与 algorithm/datasets/platform_schema.py 保持一致）
CROSS_PLATFORMS = [("douyin", "抖音"), ("youtube", "YouTube"),
                   ("tiktok", "TikTok"), ("bilibili", "哔哩哔哩")]


def mode_cross_platform(sample=1500):
    """
    跨平台 SHAP 特征贡献对照：
    对 4 个平台分别训练 LightGBM 并计算 SHAP 平均绝对贡献，归一化成"贡献占比"，
    从而回答「同一特征（如作者粉丝数）在不同平台上的重要性是否一致」。
    """
    import shap
    per_platform = []
    shares = {}          # platform -> {feature: share}
    ranks = {}           # platform -> {feature: rank}
    for pf, cn in CROSS_PLATFORMS:
        bundle, _ = P.load_or_train("lgbm", platform=pf)
        model = bundle["model"]
        X_train, y_train, X_test, y_test, meta = P._prepare(platform=pf)
        n = min(sample, len(X_train))
        X_smp = X_train.sample(n=n, random_state=42)
        sv = _tree_shap(shap.TreeExplainer(model), X_smp)
        mean_abs = np.abs(sv).mean(axis=0)
        total = float(mean_abs.sum()) or 1.0
        share = mean_abs / total
        order = np.argsort(mean_abs)[::-1]
        rank = {int(i): r + 1 for r, i in enumerate(order)}
        feats = [{
            "feature": P.FEATURE_NAMES[i],
            "feature_cn": FEATURE_CN.get(P.FEATURE_NAMES[i], P.FEATURE_NAMES[i]),
            "importance": float(mean_abs[i]),
            "share": float(share[i]),
            "rank": rank[i],
        } for i in range(len(P.FEATURE_NAMES))]
        shares[pf] = {f["feature"]: f["share"] for f in feats}
        ranks[pf] = {f["feature"]: f["rank"] for f in feats}
        per_platform.append({
            "platform": pf, "platform_cn": cn,
            "n_train": int(len(X_train)),
            "r2": float(bundle["metrics"]["r2"]),
            "features": feats,
            "top_features": sorted(feats, key=lambda f: f["rank"])[:4],
        })
        print(f"[cross-platform] {pf} n={len(X_train)} r2={bundle['metrics']['r2']:.4f} "
              f"top={feats[0]['feature']}", file=sys.stderr)

    # 以抖音为参照，给出各特征跨平台的贡献占比矩阵（行=特征，列=平台）
    ref = shares["douyin"]
    feature_matrix = []
    for f in P.FEATURE_NAMES:
        row = {"feature": f, "feature_cn": FEATURE_CN.get(f, f),
               "douyin_share": ref.get(f, 0.0),
               "max_share": max(shares[pf].get(f, 0.0) for pf, _ in CROSS_PLATFORMS),
               "min_share": min(shares[pf].get(f, 0.0) for pf, _ in CROSS_PLATFORMS),
               "spread": max(shares[pf].get(f, 0.0) for pf, _ in CROSS_PLATFORMS)
                         - min(shares[pf].get(f, 0.0) for pf, _ in CROSS_PLATFORMS)}
        for pf, _ in CROSS_PLATFORMS:
            row[pf + "_share"] = shares[pf].get(f, 0.0)
            row[pf + "_rank"] = ranks[pf].get(f, -1)
        feature_matrix.append(row)
    feature_matrix.sort(key=lambda r: -r["spread"])

    # 热力图：特征 × 平台的 SHAP 贡献占比
    cols = [pf for pf, _ in CROSS_PLATFORMS]
    col_cn = [cn for _, cn in CROSS_PLATFORMS]
    order_feat = [f for f in P.FEATURE_NAMES]
    mat = np.array([[shares[pf][f] for pf in cols] for f in order_feat])
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    im = ax.imshow(mat, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(col_cn)
    ax.set_yticks(range(len(order_feat)))
    ax.set_yticklabels([FEATURE_CN.get(f, f) for f in order_feat])
    for i in range(len(order_feat)):
        for j in range(len(cols)):
            v = mat[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    color="#1e293b" if v < mat.max() * 0.6 else "#fff", fontsize=9)
    ax.set_title("跨平台 SHAP 特征贡献占比对照")
    fig.colorbar(im, ax=ax, shrink=0.82, label="贡献占比")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "cross_platform_shap.png"), dpi=130)
    plt.close(fig)

    # 一致性结论：贡献占比最高的特征在各平台是否相同
    top1 = {x["platform"]: x["features"][0]["feature_cn"] for x in per_platform}
    consistent = len(set(top1.values())) == 1
    return {
        "mode": "cross-platform",
        "figure": "cross_platform_shap.png",
        "platforms": per_platform,
        "feature_matrix": feature_matrix,
        "matrix_columns": [{"key": pf + "_share", "label": cn} for pf, cn in CROSS_PLATFORMS],
        "top1_by_platform": top1,
        "top1_consistent": consistent,
        "spread_features": [r["feature_cn"] for r in feature_matrix[:3]],
    }


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main():
    try:
        parser = _Parser(prog="shap_analysis.py")
        parser.add_argument("--mode", default="global",
                            choices=["global", "explain", "pdp", "interaction",
                                     "counterfactual", "cross-platform"])

        parser.add_argument("--category", default="美食")
        parser.add_argument("--fans", type=float, default=1000.0)
        parser.add_argument("--hour", type=int, default=20)
        parser.add_argument("--weekday", type=int, default=5)
        parser.add_argument("--month", type=int, default=6)
        parser.add_argument("--feature", default="author_fans_log")
        parser.add_argument("--sample", type=int, default=1500,
                            help="跨平台模式下每个平台的 SHAP 采样行数")
        args = parser.parse_args()

        # 与 predict_api 一致的 URL 解码（Java 端传参为 ASCII 安全形式）
        from urllib.parse import unquote_plus
        category = unquote_plus(args.category) if "%" in args.category else args.category

        if args.mode == "global":
            out = mode_global()
        elif args.mode == "cross-platform":
            out = mode_cross_platform(args.sample)
        elif args.mode == "pdp":
            out = mode_pdp(args.feature)
        elif args.mode == "interaction":
            out = mode_interaction()
        elif args.mode == "counterfactual":
            out = mode_counterfactual(category, args.fans, args.hour, args.weekday, args.month)
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
