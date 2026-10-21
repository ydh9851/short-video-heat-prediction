# -*- coding: utf-8 -*-
"""
growth_predict.py —— 短视频热度增长曲线预测
============================================
数据来源：TikTok 真实「每日累计」快照（data/raw/tiktok_engagement_daily.parquet），
每个视频在发布后第 0~30 天各有一次累计互动快照，共 20.9 万条视频。

核心问题（业务含义）：
    一条新视频刚发布，用「发布后 0~1 天」的早期热度，能否预测它
    发布后 1 / 3 / 7 天的累计热度？从而在冷启动期判断一条内容是否值得继续投放。

热度口径与系统一致：heat = 播放量 + 3×点赞 + 5×评论 + 8×转发。

输出（单行 JSON，供 Java 后端 ProcessBuilder 解析）：
    {"mode":"growth","n_videos":...,"horizons":[...],"curve":{...},"figure":...}
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

BASE = os.path.dirname(os.path.abspath(__file__))               # .../algorithm/prediction
ALGO_DIR = os.path.dirname(BASE)
SYSTEM_ROOT = os.path.dirname(ALGO_DIR)
RAW_PARQUET = os.path.join(SYSTEM_ROOT, "data", "raw", "tiktok_engagement_daily.parquet")
PROCESSED_DIR = os.path.join(SYSTEM_ROOT, "data", "processed")
GROWTH_CSV = os.path.join(PROCESSED_DIR, "tiktok_growth.csv")
FIG_DIR = os.path.join(ALGO_DIR, "evaluation", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

RANDOM_STATE = 42
HORIZONS = (1, 3, 7)                 # 预测目标：发布后第 1 / 3 / 7 天累计热度
REQUIRED_DAYS = (0, 1, 3, 7)         # 必须齐全的天数（保证口径一致）


def _stdout_reconfigure():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _heat_expr():
    return ("play_count + 3 * like_count + 5 * comment_count + 8 * share_count")


def build_growth_table(force=False):
    """从原始 parquet 汇总出「每视频一行的累计热度表」，并缓存为 CSV。"""
    if os.path.exists(GROWTH_CSV) and not force:
        if os.path.getmtime(GROWTH_CSV) >= os.path.getmtime(RAW_PARQUET):
            return pd.read_csv(GROWTH_CSV)
    if not os.path.exists(RAW_PARQUET):
        raise FileNotFoundError("未找到 TikTok 每日快照：%s" % RAW_PARQUET)

    cols = ["video_id", "days_since_post", "play_count", "like_count",
            "comment_count", "share_count"]
    df = pd.read_parquet(RAW_PARQUET, columns=cols)
    df["heat"] = df.eval(_heat_expr())
    pv = df.pivot_table(index="video_id", columns="days_since_post",
                        values="heat", aggfunc="max")
    keep = [d for d in REQUIRED_DAYS if d in pv.columns]
    pv = pv.dropna(subset=keep)
    out = pd.DataFrame({"video_id": pv.index})
    for d in sorted(int(x) for x in pv.columns):          # 缓存全部 0~30 天真实值
        out[f"h{d}"] = pv[d].values
    out = out.reset_index(drop=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    out.to_csv(GROWTH_CSV, index=False)
    print("[growth] built %d videos -> %s" % (len(out), GROWTH_CSV), file=sys.stderr)
    return out


def _fit_horizon(day, feats, table):
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import train_test_split

    y = np.log1p(table[f"h{day}"].astype(float).values)
    X = table[feats].astype(float).values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE)
    ds = lgb.Dataset(Xtr, label=ytr, free_raw_data=False)
    model = lgb.train({"objective": "regression", "metric": "rmse", "learning_rate": 0.05,
                       "num_leaves": 31, "feature_fraction": 0.9, "bagging_fraction": 0.9,
                       "bagging_freq": 5, "verbose": -1, "seed": RANDOM_STATE},
                      ds, num_boost_round=300)
    pred_log = model.predict(Xte)
    pred_raw, y_true = np.expm1(pred_log), np.expm1(yte)
    # 相对原始中位数 h1 的增长倍数
    mult = float(np.median(np.expm1(yte) / np.maximum(np.expm1(Xte[:, 0]), 1.0)))
    return {
        "day": day,
        "features": feats,
        "r2": float(r2_score(yte, pred_log)),
        "rmse_raw": float(np.sqrt(mean_squared_error(y_true, pred_raw))),
        "mae_raw": float(mean_absolute_error(y_true, pred_raw)),
        "median_multiplier": mult,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
    }, (y_true, pred_raw)


def mode_growth(sample=20000):
    """热度增长曲线预测：用 0~1 天早期热度预测第 1/3/7 天累计热度。"""
    table = build_growth_table()
    table = table.dropna(subset=["h0", "h1"])
    if len(table) > sample:
        table = table.sample(n=sample, random_state=RANDOM_STATE).reset_index(drop=True)
    table["l0"] = np.log1p(table["h0"].astype(float))
    table["l1"] = np.log1p(table["h1"].astype(float))

    horizons, preds = [], {}
    for day in HORIZONS:
        feats = ["l0"] if day == 1 else ["l0", "l1"]
        item, pa = _fit_horizon(day, feats, table)
        item["signal"] = "发布后第 0 天累计热度" if day == 1 else "发布后第 0~1 天累计热度"
        horizons.append(item)
        preds[day] = pa
        print(f"[growth] day{day}: R2={item['r2']:.4f} MAE={item['mae_raw']:.1f}", file=sys.stderr)

    # 典型增长曲线：参与统计视频在第 0~7 天的累计热度中位数 / 四分位
    curve_days = list(range(0, 8))
    curve = {"days": curve_days, "p25": [], "p50": [], "p75": []}
    base = table
    for d in curve_days:
        col = f"h{d}"
        if col not in base.columns:
            continue
        v = base[col].astype(float).dropna()
        curve["p25"].append(float(v.quantile(0.25)))
        curve["p50"].append(float(v.median()))
        curve["p75"].append(float(v.quantile(0.75)))

    # 可视化：左=典型增长曲线（对数轴），右=第 7 天预测 vs 真实
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    axes[0].plot(curve_days, curve["p50"], marker="o", color="#6366f1", label="中位数 P50")
    axes[0].fill_between(curve_days, curve["p25"], curve["p75"], color="#c7cbf7", alpha=.45,
                         label="P25~P75")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("发布后天数")
    axes[0].set_ylabel("累计热度（对数轴）")
    axes[0].set_title("TikTok 真实累计热度增长曲线")
    axes[0].grid(alpha=.25)
    axes[0].legend()

    y_true, pred_raw = preds[7]
    idx = np.random.RandomState(RANDOM_STATE).choice(
        len(y_true), size=min(4000, len(y_true)), replace=False)
    lo = max(1.0, float(np.percentile(np.concatenate([y_true[idx], pred_raw[idx]]), 1)))
    hi = float(np.percentile(np.concatenate([y_true[idx], pred_raw[idx]]), 99))
    axes[1].scatter(y_true[idx], pred_raw[idx], s=5, alpha=.28, color="#8b5cf6")
    axes[1].plot([lo, hi], [lo, hi], color="#ef4444", linewidth=1.6, label="理想线 y=x")
    axes[1].set_xscale("log")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("真实第 7 天累计热度")
    axes[1].set_ylabel("预测第 7 天累计热度")
    axes[1].set_title("第 7 天累计热度：预测 vs 真实")
    axes[1].grid(alpha=.25)
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "growth_forecast.png"), dpi=130)
    plt.close(fig)

    ref = horizons[-1]
    return {
        "mode": "growth",
        "n_videos": int(len(table)),
        "sample_used": int(len(table)),
        "source": "TikTok 每日累计快照（真实，第 0~30 天）",
        "horizons": horizons,
        "curve": curve,
        "figure": "growth_forecast.png",
        "summary": {
            "day7_r2": ref["r2"],
            "day7_mae_raw": ref["mae_raw"],
            "day7_median_multiplier": ref["median_multiplier"],
        },
    }


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main():
    try:
        parser = _Parser(prog="growth_predict.py")
        parser.add_argument("--build", action="store_true", help="仅重建增长表后退出")
        parser.add_argument("--sample", type=int, default=20000)
        args = parser.parse_args()

        if args.build:
            t = build_growth_table(force=True)
            print(json.dumps({"mode": "build", "n_videos": int(len(t))}, ensure_ascii=False))
            sys.exit(0)

        print(json.dumps(mode_growth(sample=args.sample), ensure_ascii=False))
        sys.exit(0)
    except BaseException as exc:  # noqa: BLE001
        if isinstance(exc, SystemExit) and exc.code == 0:
            raise
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc()}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    _stdout_reconfigure()
    main()
