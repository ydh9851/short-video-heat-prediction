"""
解释质量评估（Explanation Quality）：回答「SHAP 结论凭什么可信」。

参考 MAIF/shapash 的三个解释质量维度，做本地化实现：

  1) 紧凑性 Compacity —— 需要多少个特征才能解释 80% / 90% 的平均绝对贡献。
     越少说明模型行为越容易被少数关键因素概括，解释越"好懂"。
  2) 一致性 Consistency —— SHAP 归因排序与另外两种重要性度量（增益重要性、
     置换重要性）的 Kendall τ 秩相关。三种方法独立计算却给出同样排序，
     说明归因结论不是某一种度量的算法假象。
  3) 稳定性 Stability —— 对训练集做 B 次 bootstrap 重采样并**重新训练**，
     观察 Top-K 特征集合的 Jaccard 相似度与平均 |SHAP| 向量的 Spearman 相关。
     稳定性低意味着"数据稍微变一点，结论就变了"，解释不可用于决策。

CLI 契约（单行 JSON，与其它算法脚本一致）：
  python explanation_quality.py --sample 2000 --bootstraps 3
"""
import argparse
import json
import os
import sys
import traceback

import numpy as np

ATTRIBUTION_DIR = os.path.dirname(os.path.abspath(__file__))
PREDICTION_DIR = os.path.join(os.path.dirname(ATTRIBUTION_DIR), "prediction")
sys.path.insert(0, PREDICTION_DIR)
import predict_api as P  # noqa: E402

SEED = 42
TOPK = 3


def _encode_all(platform=None):
    X_train, y_train, X_test, y_test, meta = P._prepare(platform=platform)
    return X_train, y_train, X_test, y_test, meta


def _mean_abs_shap(model, X_sample):
    """返回每个特征的平均 |SHAP|（按 FEATURE_NAMES 顺序）。"""
    import shap
    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(X_sample)
    if isinstance(values, list):  # 兼容旧版多输出返回
        values = values[0]
    values = np.asarray(values)
    if values.ndim == 3:
        values = values[:, :, 0]
    return np.abs(values).mean(axis=0)


def _gain_importance(model, n_features):
    """LightGBM 增益重要性；非 LightGBM 模型返回 None。"""
    try:
        gain = np.asarray(model.feature_importance(importance_type="gain"), dtype=float)
        return gain if gain.shape[0] == n_features else None
    except Exception:
        return None


def _permutation_importance_manual(model, X_eval, y_eval, seed=SEED, repeats=5):
    """
    手工置换重要性：逐列打乱后看 RMSE 上升幅度。
    （LightGBM Booster 不满足 sklearn 估算器接口，无法直接用 sklearn 的实现）
    """
    rng = np.random.RandomState(seed)
    base = np.sqrt(np.mean((model.predict(X_eval) - y_eval) ** 2))
    scores = np.zeros(X_eval.shape[1])
    for j in range(X_eval.shape[1]):
        deltas = []
        for _ in range(repeats):
            shuffled = X_eval.copy()
            # pandas 3 的 copy-on-write 下取出的列是只读视图，必须显式复制后打乱
            col = np.array(shuffled.iloc[:, j].values if hasattr(shuffled, "iloc") else shuffled[:, j],
                           dtype=float, copy=True)
            rng.shuffle(col)
            if hasattr(shuffled, "iloc"):
                shuffled.iloc[:, j] = col
            else:
                shuffled[:, j] = col
            rmse = np.sqrt(np.mean((model.predict(shuffled) - y_eval) ** 2))
            deltas.append(rmse - base)
        scores[j] = float(np.mean(deltas))
    return scores


def _kendall(a, b):
    from scipy.stats import kendalltau
    if a is None or b is None:
        return None
    if float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
        return None
    return float(kendalltau(a, b).statistic)


def _spearman(a, b):
    from scipy.stats import spearmanr
    if float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
        return None
    return float(spearmanr(a, b).statistic)


def _topk_set(vec, k=TOPK):
    return set(np.argsort(-np.asarray(vec))[:k].tolist())


def _jaccard(a, b):
    if not a and not b:
        return 1.0
    return len(a & b) / float(len(a | b))


def mode_quality(model="lgbm", sample=2000, bootstraps=3, platform=None):
    X_train, y_train, X_test, y_test, _meta = _encode_all(platform=platform)
    if X_test is None or len(X_test) == 0:
        return {"mode": "explanation-quality", "error": "当前平台缺少测试集"}

    n_feat = X_train.shape[1]
    names = list(P.FEATURE_NAMES)

    # 主模型：全训练集训练（与线上口径一致）
    main = P.build_model(model, X_train, y_train)

    rng = np.random.RandomState(SEED)
    n_eval = min(int(sample), len(X_test))
    eval_idx = rng.choice(len(X_test), size=n_eval, replace=False)
    X_eval = X_test.iloc[eval_idx] if hasattr(X_test, "iloc") else X_test[eval_idx]
    y_eval = y_test[eval_idx]

    shap_main = _mean_abs_shap(main, X_eval)

    # ---------------- 1) 紧凑性
    order = np.argsort(-shap_main)
    total = float(shap_main.sum()) or 1.0
    cumulative = np.cumsum(shap_main[order]) / total
    k80 = int(np.searchsorted(cumulative, 0.80) + 1)
    k90 = int(np.searchsorted(cumulative, 0.90) + 1)
    ranking = [{"feature": names[i], "mean_abs_shap": float(shap_main[i]),
                "share": float(shap_main[i] / total)} for i in order]

    # ---------------- 2) 一致性（三种度量排序的秩相关）
    gain = _gain_importance(main, n_feat)
    perm = _permutation_importance_manual(main, X_eval, y_eval)
    consistency = {
        "kendall_shap_vs_gain": _kendall(shap_main, gain),
        "kendall_shap_vs_permutation": _kendall(shap_main, perm),
        "kendall_gain_vs_permutation": _kendall(gain, perm),
        "permutation_top3": [names[i] for i in np.argsort(-perm)[:TOPK]],
        "gain_top3": None if gain is None else [names[i] for i in np.argsort(-gain)[:TOPK]],
        "shap_top3": [names[i] for i in order[:TOPK]],
    }

    # ---------------- 3) 稳定性（bootstrap 重训练）
    sets, spearmans = [], []
    for b in range(int(bootstraps)):
        idx = np.random.RandomState(SEED + b).choice(len(y_train), size=int(len(y_train) * 0.7), replace=True)
        Xb = X_train.iloc[idx] if hasattr(X_train, "iloc") else X_train[idx]
        yb = y_train[idx]
        mb = P.build_model(model, Xb, yb)
        vec = _mean_abs_shap(mb, X_eval)
        sets.append(sorted(names[i] for i in _topk_set(vec)))
        s = _spearman(vec, shap_main)
        if s is not None:
            spearmans.append(s)

    pairwise = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            pairwise.append(_jaccard(set(sets[i]), set(sets[j])))

    stability = {
        "bootstraps": int(bootstraps),
        "topk": TOPK,
        "topk_sets": sets,
        "jaccard_mean": float(np.mean(pairwise)) if pairwise else None,
        "jaccard_min": float(np.min(pairwise)) if pairwise else None,
        "spearman_mean": float(np.mean(spearmans)) if spearmans else None,
        "spearman_min": float(np.min(spearmans)) if spearmans else None,
    }

    return {
        "mode": "explanation-quality",
        "model": model,
        "platform": platform or "douyin",
        "sample": n_eval,
        "features": n_feat,
        "ranking": ranking,
        "compacity": {"k80": k80, "k90": k90,
                      "cumulative": [float(x) for x in cumulative[:min(len(cumulative), 8)]]},
        "consistency": consistency,
        "stability": stability,
        "note": "紧凑性=解释 80% 贡献所需特征数；一致性=三种重要性排序的 Kendall τ；"
                "稳定性=bootstrap 重训后 Top-K 特征集合的 Jaccard 与贡献向量 Spearman 相关",
    }


def main():
    ap = argparse.ArgumentParser(description="SHAP 解释质量评估（紧凑性 / 一致性 / 稳定性）")
    ap.add_argument("--sample", type=int, default=2000, help="解释所用测试样本数")
    ap.add_argument("--bootstraps", type=int, default=3, help="稳定性检验的重采样次数")
    ap.add_argument("--model", default="lgbm", choices=["lgbm", "xgb", "rf"])
    ap.add_argument("--platform", default=None)
    args = ap.parse_args()
    try:
        print(json.dumps(mode_quality(sample=args.sample, bootstraps=args.bootstraps,
                                      model=args.model, platform=args.platform),
                         ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc(),
                          "trace_id": os.environ.get("TRACE_ID")}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
