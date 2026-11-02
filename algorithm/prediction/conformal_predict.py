"""
保形预测（Split Conformal Prediction）：为短视频热度预测给出「有覆盖保证」的区间估计。

与分位数回归（quantile_predict.py）的区别：
  - 分位数回归：训练 3 个不同目标的分位模型，覆盖率**只能事后检验**，没有保证；
  - 保形预测：用校准集残差的分位数构造区间，在样本可交换假设下满足
        P(y ∈ [lo, hi]) ≥ 1 - α
    是**有限样本**的覆盖保证，而不是渐近性质。

实现步骤：
  1) 训练集再切一刀：proper-train 拟合模型、calibration 计算非一致性分数；
  2) 分数 s_i = |y_i - ŷ_i|（log1p 空间，与训练目标一致）；
  3) q̂ 取 s 的经验分位，level = ceil((n+1)(1-α))/n（有限样本修正，防覆盖率不足）；
  4) 区间 = ŷ ± q̂（log 空间）→ expm1 还原为原始热度；
  5) Mondrian 变体：按「预测热度等级」分组各算一个 q̂，缓解低/中/高热度的条件覆盖失衡。

CLI 契约（与其它算法脚本一致：单行 JSON）：
  python conformal_predict.py --model lgbm --alpha 0.1 --platform douyin
  输出：{"mode":"conformal","alpha":0.1,...}
"""
import argparse
import json
import os
import sys
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import predict_api as P  # noqa: E402

# 校准集占训练集比例：太小导致 q̂ 方差大，太大浪费拟合样本，0.2 是常见折中
CALIB_RATIO = 0.2
SEED = 42
# 分组样本少于此阈值时不单独估 q̂，避免分位数噪声过大
MIN_GROUP_SIZE = 100


def _take_rows(X, idx):
    """按行号取子集：X 可能是 DataFrame（用 iloc）或 ndarray（用下标）。"""
    return X.iloc[idx] if hasattr(X, "iloc") else X[idx]


def _split_train_calib(X, y, ratio=CALIB_RATIO, seed=SEED):
    """把训练集随机切成「拟合集 + 校准集」，保形预测要求校准集不参与训练。"""
    n = len(y)
    idx = np.random.RandomState(seed).permutation(n)
    k = int(n * ratio)
    cal_idx, fit_idx = idx[:k], idx[k:]
    return _take_rows(X, fit_idx), y[fit_idx], _take_rows(X, cal_idx), y[cal_idx]


def _qhat(scores, alpha):
    """有限样本修正后的残差分位数：ceil((n+1)(1-α))/n。"""
    n = len(scores)
    if n == 0:
        return float("inf")
    level = min(np.ceil((n + 1) * (1 - alpha)) / n, 1.0)
    return float(np.quantile(scores, level))


def _interval_raw(pred_log, q):
    """把 log 空间的对称区间还原为原始热度区间（原始空间因此是非对称的）。"""
    return np.expm1(pred_log - q), np.expm1(pred_log + q)


def _coverage(y_true_raw, lo, hi):
    return float(np.mean((y_true_raw >= lo) & (y_true_raw <= hi)))


def _width_stats(lo, hi):
    width = np.maximum(hi - lo, 0.0)
    return {
        "avg_width": float(np.mean(width)),
        "median_width": float(np.median(width)),
    }


def _grade_groups(heat_values):
    return np.array([P.grade_of(h) for h in heat_values])


def _quantile_baseline(alpha, X_test, y_test_raw):
    """
    同口径对照：用既有的 q_low / q_high 分位模型在同一测试集上评估覆盖率与宽度。
    分位数模型缺失时返回 None（不阻断保形实验）。
    """
    try:
        import quantile_predict as Q
    except Exception:
        return None
    low_alpha, high_alpha = alpha, 1.0 - alpha
    try:
        b_lo, _ = Q.load_or_train(low_alpha)
        b_hi, _ = Q.load_or_train(high_alpha)
        lo = np.expm1(b_lo["model"].predict(X_test))
        hi = np.expm1(b_hi["model"].predict(X_test))
    except Exception as e:  # 训练失败不影响主实验
        return {"error": str(e)}
    st = _width_stats(lo, hi)
    return {
        "method": "quantile-lgbm",
        "target_coverage": 1 - alpha,
        "coverage": _coverage(y_test_raw, lo, hi),
        "avg_width": st["avg_width"],
        "median_width": st["median_width"],
    }


def mode_conformal(model="lgbm", alpha=0.1, platform=None):
    """保形预测主流程：训练 → 校准 → 在测试集上评估覆盖与宽度 → 与分位回归对照。"""
    X_train, y_train, X_test, y_test_log, _meta = P._prepare(platform=platform)
    if X_test is None or len(y_test_log) == 0:
        return {"mode": "conformal", "error": "当前平台没有测试集，无法评估覆盖率"}

    X_fit, y_fit, X_cal, y_cal = _split_train_calib(X_train, y_train)
    mdl = P.build_model(model, X_fit, y_fit)

    # ---- 校准：非一致性分数
    score_cal = np.abs(y_cal - mdl.predict(X_cal))
    q_global = _qhat(score_cal, alpha)

    # ---- Mondrian：按预测热度等级分组校准（部署时不需要知道真实热度，可用）
    pred_cal_log = mdl.predict(X_cal)
    groups = _grade_groups(np.expm1(pred_cal_log))
    q_by_grade = {}
    for g in np.unique(groups):
        mask = groups == g
        if int(mask.sum()) >= MIN_GROUP_SIZE:
            q_by_grade[str(g)] = _qhat(score_cal[mask], alpha)

    # ---- 测试集评估
    pred_log = mdl.predict(X_test)
    y_test_raw = np.expm1(y_test_log)

    lo, hi = _interval_raw(pred_log, q_global)
    st = _width_stats(lo, hi)
    global_block = {
        "coverage": _coverage(y_test_raw, lo, hi),
        "target_coverage": 1 - alpha,
        **st,
    }

    # 条件覆盖：按真实等级分组统计（论文里最关心「高热度是否被覆盖」）
    true_groups = _grade_groups(y_test_raw)
    by_grade = []
    for g in ["低热度", "中热度", "高热度"]:
        mask = true_groups == g
        if not mask.any():
            continue
        item = {
            "grade": g,
            "count": int(mask.sum()),
            "coverage_global_q": _coverage(y_test_raw[mask], lo[mask], hi[mask]),
        }
        # Mondrian：用预测等级匹配到的 q̂（预测错档时回退全局 q̂）
        q_g = q_by_grade.get(g, q_global)
        lo_g, hi_g = _interval_raw(pred_log[mask], q_g)
        item["coverage_mondrian_q"] = _coverage(y_test_raw[mask], lo_g, hi_g)
        item["qhat_log"] = q_g
        by_grade.append(item)

    baseline = _quantile_baseline(alpha, X_test, y_test_raw)

    return {
        "mode": "conformal",
        "model": model,
        "alpha": alpha,
        "target_coverage": 1 - alpha,
        "n_fit": int(len(y_fit)),
        "n_calib": int(len(y_cal)),
        "n_test": int(len(y_test_log)),
        "qhat_log": q_global,
        "global": global_block,
        "by_grade": by_grade,
        "mondrian_qhat": q_by_grade,
        "quantile_baseline": baseline,
        "note": "保形区间在样本可交换假设下满足有限样本覆盖保证；分位数回归无此保证，仅事后检验",
    }


def main():
    ap = argparse.ArgumentParser(description="短视频热度预测的保形预测区间")
    ap.add_argument("--mode", default="conformal", choices=["conformal"])
    ap.add_argument("--model", default="lgbm",
                    choices=["lgbm", "xgb", "rf", "lr", "knn", "dt"])
    ap.add_argument("--alpha", type=float, default=0.1, help="显著性水平，0.1 对应 90%% 覆盖")
    ap.add_argument("--platform", default=None)
    args = ap.parse_args()

    try:
        result = mode_conformal(model=args.model, alpha=args.alpha, platform=args.platform)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc(),
                          "trace_id": os.environ.get("TRACE_ID")}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
