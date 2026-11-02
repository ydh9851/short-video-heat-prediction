"""
特征增量实验（Feature Enrichment）：验证「加维度比加样本更有效」这一判断。

做法：用本地已有的 YouTube 趋势数据集（450K 行、28 列，含标题/描述/标签/时长/频道统计），
构造三组特征集，在**同一份数据、同一套 CV、同一个模型**下对照：

  A. base      —— 只有「发布时即可获得」的粗粒度先验（时段/星期/月份/类别/频道粉丝）
  B. +content  —— base 之外再加内容属性（视频时长 / 标题长度 / 描述长度 / 标签数量 / 频道年龄）
  C. +text     —— 在 B 之上再加标题文本向量（TF-IDF → SVD 32 维）

目标口径：heat = 浏览量 + 3×点赞 + 5×评论（YouTube 无转发字段），训练目标 log1p(heat)。
防泄漏：点赞/评论/浏览量本身是目标组成部分，一律不进特征；频道订阅数取首次上榜快照。

输出单行 JSON，含三组特征的 R²(log)/RMSE/MAE 与增益，可直接作为论文「特征体系设计」一节的证据。

CLI：
  python feature_enrichment.py --folds 5 [--sample 200000]
"""
import argparse
import json
import os
import sys
import traceback

import numpy as np
import pandas as pd

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_ROOT = os.path.dirname(os.path.dirname(EVAL_DIR))
PRED_DIR = os.path.join(SYSTEM_ROOT, "algorithm", "prediction")
sys.path.insert(0, PRED_DIR)

RAW_CSV = os.path.join(SYSTEM_ROOT, "data", "raw", "youtube_trending.csv")
CACHE_PARQUET = os.path.join(SYSTEM_ROOT, "data", "processed", "youtube_rich.parquet")
SEED = 42

USECOLS = [
    "video_id", "video_published_at", "video_trending__date", "video_category_id",
    "video_title", "video_description", "video_tags", "video_duration",
    "video_view_count", "video_like_count", "video_comment_count",
    "channel_subscriber_count", "channel_video_count", "channel_published_at",
]


def _build_dataset():
    """把原始 CSV 压成一张「一行一条视频」的宽表并缓存（首次约 1 分钟，之后秒级）。"""
    if os.path.exists(CACHE_PARQUET):
        return pd.read_parquet(CACHE_PARQUET), False

    if not os.path.isfile(RAW_CSV):
        raise FileNotFoundError("缺少 data/raw/youtube_trending.csv（README「数据获取」一节有下载说明）")

    df = pd.read_csv(RAW_CSV, usecols=lambda c: c in USECOLS, low_memory=False)
    df["published"] = pd.to_datetime(df["video_published_at"], errors="coerce")
    df["trend_date"] = pd.to_datetime(df["video_trending__date"], errors="coerce")
    # 同一条视频可能连续多天在榜：取「首次上榜」快照，避免同一视频重复计入
    df = df.sort_values("trend_date").drop_duplicates(subset=["video_id"], keep="first")

    for col in ["video_view_count", "video_like_count", "video_comment_count",
                "channel_subscriber_count", "channel_video_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 目标：加权互动量（与抖音口径一致，YouTube 无转发字段）
    df["heat"] = (df["video_view_count"].fillna(0)
                  + 3 * df["video_like_count"].fillna(0)
                  + 5 * df["video_comment_count"].fillna(0))
    df = df[df["heat"] > 0]

    # 时长：ISO8601（PT1M30S / PT45S）→ 秒
    df["duration_sec"] = df["video_duration"].fillna("").map(_iso_duration)

    pub = df["published"]
    df["publish_hour"] = pub.dt.hour.fillna(-1)
    df["publish_weekday"] = pub.dt.weekday.fillna(-1)
    df["publish_month"] = pub.dt.month.fillna(-1)
    df["is_weekend"] = df["publish_weekday"].isin([5, 6]).astype(int)
    df["category"] = df["video_category_id"].fillna("NA").astype(str)

    df["sub_log"] = np.log1p(df["channel_subscriber_count"].clip(lower=0).fillna(0))
    df["channel_videos_log"] = np.log1p(df["channel_video_count"].clip(lower=0).fillna(0))
    ch_pub = pd.to_datetime(df["channel_published_at"], errors="coerce")
    df["channel_age_days"] = (pub - ch_pub).dt.days.clip(lower=0).fillna(-1)

    df["title_len"] = df["video_title"].fillna("").str.len()
    df["desc_len"] = df["video_description"].fillna("").str.len()
    df["tags_count"] = df["video_tags"].fillna("").map(
        lambda s: 0 if not isinstance(s, str) or not s.strip() or s == "[none]" else len(s.split("|")))
    df["title"] = df["video_title"].fillna("")
    df["heat_log"] = np.log1p(df["heat"].clip(upper=1e12))

    keep = ["video_id", "category", "publish_hour", "publish_weekday", "publish_month",
            "is_weekend", "sub_log", "channel_videos_log", "channel_age_days",
            "duration_sec", "title_len", "desc_len", "tags_count", "title",
            "heat", "heat_log"]
    out = df[keep].reset_index(drop=True)

    os.makedirs(os.path.dirname(CACHE_PARQUET), exist_ok=True)
    out.to_parquet(CACHE_PARQUET, index=False, compression="zstd")
    return out, True


def _iso_duration(text):
    """解析 ISO 8601 时长（PT1H2M3S）为秒；解析失败返回 -1。"""
    if not isinstance(text, str) or not text.startswith("PT"):
        return -1
    body = text[2:]
    seconds, num = 0, ""
    for ch in body:
        if ch.isdigit():
            num += ch
        elif ch in "HMS":
            if not num:
                return -1
            n = int(num)
            seconds += n * {"H": 3600, "M": 60, "S": 1}[ch]
            num = ""
        else:
            return -1
    return seconds


BASE_COLS = ["publish_hour", "publish_weekday", "publish_month", "is_weekend",
             "sub_log", "channel_videos_log", "channel_age_days"]
CONTENT_COLS = ["duration_sec", "title_len", "desc_len", "tags_count"]


def _text_features(titles, dim=32):
    """标题文本 → TF-IDF → SVD 降维（无监督，不接触目标变量）。"""
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(max_features=30000, min_df=5, ngram_range=(1, 2),
                          sublinear_tf=True, stop_words="english")
    mat = vec.fit_transform(titles)
    if mat.shape[1] <= dim:
        return mat.toarray(), 0
    svd = TruncatedSVD(n_components=dim, random_state=SEED)
    return svd.fit_transform(mat), dim


def _cv_eval(X, y, folds, categories=None):
    """5 折交叉验证，LightGBM 回归，返回 log 空间指标。"""
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import KFold

    params = {"objective": "regression", "metric": "rmse", "boosting_type": "gbdt",
              "learning_rate": 0.05, "num_leaves": 31, "feature_fraction": 0.8,
              "bagging_fraction": 0.8, "bagging_freq": 5, "verbose": -1}
    cat_idx = [X.columns.get_loc(c) for c in (categories or [])]
    kf = KFold(n_splits=folds, shuffle=True, random_state=SEED)
    r2s, rmses, maes = [], [], []
    for tr, te in kf.split(X):
        ds = lgb.Dataset(X.iloc[tr], label=y[tr], categorical_feature=cat_idx or "auto",
                         free_raw_data=False)
        model = lgb.train(params, ds, num_boost_round=400)
        pred = model.predict(X.iloc[te])
        r2s.append(r2_score(y[te], pred))
        rmses.append(float(np.sqrt(mean_squared_error(y[te], pred))))
        maes.append(float(mean_absolute_error(y[te], pred)))
    return {"r2_mean": float(np.mean(r2s)), "r2_std": float(np.std(r2s)),
            "rmse_mean": float(np.mean(rmses)), "mae_mean": float(np.mean(maes))}


def run(folds=5, sample=None, text_dim=32):
    df, built = _build_dataset()
    if sample and sample < len(df):
        df = df.sample(n=int(sample), random_state=SEED).reset_index(drop=True)
    y = df["heat_log"].values.astype(float)

    results = []

    # A. 基础先验特征
    Xa = df[BASE_COLS + ["category"]].copy()
    Xa["category"] = Xa["category"].astype("category")
    results.append({"feature_set": "A 基础先验（7 维）", **( _cv_eval(Xa, y, folds, ["category"]))})

    # B. 追加内容属性
    Xb = df[BASE_COLS + CONTENT_COLS + ["category"]].copy()
    Xb["category"] = Xb["category"].astype("category")
    results.append({"feature_set": "B + 内容属性（11 维）", **(_cv_eval(Xb, y, folds, ["category"]))})

    # C. 再追加标题文本向量
    text_mat, used_dim = _text_features(df["title"].tolist(), text_dim)
    Xc = Xb.copy()
    for i in range(used_dim):
        Xc["txt_%02d" % i] = text_mat[:, i]
    results.append({"feature_set": "C + 标题文本（%d 维）" % (Xc.shape[1] - 1),
                    **(_cv_eval(Xc, y, folds, ["category"]))})

    base = results[0]
    for item in results:
        item["r2_gain_vs_base"] = round(item["r2_mean"] - base["r2_mean"], 4)
        item["rmse_gain_vs_base"] = round(base["rmse_mean"] - item["rmse_mean"], 4)
        item["r2_mean"] = round(item["r2_mean"], 4)
        item["r2_std"] = round(item["r2_std"], 4)
        item["rmse_mean"] = round(item["rmse_mean"], 4)
        item["mae_mean"] = round(item["mae_mean"], 4)

    return {
        "mode": "feature-enrichment",
        "source": "data/raw/youtube_trending.csv（首次上榜快照）",
        "cache_built_now": built,
        "rows": int(len(df)),
        "folds": folds,
        "target": "log1p(浏览量 + 3×点赞 + 5×评论)",
        "table": results,
        "summary": {
            "base_r2": base["r2_mean"],
            "content_r2": results[1]["r2_mean"],
            "text_r2": results[2]["r2_mean"],
            "content_gain": results[1]["r2_gain_vs_base"],
            "text_gain": round(results[2]["r2_mean"] - results[1]["r2_mean"], 4),
        },
        "note": "同一数据/同一 CV/同一模型下，仅改变特征集；文本向量由 TF-IDF+SVD 无监督生成，未使用目标变量",
    }


def main():
    ap = argparse.ArgumentParser(description="特征增量实验：base / +content / +text 三组对照")
    ap.add_argument("--mode", default="feature-enrichment")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--sample", type=int, default=None, help="可选下采样行数（调试用）")
    ap.add_argument("--text-dim", type=int, default=32)
    args = ap.parse_args()
    try:
        print(json.dumps(run(folds=args.folds, sample=args.sample, text_dim=args.text_dim),
                         ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc(),
                          "trace_id": os.environ.get("TRACE_ID")}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
