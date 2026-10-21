# -*- coding: utf-8 -*-
"""
model_evaluation.py —— 热度预测模型的系统化评估与实验分析
==========================================================
本模块为「论文实验章节」提供可复现的证据，覆盖以下 6 类实验（CLI，输出单行 JSON）：

    --mode cv               K 折交叉验证：多折 RMSE/MAE/R² 的均值±标准差，论证结果稳定性
    --mode tuning           LightGBM 超参数随机搜索：多组参数交叉验证对比，输出最优参数
    --mode learning-curve   学习曲线：训练集规模 10%→100% 对训练/验证误差的影响
    --mode importance       特征重要性三方对照：增益重要性 / 置换重要性 / SHAP 平均|贡献|
    --mode residual         残差分析：按热度等级的误差分布 + 分位数误差（P50/P90/P99）
    --mode ablation         特征消融：基础特征 vs 增强特征（周期编码 + 作者分层）

设计要点：
    * 复用 prediction/predict_api.py 的特征定义与类别编码（单一事实来源，避免口径漂移）；
    * 交叉验证与随机搜索均固定随机种子，保证实验可复现；
    * 所有指标同时给出 log1p 空间（训练目标，稳定）与原始热度空间（业务视角，受长尾影响）。
"""

import argparse
import json
import os
import sys
import time
import traceback
import warnings

warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))       # .../algorithm/evaluation
ALGO_DIR = os.path.dirname(BASE_DIR)                        # .../algorithm
SYSTEM_ROOT = os.path.dirname(ALGO_DIR)
PRED_DIR = os.path.join(ALGO_DIR, "prediction")
FIG_DIR = os.path.join(BASE_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

sys.path.insert(0, PRED_DIR)
import predict_api as P  # noqa: E402

RANDOM_STATE = 42
LGBM_ROUNDS = 500

# 分级阈值（与 grading 模块 K-Means k=3 一致），用于按等级做残差分析
GRADE_THRESHOLDS = (684.0, 15661.0)

FEATURE_CN = {
    "author_fans_log": "作者粉丝数(log)",
    "publish_hour": "发布小时",
    "publish_weekday": "发布星期",
    "publish_month": "发布月份",
    "is_weekend": "是否周末",
    "video_category": "视频类别",
    "hour_bucket": "发布时段",
    "hour_sin": "小时周期性(sin)",
    "hour_cos": "小时周期性(cos)",
    "weekday_sin": "星期周期性(sin)",
    "weekday_cos": "星期周期性(cos)",
    "author_tier": "作者分层",
}

# ---- 增强特征（在基础先验特征之上追加，仍严格满足"发布时可得"的防泄漏原则） ----
BASE_NUM = P.NUM_FEATURES                                        # 5 个数值特征
ENH_NUM = ["hour_sin", "hour_cos", "weekday_sin", "weekday_cos", "author_tier"]
CAT_FEATURES = P.CAT_FEATURES                                    # 2 个类别特征
BASE_FEATURES = BASE_NUM + CAT_FEATURES
ENH_FEATURES = BASE_NUM + ENH_NUM + CAT_FEATURES


def _stdout_reconfigure():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _tier(fans):
    """作者分层：素人(<1e3) / 腰部(1e3~1e5) / 头部(≥1e5)。"""
    if fans < 1000:
        return 0.0
    if fans < 100000:
        return 1.0
    return 2.0


def _add_enhanced(df: pd.DataFrame) -> pd.DataFrame:
    """在已编码的数值列基础上追加周期编码与作者分层（均可用发布时信息计算）。"""
    out = df.copy()
    hour = pd.to_numeric(out["publish_hour"], errors="coerce").fillna(-1)
    wd = pd.to_numeric(out["publish_weekday"], errors="coerce").fillna(-1)
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    out["weekday_sin"] = np.sin(2 * np.pi * wd / 7.0)
    out["weekday_cos"] = np.cos(2 * np.pi * wd / 7.0)
    fans = np.expm1(out["author_fans_log"].astype(float))     # 由 log 还原粉丝数
    out["author_tier"] = fans.apply(_tier)
    return out


def load_matrix(platform=None, enhanced=False):
    """
    返回 (X_train, y_train, X_test, y_test)：
      - 类别编码复用 predict_api，保证与线上预测口径一致；
      - platform 指定时加载对应平台清洗数据并自动切分；
      - enhanced=True 时追加周期编码与作者分层。
    """
    train, test = P._load_frames(platform=platform)
    maps, modes = P._fit_cat_maps(train)

    def build(df):
        enc = P._encode_frame(df, maps, modes)          # 仅基础特征
        full = df.copy()
        for col in P.NUM_FEATURES:
            full[col] = pd.to_numeric(enc[col], errors="coerce").fillna(0.0)
        full[P.CAT_FEATURES[0]] = enc[P.CAT_FEATURES[0]]
        full[P.CAT_FEATURES[1]] = enc[P.CAT_FEATURES[1]]
        full = _add_enhanced(full)
        cols = ENH_FEATURES if enhanced else BASE_FEATURES
        return full[cols].astype(float)

    X_train = build(train)
    X_test = build(test)
    y_train = train[P.TARGET_LOG].astype(float).values
    y_test = test[P.TARGET_LOG].astype(float).values
    return X_train, y_train, X_test, y_test


def feature_names(enhanced=False):
    return ENH_FEATURES if enhanced else BASE_FEATURES


def cat_idx_for(enhanced=False):
    names = feature_names(enhanced)
    return [names.index(c) for c in CAT_FEATURES]


# --------------------------------------------------------------------------- #
# 模型构造（CV / 调优均复用）
# --------------------------------------------------------------------------- #
def fit_lgbm(X, y, params=None, rounds=LGBM_ROUNDS, cat_idx=None):
    import lightgbm as lgb
    p = {
        "objective": "regression",
        "metric": "rmse",
        "boosting_type": "gbdt",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
        "seed": RANDOM_STATE,
    }
    if params:
        p.update(params)
    ds = lgb.Dataset(X, label=y, categorical_feature=cat_idx or [], free_raw_data=False)
    return lgb.train(p, ds, num_boost_round=rounds)


def fit_sklearn(name, X, y):
    if name == "lr":
        from sklearn.linear_model import LinearRegression
        return LinearRegression().fit(X, y)
    if name == "rf":
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(n_estimators=120, max_depth=16, min_samples_leaf=5,
                                     random_state=RANDOM_STATE, n_jobs=-1).fit(X, y)
    if name == "knn":
        from sklearn.neighbors import KNeighborsRegressor
        return KNeighborsRegressor(n_neighbors=5, weights="distance", n_jobs=-1).fit(X, y)
    if name == "dt":
        from sklearn.tree import DecisionTreeRegressor
        return DecisionTreeRegressor(random_state=RANDOM_STATE).fit(X, y)
    raise ValueError("unsupported model: %s" % name)


def _fit(name, X, y, params=None, rounds=LGBM_ROUNDS, cat_idx=None):
    if name == "lgbm":
        return fit_lgbm(X, y, params, rounds, cat_idx)
    return fit_sklearn(name, X, y)


def metrics_on(model, X, y):
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    pl = np.asarray(model.predict(X), dtype=float).ravel()
    y_raw, p_raw = np.expm1(y), np.expm1(pl)
    return {
        "rmse": float(np.sqrt(mean_squared_error(y, pl))),
        "mae": float(mean_absolute_error(y, pl)),
        "r2": float(r2_score(y, pl)),
        "rmse_raw": float(np.sqrt(mean_squared_error(y_raw, p_raw))),
        "mae_raw": float(mean_absolute_error(y_raw, p_raw)),
        "r2_raw": float(r2_score(y_raw, p_raw)),
    }


# --------------------------------------------------------------------------- #
# 1) K 折交叉验证
# --------------------------------------------------------------------------- #
def mode_cv(platform=None, folds=5, models=("lgbm", "lr", "rf")):
    from sklearn.model_selection import KFold
    X, y, _, _ = load_matrix(platform=platform, enhanced=False)
    cat = cat_idx_for(enhanced=False)
    kf = KFold(n_splits=folds, shuffle=True, random_state=RANDOM_STATE)

    out = {}
    for name in models:
        rows = []
        t0 = time.time()
        for tr, va in kf.split(X):
            m = _fit(name, X.iloc[tr], y[tr], cat_idx=cat)
            rows.append(metrics_on(m, X.iloc[va], y[va]))
        r2 = [r["r2"] for r in rows]
        rmse = [r["rmse"] for r in rows]
        out[name] = {
            "folds": rows,
            "r2_mean": float(np.mean(r2)), "r2_std": float(np.std(r2)),
            "rmse_mean": float(np.mean(rmse)), "rmse_std": float(np.std(rmse)),
            "seconds": round(time.time() - t0, 1),
        }
        print(f"[cv] {name}: R2={np.mean(r2):.4f}±{np.std(r2):.4f}", file=sys.stderr)

    # 交叉验证得分图
    names = list(out.keys())
    fig, ax = plt.subplots(figsize=(8, 4.6))
    data = [[f["r2"] for f in out[n]["folds"]] for n in names]
    bp = ax.boxplot(data, patch_artist=True, widths=0.5)
    ax.set_xticklabels(names)
    for patch in bp["boxes"]:
        patch.set_facecolor("#c7cbf7")
        patch.set_edgecolor("#6366f1")
    for med in bp["medians"]:
        med.set_color("#4f46e5")
        med.set_linewidth(2)
    ax.set_ylabel("R²（log 空间）")
    ax.set_title(f"{folds} 折交叉验证 R² 分布")
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "cv_scores.png"), dpi=130)
    plt.close(fig)

    return {
        "mode": "cv", "folds": folds, "models": out,
        "figure": "cv_scores.png",
        "best": max(names, key=lambda n: out[n]["r2_mean"]),
    }


# --------------------------------------------------------------------------- #
# 2) LightGBM 超参数随机搜索
# --------------------------------------------------------------------------- #
def mode_tuning(platform=None, trials=12, folds=3):
    from sklearn.model_selection import KFold
    X, y, _, _ = load_matrix(platform=platform, enhanced=False)
    cat = cat_idx_for(enhanced=False)
    kf = KFold(n_splits=folds, shuffle=True, random_state=RANDOM_STATE)

    rng = np.random.RandomState(RANDOM_STATE)
    space = {
        "learning_rate": [0.02, 0.03, 0.05, 0.08, 0.1],
        "num_leaves": [15, 31, 63, 127],
        "min_data_in_leaf": [10, 20, 50, 100],
        "feature_fraction": [0.6, 0.8, 1.0],
        "bagging_fraction": [0.6, 0.8, 1.0],
        "lambda_l2": [0.0, 1.0, 5.0],
    }
    sampled, seen = [], set()
    while len(sampled) < trials:
        cfg = {k: v[rng.randint(len(v))] for k, v in space.items()}
        key = tuple(sorted(cfg.items()))
        if key in seen:
            continue
        seen.add(key)
        sampled.append(cfg)

    results = []
    for i, cfg in enumerate(sampled, 1):
        t0 = time.time()
        scores = []
        for tr, va in kf.split(X):
            m = fit_lgbm(X.iloc[tr], y[tr], params=cfg, cat_idx=cat)
            scores.append(metrics_on(m, X.iloc[va], y[va])["rmse"])
        results.append({
            "params": cfg,
            "rmse_mean": float(np.mean(scores)),
            "rmse_std": float(np.std(scores)),
            "seconds": round(time.time() - t0, 1),
        })
        print(f"[tuning] {i}/{trials} rmse={np.mean(scores):.4f} {cfg}", file=sys.stderr)

    results.sort(key=lambda r: r["rmse_mean"])
    best = results[0]

    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    xs = list(range(1, len(results) + 1))
    ys = [r["rmse_mean"] for r in results]
    ax.plot(xs, ys, marker="o", color="#6366f1", linewidth=2)
    ax.scatter([1], [ys[0]], s=90, color="#ef4444", zorder=5, label="最优参数")
    ax.set_xlabel("按 RMSE 排序的试验序号")
    ax.set_ylabel("3 折 CV RMSE(log)")
    ax.set_title("LightGBM 超参数随机搜索结果")
    ax.grid(alpha=.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "tuning_result.png"), dpi=130)
    plt.close(fig)

    return {
        "mode": "tuning", "trials": trials, "folds": folds,
        "space": space, "results": results[:10],
        "best_params": best["params"], "best_rmse": best["rmse_mean"],
        "figure": "tuning_result.png",
    }


# --------------------------------------------------------------------------- #
# 3) 学习曲线
# --------------------------------------------------------------------------- #
def mode_learning_curve(platform=None, fractions=(0.1, 0.2, 0.4, 0.6, 0.8, 1.0)):
    X, y, X_test, y_test = load_matrix(platform=platform, enhanced=False)
    cat = cat_idx_for(enhanced=False)
    rng = np.random.RandomState(RANDOM_STATE)
    idx = rng.permutation(len(X))
    rounds = 300

    rows = []
    for f in fractions:
        n = max(500, int(len(X) * f))
        sel = idx[:n]
        # 训练集内部再切 20% 作为"训练内验证"，用于观察是否过拟合
        cut = int(n * 0.8)
        tr, va = sel[:cut], sel[cut:]
        m = fit_lgbm(X.iloc[tr], y[tr], rounds=rounds, cat_idx=cat)
        rows.append({
            "fraction": f, "n_train": int(n),
            "train_rmse": metrics_on(m, X.iloc[tr], y[tr])["rmse"],
            "valid_rmse": metrics_on(m, X.iloc[va], y[va])["rmse"],
            "test_rmse": metrics_on(m, X_test, y_test)["rmse"],
        })
        print(f"[learning-curve] {f:.0%} n={n} train={rows[-1]['train_rmse']:.4f} "
              f"valid={rows[-1]['valid_rmse']:.4f}", file=sys.stderr)

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    xs = [r["n_train"] for r in rows]
    ax.plot(xs, [r["train_rmse"] for r in rows], marker="o", label="训练集 RMSE", color="#34d399")
    ax.plot(xs, [r["valid_rmse"] for r in rows], marker="s", label="训练内验证 RMSE", color="#f59e0b")
    ax.plot(xs, [r["test_rmse"] for r in rows], marker="^", label="独立测试集 RMSE", color="#6366f1")
    ax.set_xlabel("训练样本数")
    ax.set_ylabel("RMSE（log 空间）")
    ax.set_title("LightGBM 学习曲线")
    ax.grid(alpha=.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "learning_curve.png"), dpi=130)
    plt.close(fig)

    gap = rows[-1]["valid_rmse"] - rows[-1]["train_rmse"]
    return {
        "mode": "learning-curve", "points": rows, "figure": "learning_curve.png",
        "final_gap": float(gap),
        "saturated": bool(abs(rows[-1]["test_rmse"] - rows[-2]["test_rmse"]) < 0.005),
    }


# --------------------------------------------------------------------------- #
# 4) 特征重要性三方对照（增益 / 置换 / SHAP）
# --------------------------------------------------------------------------- #
def mode_importance(platform=None, sample=2000):
    import shap
    import lightgbm as lgb
    from sklearn.metrics import mean_squared_error

    X, y, X_test, y_test = load_matrix(platform=platform, enhanced=False)
    cat = cat_idx_for(enhanced=False)
    names = feature_names(enhanced=False)

    booster = fit_lgbm(X, y, cat_idx=cat)

    # (1) 增益重要性
    gain = np.asarray(booster.feature_importance(importance_type="gain"), dtype=float)
    gain = gain / gain.sum() if gain.sum() else gain

    # (2) 置换重要性（在测试集上打乱单列后 RMSE 的增量）
    base_rmse = float(np.sqrt(mean_squared_error(y_test, booster.predict(X_test))))
    rng = np.random.RandomState(RANDOM_STATE)
    perm = []
    Xt = X_test.reset_index(drop=True)
    for col in names:
        tmp = Xt.copy()
        tmp[col] = tmp[col].values[rng.permutation(len(tmp))]
        rmse = float(np.sqrt(mean_squared_error(y_test, booster.predict(tmp))))
        perm.append(max(0.0, rmse - base_rmse))
    perm = np.asarray(perm, dtype=float)
    perm = perm / perm.sum() if perm.sum() else perm

    # (3) SHAP 平均绝对贡献
    n = min(sample, len(X))
    Xs = X.sample(n=n, random_state=RANDOM_STATE)
    explainer = shap.TreeExplainer(booster)
    sv = np.asarray(explainer.shap_values(Xs), dtype=float)
    if sv.ndim == 3:
        sv = sv[:, :, 0]
    shap_imp = np.abs(sv).mean(axis=0)
    shap_imp = shap_imp / shap_imp.sum() if shap_imp.sum() else shap_imp

    order = np.argsort(shap_imp)[::-1]
    cn = [FEATURE_CN.get(names[i], names[i]) for i in order]
    table = [{
        "feature": names[i], "feature_cn": FEATURE_CN.get(names[i], names[i]),
        "gain": float(gain[i]), "permutation": float(perm[i]), "shap": float(shap_imp[i]),
    } for i in order]

    ypos = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    h = 0.26
    ax.barh(ypos + h, [gain[i] for i in order][::-1], height=h, label="增益重要性", color="#6366f1")
    ax.barh(ypos, [perm[i] for i in order][::-1], height=h, label="置换重要性", color="#f59e0b")
    ax.barh(ypos - h, [shap_imp[i] for i in order][::-1], height=h, label="SHAP 平均|贡献|", color="#10b981")
    ax.set_yticks(ypos)
    ax.set_yticklabels(cn[::-1])
    ax.set_xlabel("归一化重要性（三者各自归一化到和为 1）")
    ax.set_title("特征重要性三方对照")
    ax.grid(axis="x", alpha=.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "importance_compare.png"), dpi=130)
    plt.close(fig)

    top3 = [t["feature_cn"] for t in table[:3]]
    gain_order = [names[i] for i in np.argsort(gain)[::-1]]
    perm_order = [names[i] for i in np.argsort(perm)[::-1]]
    shap_order = [names[i] for i in np.argsort(shap_imp)[::-1]]
    return {
        "mode": "importance", "table": table, "figure": "importance_compare.png",
        "top3": top3,
        "rank_orders": {"gain": gain_order, "permutation": perm_order, "shap": shap_order},
        "top1_consistent": bool(len({gain_order[0], perm_order[0], shap_order[0]}) == 1),
        "top3_overlap": int(len(set(gain_order[:3]) & set(perm_order[:3]) & set(shap_order[:3]))),
    }


# --------------------------------------------------------------------------- #
# 5) 残差分析
# --------------------------------------------------------------------------- #
def mode_residual(platform=None):
    X, y, X_test, y_test = load_matrix(platform=platform, enhanced=False)
    cat = cat_idx_for(enhanced=False)
    booster = fit_lgbm(X, y, cat_idx=cat)

    pred_log = np.asarray(booster.predict(X_test), dtype=float).ravel()
    res_log = y_test - pred_log
    y_raw, p_raw = np.expm1(y_test), np.expm1(pred_log)
    abs_err = np.abs(p_raw - y_raw)
    rel_err = abs_err / np.maximum(y_raw, 1.0)

    # 分位数误差（原始空间）：反映"多数样本误差很小、少数爆款误差大"的长尾特性
    q = {f"p{int(k * 100)}": float(np.quantile(abs_err, k)) for k in (0.5, 0.9, 0.95, 0.99)}
    rel = {f"p{int(k * 100)}": float(np.quantile(rel_err, k)) for k in (0.5, 0.9, 0.95, 0.99)}

    def grade_of(h):
        if h < GRADE_THRESHOLDS[0]:
            return "低热度"
        if h < GRADE_THRESHOLDS[1]:
            return "中热度"
        return "高热度"

    df = pd.DataFrame({"y": y_test, "y_raw": y_raw, "p_raw": p_raw, "res_log": res_log,
                       "abs_err": abs_err, "rel_err": rel_err})
    df["grade"] = df["y_raw"].apply(grade_of)

    by_grade = []
    for g in ["低热度", "中热度", "高热度"]:
        sub = df[df["grade"] == g]
        if len(sub) == 0:
            continue
        by_grade.append({
            "grade": g, "count": int(len(sub)),
            "rmse_log": float(np.sqrt((sub["res_log"] ** 2).mean())),
            "mae_raw": float(sub["abs_err"].mean()),
            "mae_raw_median": float(sub["abs_err"].median()),
            "rel_err_p50": float(sub["rel_err"].median()),
        })

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    axes[0].boxplot([df[df["grade"] == g]["res_log"].values for g in ["低热度", "中热度", "高热度"]],
                    patch_artist=True,
                    boxprops=dict(facecolor="#e0e0fc", color="#6366f1"),
                    medianprops=dict(color="#4f46e5", linewidth=2))
    axes[0].set_xticklabels(["低热度", "中热度", "高热度"])
    axes[0].axhline(0, color="#94a3b8", linewidth=1, linestyle="--")
    axes[0].set_ylabel("残差（log 空间）")
    axes[0].set_title("按热度等级的残差分布")
    axes[0].grid(axis="y", alpha=.25)

    axes[1].hist(np.clip(rel_err, 0, 2.0), bins=50, color="#8b5cf6", alpha=.85)
    axes[1].axvline(np.median(rel_err), color="#ef4444", linestyle="--",
                    label=f"P50 相对误差={np.median(rel_err):.2f}")
    axes[1].set_xlabel("相对误差 |预测-真实| / 真实")
    axes[1].set_ylabel("样本数")
    axes[1].set_title("原始空间相对误差分布（截断至 2.0）")
    axes[1].legend()
    axes[1].grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "residual_analysis.png"), dpi=130)
    plt.close(fig)

    return {
        "mode": "residual", "by_grade": by_grade,
        "abs_err_quantiles_raw": q, "rel_err_quantiles": rel,
        "mean_abs_err_raw": float(abs_err.mean()), "median_abs_err_raw": float(np.median(abs_err)),
        "figure": "residual_analysis.png",
    }


# --------------------------------------------------------------------------- #
# 6) 特征消融实验
# --------------------------------------------------------------------------- #
def mode_ablation(platform=None, models=("lgbm", "lr")):
    from sklearn.model_selection import KFold
    kf_cache = {}
    out = {}
    for enhanced in (False, True):
        X, y, X_test, y_test = load_matrix(platform=platform, enhanced=enhanced)
        cat = cat_idx_for(enhanced=enhanced)
        key = "enhanced" if enhanced else "base"
        out[key] = {"n_features": int(X.shape[1]), "features": feature_names(enhanced), "models": {}}
        for name in models:
            kf = kf_cache.setdefault(name, KFold(n_splits=3, shuffle=True, random_state=RANDOM_STATE))
            scores = []
            for tr, va in kf.split(X):
                m = _fit(name, X.iloc[tr], y[tr], cat_idx=cat)
                scores.append(metrics_on(m, X.iloc[va], y[va]))
            out[key]["models"][name] = {
                "r2_mean": float(np.mean([s["r2"] for s in scores])),
                "rmse_mean": float(np.mean([s["rmse"] for s in scores])),
                "mae_mean": float(np.mean([s["mae"] for s in scores])),
            }
            print(f"[ablation] {key}/{name} R2={out[key]['models'][name]['r2_mean']:.4f}", file=sys.stderr)

    fig, ax = plt.subplots(figsize=(8, 4.6))
    xs = np.arange(len(models))
    w = 0.34
    ax.bar(xs - w / 2, [out["base"]["models"][m]["r2_mean"] for m in models], w,
           label="基础特征", color="#c7cbf7")
    ax.bar(xs + w / 2, [out["enhanced"]["models"][m]["r2_mean"] for m in models], w,
           label="增强特征(+周期编码+作者分层)", color="#6366f1")
    ax.set_xticks(xs)
    ax.set_xticklabels([m.upper() for m in models])
    ax.set_ylabel("3 折 CV R²（log 空间）")
    ax.set_ylim(0, 1)
    ax.set_title("特征消融实验：基础特征 vs 增强特征")
    for i, m in enumerate(models):
        ax.text(i - w / 2, out["base"]["models"][m]["r2_mean"] + .01,
                f"{out['base']['models'][m]['r2_mean']:.3f}", ha="center", fontsize=9)
        ax.text(i + w / 2, out["enhanced"]["models"][m]["r2_mean"] + .01,
                f"{out['enhanced']['models'][m]['r2_mean']:.3f}", ha="center", fontsize=9)
    ax.grid(axis="y", alpha=.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "ablation.png"), dpi=130)
    plt.close(fig)

    delta = {m: round(out["enhanced"]["models"][m]["r2_mean"] - out["base"]["models"][m]["r2_mean"], 4)
             for m in models}
    return {"mode": "ablation", "result": out, "r2_delta": delta, "figure": "ablation.png"}


# --------------------------------------------------------------------------- #
# 7) 跨平台分布漂移（PSI / KS）
# --------------------------------------------------------------------------- #
DRIFT_PLATFORMS = [("douyin", "抖音"), ("youtube", "YouTube"),
                   ("tiktok", "TikTok"), ("bilibili", "哔哩哔哩")]
DRIFT_FEATURES = ["author_fans_log", "publish_hour", "publish_weekday",
                  "publish_month", "is_weekend"]


def _psi(ref, tgt, bins=10):
    """群体稳定性指数：衡量两个分布的整体偏移程度。

    以参照分布的等频分位点为分箱边界，比较两分布在各箱内的占比差异。
    PSI < 0.1 稳定；0.1~0.25 中等漂移；>= 0.25 显著漂移。
    """
    ref = np.asarray(ref, dtype=float)
    tgt = np.asarray(tgt, dtype=float)
    ref = ref[np.isfinite(ref)]
    tgt = tgt[np.isfinite(tgt)]
    qs = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(qs) < 3:                     # 取值过少（如 is_weekend 只有 0/1）
        qs = np.unique(np.concatenate([[-np.inf], qs, [np.inf]]))
    else:
        qs[0], qs[-1] = -np.inf, np.inf
    r_hist = np.histogram(ref, bins=qs)[0] / max(len(ref), 1)
    t_hist = np.histogram(tgt, bins=qs)[0] / max(len(tgt), 1)
    eps = 1e-6
    r_hist = np.where(r_hist == 0, eps, r_hist)
    t_hist = np.where(t_hist == 0, eps, t_hist)
    return float(np.sum((t_hist - r_hist) * np.log(t_hist / r_hist)))


def _load_raw(platform):
    df = pd.read_csv(os.path.join(SYSTEM_ROOT, "data", "processed", f"{platform}_clean.csv"))
    return df


def mode_drift(reference="douyin"):
    """跨平台分布漂移看板：以参照平台为基准，衡量其它平台各特征分布的 PSI/KS。"""
    from scipy.stats import ks_2samp

    frames = {}
    for pf, _ in DRIFT_PLATFORMS:
        d = _load_raw(pf)
        frames[pf] = {f: pd.to_numeric(d[f], errors="coerce").values for f in DRIFT_FEATURES}

    ref_pf = reference
    detail = []
    for pf, cn in DRIFT_PLATFORMS:
        if pf == ref_pf:
            continue
        for f in DRIFT_FEATURES:
            r, t = frames[ref_pf][f], frames[pf][f]
            psi = _psi(r, t)
            ks = ks_2samp(r[np.isfinite(r)], t[np.isfinite(t)])
            level = "稳定" if psi < 0.1 else ("中等漂移" if psi < 0.25 else "显著漂移")
            detail.append({
                "platform": pf, "platform_cn": cn,
                "feature": f, "feature_cn": FEATURE_CN.get(f, f),
                "psi": psi, "psi_level": level,
                "ks_stat": float(ks.statistic), "ks_p": float(ks.pvalue),
                "ks_significant": bool(ks.pvalue < 0.05),
                "n_ref": int(np.isfinite(r).sum()), "n_target": int(np.isfinite(t).sum()),
            })
    detail.sort(key=lambda d: -d["psi"])

    # 热力图：特征 × 平台的 PSI
    others = [(pf, cn) for pf, cn in DRIFT_PLATFORMS if pf != ref_pf]
    mat = np.array([[_psi(frames[ref_pf][f], frames[pf][f]) for pf, _ in others]
                    for f in DRIFT_FEATURES])
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    im = ax.imshow(mat, cmap="OrRd", aspect="auto", vmin=0, vmax=max(0.3, float(mat.max())))
    ax.set_xticks(range(len(others)))
    ax.set_xticklabels([cn for _, cn in others])
    ax.set_yticks(range(len(DRIFT_FEATURES)))
    ax.set_yticklabels([FEATURE_CN.get(f, f) for f in DRIFT_FEATURES])
    for i in range(len(DRIFT_FEATURES)):
        for j in range(len(others)):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center",
                    color="#1e293b" if mat[i, j] < 0.18 else "#fff", fontsize=9)
    ax.set_title(f"跨平台特征分布漂移 PSI（基准：{dict(DRIFT_PLATFORMS)[ref_pf]}）")
    fig.colorbar(im, ax=ax, shrink=0.85, label="PSI")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "platform_drift.png"), dpi=130)
    plt.close(fig)

    worst = detail[0]
    return {
        "mode": "drift",
        "reference": ref_pf,
        "reference_cn": dict(DRIFT_PLATFORMS)[ref_pf],
        "features": DRIFT_FEATURES,
        "detail": detail,
        "figure": "platform_drift.png",
        "max_psi": worst["psi"],
        "worst_platform": worst["platform_cn"],
        "worst_feature": worst["feature_cn"],
        "stable_ratio": float(sum(1 for d in detail if d["psi_level"] == "稳定") / len(detail)),
    }


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


MODES = ["cv", "tuning", "learning-curve", "importance", "residual", "ablation", "drift"]


def main():
    try:
        parser = _Parser(prog="model_evaluation.py")
        parser.add_argument("--mode", required=True, choices=MODES)
        parser.add_argument("--platform", default=None,
                            help="平台标识：douyin / youtube / tiktok / bilibili，缺省时使用抖音原始预切分数据")
        parser.add_argument("--folds", type=int, default=5)
        parser.add_argument("--trials", type=int, default=12)
        parser.add_argument("--sample", type=int, default=2000)
        args = parser.parse_args()

        pf = args.platform or None

        if args.mode == "cv":
            out = mode_cv(platform=pf, folds=args.folds)
        elif args.mode == "tuning":
            out = mode_tuning(platform=pf, trials=args.trials)
        elif args.mode == "learning-curve":
            out = mode_learning_curve(platform=pf)
        elif args.mode == "importance":
            out = mode_importance(platform=pf, sample=args.sample)
        elif args.mode == "residual":
            out = mode_residual(platform=pf)
        elif args.mode == "drift":
            out = mode_drift()
        else:
            out = mode_ablation(platform=pf)

        print(json.dumps(out, ensure_ascii=False))
        sys.exit(0)
    except BaseException as exc:  # noqa: BLE001
        if isinstance(exc, SystemExit) and exc.code == 0:
            raise
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc()}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    _stdout_reconfigure()
    main()
