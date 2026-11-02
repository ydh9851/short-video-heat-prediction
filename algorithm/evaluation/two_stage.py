"""
两阶段热度预测（Two-Stage / Early-Signal Forecasting）

业务问题：短视频发布前的先验信息只能解释一部分热度，真正决定"能不能爆"的往往是
发布后最初 24~72 小时的传播势能。本脚本量化「早期互动信号」的增量价值：

  阶段一（发布时）：只用发布时即可获得的先验特征预测第 7 天热度 —— 对应系统现有能力；
  阶段二（发布后）：在阶段一基础上逐步加入第 1 天、第 3 天的真实累计互动，
                   观察 R² 与误差如何变化。

三组特征集（同一行子集、同一套 CV、同一个模型，保证可比）：
  A. prior        —— 时长 / 话题标签数 / 文案词数 / emoji / 发布时段 / 话题分类 / 作者粉丝
  B. prior + d1   —— 再加第 1 天累计热度的绝对值与速度
  C. prior + d1d3 —— 再加第 3 天累计热度与 1→3 天增速

数据口径：
  热度 heat = 播放 + 3×点赞 + 5×评论 + 8×转发（与抖音主实验一致）
  目标 = log1p(第 7 天累计 heat)
  防泄漏：预测第 7 天时，只允许使用 ≤ 第 3 天的信号；第 7 天自身的值绝不进特征。

CLI（单行 JSON）：
  python two_stage.py --folds 5 [--sample 100000]
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
RAW = os.path.join(SYSTEM_ROOT, "data", "raw")
CACHE = os.path.join(SYSTEM_ROOT, "data", "processed", "tiktok_two_stage.parquet")
SEED = 42

ENG = os.path.join(RAW, "tiktok_engagement_daily.parquet")
VID = os.path.join(RAW, "tiktok_videos_full.parquet")
CREATOR = os.path.join(RAW, "tiktok_creator_daily.parquet")


def _build_dataset():
    """把「视频 × 天数」的累计互动压成一行一条视频的宽表（首次约 1 分钟，之后秒级）。"""
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE), False
    for path in (ENG, VID):
        if not os.path.isfile(path):
            raise FileNotFoundError("缺少 " + os.path.basename(path) + "（见 README「数据获取」）")

    eng = pd.read_parquet(ENG, columns=["video_id", "days_since_post", "play_count",
                                        "like_count", "comment_count", "share_count"])
    for col in ["play_count", "like_count", "comment_count", "share_count"]:
        eng[col] = pd.to_numeric(eng[col], errors="coerce").fillna(0)
    eng["heat"] = (eng["play_count"] + 3 * eng["like_count"]
                   + 5 * eng["comment_count"] + 8 * eng["share_count"])

    # 透视成「每条视频一行、每天一列」，累计量单调不减，故按天数排序后前向填充
    wide = eng.pivot_table(index="video_id", columns="days_since_post", values="heat", aggfunc="last")
    wide = wide.sort_index(axis=1).ffill(axis=1)

    def day(d):
        return wide[d] if d in wide.columns else pd.Series(np.nan, index=wide.index)

    traj = pd.DataFrame({
        "h0": day(0), "h1": day(1), "h3": day(3), "h7": day(7),
    }, index=wide.index)

    vids = pd.read_parquet(VID, columns=["video_id", "author_id", "create_date", "duration",
                                         "hashtag_count", "word_count", "emoji_count", "topic"])
    vids["create_ts"] = pd.to_datetime(vids["create_date"], errors="coerce")
    vids["create_hour"] = vids["create_ts"].dt.hour
    vids["create_weekday"] = vids["create_ts"].dt.weekday
    vids["is_weekend"] = vids["create_weekday"].isin([5, 6]).astype(int)

    # 作者发布时的粉丝数：按作者 + 时间取「发布日或之前最近一次」快照
    try:
        cd = pd.read_parquet(CREATOR, columns=["author_id", "date", "follower_count"])
        cd["date"] = pd.to_datetime(cd["date"], errors="coerce")
        cd = cd.dropna(subset=["date"]).sort_values("date")
        vids = pd.merge_asof(vids.sort_values("create_ts"), cd, left_on="create_ts",
                             right_on="date", by="author_id", direction="backward")
        vids["followers_log"] = np.log1p(pd.to_numeric(vids["follower_count"], errors="coerce")
                                        .clip(lower=0).fillna(0))
    except Exception:
        # 创作者表缺失时退化为 0，实验仍可跑通
        vids["followers_log"] = 0.0

    out = vids.merge(traj, left_on="video_id", right_index=True, how="inner")
    out["topic"] = out["topic"].fillna("NA").astype(str)
    out["duration"] = pd.to_numeric(out["duration"], errors="coerce").fillna(0)
    for c in ["hashtag_count", "word_count", "emoji_count"]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)

    # 至少要有第 1、3、7 天的观测，才能做「同子集」对照
    out = out.dropna(subset=["h1", "h3", "h7"])
    out = out[out["h7"] > 0]

    out["y7"] = np.log1p(out["h7"].clip(upper=1e12))
    out["h1_log"] = np.log1p(out["h1"].clip(lower=0))
    out["h3_log"] = np.log1p(out["h3"].clip(lower=0))
    # 第 1 天的传播速度（每小时热度）与 1→3 天增速，刻画「势能」而非绝对量
    out["v1"] = out["h1"] / 24.0
    out["growth_1_3"] = out["h3_log"] - out["h1_log"]

    keep = ["video_id", "topic", "duration", "hashtag_count", "word_count", "emoji_count",
            "create_hour", "create_weekday", "is_weekend", "followers_log",
            "h1", "h3", "h7", "h1_log", "h3_log", "v1", "growth_1_3", "y7"]
    out = out[keep].reset_index(drop=True)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    out.to_parquet(CACHE, index=False, compression="zstd")
    return out, True


PRIOR_COLS = ["duration", "hashtag_count", "word_count", "emoji_count",
              "create_hour", "create_weekday", "is_weekend", "followers_log", "topic"]
D1_COLS = ["h1_log", "v1"]
D3_COLS = ["h3_log", "growth_1_3"]


def _cv_eval(X, y, folds, cat_cols):
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import KFold

    params = {"objective": "regression", "metric": "rmse", "boosting_type": "gbdt",
              "learning_rate": 0.05, "num_leaves": 31, "feature_fraction": 0.8,
              "bagging_fraction": 0.8, "bagging_freq": 5, "verbose": -1}
    cat_idx = [X.columns.get_loc(c) for c in cat_cols if c in X.columns]
    kf = KFold(n_splits=folds, shuffle=True, random_state=SEED)
    r2s, rmses, maes, rels = [], [], [], []
    y_raw = np.expm1(y)
    for tr, te in kf.split(X):
        ds = lgb.Dataset(X.iloc[tr], label=y[tr], categorical_feature=cat_idx or "auto",
                         free_raw_data=False)
        model = lgb.train(params, ds, num_boost_round=400)
        pred = model.predict(X.iloc[te])
        r2s.append(r2_score(y[te], pred))
        rmses.append(float(np.sqrt(mean_squared_error(y[te], pred))))
        maes.append(float(mean_absolute_error(y[te], pred)))
        # 原始空间的相对误差中位数：业务方更关心「多数视频误差多大」
        pred_raw = np.expm1(pred)
        with np.errstate(divide="ignore", invalid="ignore"):
            rel = np.abs(pred_raw - y_raw[te]) / np.maximum(y_raw[te], 1.0)
        rels.append(float(np.nanmedian(rel)))
    return {"r2_mean": float(np.mean(r2s)), "r2_std": float(np.std(r2s)),
            "rmse_mean": float(np.mean(rmses)), "mae_mean": float(np.mean(maes)),
            "rel_err_p50": float(np.mean(rels))}


def run(folds=5, sample=None):
    df, built = _build_dataset()
    if sample and sample < len(df):
        df = df.sample(n=int(sample), random_state=SEED).reset_index(drop=True)
    y = df["y7"].values.astype(float)

    results = []

    Xa = df[PRIOR_COLS].copy()
    Xa["topic"] = Xa["topic"].astype("category")
    results.append({"feature_set": "A 仅发布时先验", "n_features": Xa.shape[1],
                    **(_cv_eval(Xa, y, folds, ["topic"]))})

    Xb = df[PRIOR_COLS + D1_COLS].copy()
    Xb["topic"] = Xb["topic"].astype("category")
    results.append({"feature_set": "B 先验 + 第 1 天信号", "n_features": Xb.shape[1],
                    **(_cv_eval(Xb, y, folds, ["topic"]))})

    Xc = df[PRIOR_COLS + D1_COLS + D3_COLS].copy()
    Xc["topic"] = Xc["topic"].astype("category")
    results.append({"feature_set": "C 先验 + 第 1、3 天信号", "n_features": Xc.shape[1],
                    **(_cv_eval(Xc, y, folds, ["topic"]))})

    base = results[0]
    for item in results:
        item["r2_gain_vs_prior"] = round(item["r2_mean"] - base["r2_mean"], 4)
        item["r2_mean"] = round(item["r2_mean"], 4)
        item["r2_std"] = round(item["r2_std"], 4)
        item["rmse_mean"] = round(item["rmse_mean"], 4)
        item["mae_mean"] = round(item["mae_mean"], 4)
        item["rel_err_p50"] = round(item["rel_err_p50"], 4)

    return {
        "mode": "two-stage",
        "source": "data/raw/tiktok_engagement_daily.parquet（第 0~30 天累计快照）",
        "cache_built_now": built,
        "rows": int(len(df)),
        "folds": folds,
        "target": "log1p(第 7 天累计 heat)，heat = 播放 + 3×点赞 + 5×评论 + 8×转发",
        "table": results,
        "summary": {
            "prior_r2": base["r2_mean"],
            "d1_r2": results[1]["r2_mean"],
            "d1d3_r2": results[2]["r2_mean"],
            "d1_gain": round(results[1]["r2_mean"] - base["r2_mean"], 4),
            "d3_gain": round(results[2]["r2_mean"] - results[1]["r2_mean"], 4),
            "prior_rel_err_p50": base["rel_err_p50"],
            "d1d3_rel_err_p50": results[2]["rel_err_p50"],
        },
        "note": "三组特征集使用同一行子集（同时具备第 1/3/7 天观测）与同一 CV 划分，"
                "差异只来自早期信号；第 7 天自身数值不参与任何特征",
    }


def main():
    ap = argparse.ArgumentParser(description="两阶段热度预测：先验 vs +第1天 vs +第1/3天信号")
    ap.add_argument("--mode", default="two-stage")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--sample", type=int, default=None)
    args = ap.parse_args()
    try:
        print(json.dumps(run(folds=args.folds, sample=args.sample), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc(),
                          "trace_id": os.environ.get("TRACE_ID")}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
