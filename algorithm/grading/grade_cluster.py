# -*- coding: utf-8 -*-
"""
grade_cluster.py —— 短视频热度分级（聚类 + 分类）
=================================================
本模块把连续的热度预测问题扩展为「热度等级」问题，是本系统题目中
「含热度分级」元素的落地，为论文提供独立的建模章节。

流程：
    1) 对热度（log1p 空间）做 K-Means 聚类，得到 k 个热度等级（低/中/高），
       并按聚类中心排序确定等级顺序与分级阈值；
    2) 以同一套「发布时先验特征」训练分类模型（LightGBM 分类器为主，
       与逻辑回归 / 随机森林对照），预测视频所属热度等级；
    3) 输出分级阈值、各等级热度区间、分类指标与混淆矩阵图。

与预测模块同源：特征定义与编码复用 prediction/predict_api.py。

用法（CLI，输出单行 JSON）：
    python grade_cluster.py                # 默认 k=3
    python grade_cluster.py --k 4
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

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.abspath(__file__))            # .../algorithm/grading
ALGO_DIR = os.path.dirname(BASE)
SYSTEM_ROOT = os.path.dirname(ALGO_DIR)
PRED_DIR = os.path.join(ALGO_DIR, "prediction")
FIG_DIR = os.path.join(BASE, "figures")
CACHE_DIR = os.path.join(BASE, "model_cache")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

sys.path.insert(0, PRED_DIR)
import predict_api as P  # noqa: E402

GRADE_NAMES = {3: ["低热度", "中热度", "高热度"],
               4: ["低热度", "中低热度", "中高热度", "高热度"],
               5: ["很低", "低", "中", "高", "很高"]}


def _stdout_reconfigure():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _load():
    train = pd.read_csv(P.TRAIN_CSV)
    test = pd.read_csv(P.TEST_CSV)
    return train, test


def fit_grades(train, k):
    """对热度 log 做 K-Means 聚类，返回等级标签、聚类中心与阈值。"""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    x = train[P.TARGET_LOG].values.reshape(-1, 1)
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(x)
    centers = km.cluster_centers_.ravel()
    order = np.argsort(centers)                 # 按中心升序 -> 低~高
    rank = {c: i for i, c in enumerate(order)}
    labels = np.array([rank[c] for c in km.labels_])
    sil = float(silhouette_score(x, labels)) if k > 1 else 0.0

    # 阈值：相邻中心在原始热度空间的中点（log 空间取中点后 expm1 还原）
    thresholds = []
    sorted_centers = centers[order]
    for i in range(k - 1):
        mid_log = (sorted_centers[i] + sorted_centers[i + 1]) / 2.0
        thresholds.append(float(np.expm1(mid_log)))

    names = GRADE_NAMES.get(k, [f"等级{i + 1}" for i in range(k)])
    return labels, names, thresholds, sil, km


def build_features(df, maps, modes):
    X = P._encode_frame(df, maps, modes)
    return X, P.FEATURE_NAMES, P.CAT_IDX


def train_classifier(name, X_train, y_train, X_test, y_test):
    """训练分类器并返回 (model, 指标)。"""
    from sklearn.metrics import accuracy_score, f1_score

    if name == "lgbm":
        import lightgbm as lgb
        n_cls = len(set(y_train))
        params = {"objective": "multiclass", "num_class": n_cls, "metric": "multi_logloss",
                  "learning_rate": 0.08, "num_leaves": 31, "verbose": -1, "seed": 42}
        ds = lgb.Dataset(X_train, label=y_train, categorical_feature=P.CAT_IDX, free_raw_data=False)
        model = lgb.train(params, ds, num_boost_round=200)
    elif name == "rf":
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=120, max_depth=16, min_samples_leaf=5,
                                       random_state=42, n_jobs=-1).fit(X_train, y_train)
    else:
        from sklearn.linear_model import LogisticRegression
        model = LogisticRegression(max_iter=1000).fit(X_train, y_train)

    raw = np.asarray(model.predict(X_test))
    if raw.ndim == 2:                      # LightGBM 多分类返回 (n, k) 概率 -> 取最大
        pred = raw.argmax(axis=1)
    else:                                  # sklearn 分类器返回 (n,) 标签
        pred = raw.ravel().round().astype(int)
    metrics = {
        "model": name,
        "accuracy": float(accuracy_score(y_test, pred)),
        "macro_f1": float(f1_score(y_test, pred, average="macro")),
    }
    return model, metrics, pred


def _confusion_fig(y_test, pred, names, path):
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_test, pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(names)))
    ax.set_yticks(range(len(names)))
    ax.set_xticklabels(names)
    ax.set_yticklabels(names)
    ax.set_xlabel("预测等级")
    ax.set_ylabel("真实等级")
    ax.set_title("热度分级混淆矩阵（LightGBM）")
    for i in range(len(names)):
        for j in range(len(names)):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def run(k=3):
    import joblib
    train, test = _load()

    labels, names, thresholds, sil, km = fit_grades(train, k)
    train = train.copy()
    train["grade"] = labels

    maps, modes = P._fit_cat_maps(train)
    X_train, fnames, cat_idx = build_features(train, maps, modes)
    y_train = train["grade"].values

    # 测试集等级：沿用同一套聚类中心（最近中心法），保证口径一致
    test = test.copy()
    t_log = test[P.TARGET_LOG].values.reshape(-1, 1)
    centers = np.sort(km.cluster_centers_.ravel())
    test["grade"] = np.array([int(np.argmin(np.abs(centers - v))) for v in t_log])
    X_test, _, _ = build_features(test, maps, modes)
    y_test = test["grade"].values

    results = []
    best = None
    for name in ["lgbm", "rf", "lr"]:
        model, metrics, pred = train_classifier(name, X_train, y_train, X_test, y_test)
        results.append(metrics)
        if name == "lgbm":
            best = model
            _confusion_fig(y_test, pred, names, os.path.join(FIG_DIR, "grade_confusion.png"))
            joblib.dump({"model": model, "cat_maps": maps, "cat_modes": modes,
                         "names": names, "thresholds": thresholds},
                        os.path.join(CACHE_DIR, "grade_lgbm.joblib"), compress=3)

    # 各等级热度区间与分布
    dist = {}
    for i, n in enumerate(names):
        sel = train[train["grade"] == i]["heat"]
        dist[n] = {"count": int(len(sel)),
                   "min": float(sel.min()), "max": float(sel.max()),
                   "mean": float(sel.mean())}

    # 分级分布图
    fig, ax = plt.subplots(figsize=(7, 5))
    counts = [dist[n]["count"] for n in names]
    ax.bar(names, counts, color="#55A868")
    ax.set_ylabel("样本数")
    ax.set_title("热度等级分布（K-Means 聚类）")
    for i, c in enumerate(counts):
        ax.text(i, c, str(c), ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "grade_distribution.png"), dpi=130)
    plt.close(fig)

    return {
        "mode": "grade",
        "k": k,
        "grade_names": names,
        "thresholds": thresholds,
        "silhouette": sil,
        "distribution": dist,
        "classifier_metrics": sorted(results, key=lambda r: -r["macro_f1"]),
        "figures": ["grade_confusion.png", "grade_distribution.png"],
    }


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main():
    try:
        parser = _Parser(prog="grade_cluster.py")
        parser.add_argument("--k", type=int, default=3, choices=[3, 4, 5])
        args = parser.parse_args()
        print(json.dumps(run(args.k), ensure_ascii=False))
        sys.exit(0)
    except BaseException as exc:  # noqa: BLE001
        if isinstance(exc, SystemExit) and exc.code == 0:
            raise
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc()}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    _stdout_reconfigure()
    main()
