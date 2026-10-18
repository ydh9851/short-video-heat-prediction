# -*- coding: utf-8 -*-
"""
探索性数据分析（EDA）与特征可视化（短视频热度）
================================================
输入：data/processed/train_clean.csv（由 preprocess.py 生成），并辅以原始 train.csv 的互动分项
输出：algorithm/FeatureEDA/figures/ 下的分析图（PNG），供网页「数据探索分析」页直接引用。

运行：
    python algorithm/FeatureEDA/eda.py
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.stdout.reconfigure(encoding="utf-8")

import seaborn as sns

from preprocess import build_data, DATA_DIR, PROCESSED_DIR

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(SCRIPT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.dpi"] = 150
plt.rcParams["figure.facecolor"] = "white"

# 与 grading 模块一致的热度分级阈值（K-Means k=3）
GRADE_THRESHOLDS = [684.0, 15661.0]


def save(fig, name):
    fig.tight_layout()
    path = os.path.join(FIG_DIR, name)
    fig.savefig(path)
    plt.close(fig)
    print("saved", name)


def run():
    # 复用清洗流水线产物；不存在时现场构建
    train_path = os.path.join(PROCESSED_DIR, "train_clean.csv")
    if os.path.exists(train_path):
        df = pd.read_csv(train_path)
    else:
        df, _ = build_data()
    raw = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
    heat = df["heat"]

    # fig01 热度分布（原值 vs log1p）
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].hist(heat, bins=60, color="#4C72B0")
    axes[0].set_title("热度分布（原值，重尾）")
    axes[0].set_xlabel("heat = 播放 + 3×点赞 + 5×评论 + 8×转发")
    axes[0].set_ylabel("视频数")
    axes[1].hist(df["heat_log"], bins=60, color="#DD8452")
    axes[1].set_title("热度分布（log1p 变换后近似正态）")
    axes[1].set_xlabel("log1p(heat)")
    save(fig, "fig01_heat_distribution.png")

    # fig02 视频类别数量
    fig, ax = plt.subplots(figsize=(10, 5))
    vc = df["video_category"].value_counts()
    ax.bar(vc.index, vc.values, color="#55A868")
    ax.set_title("各视频类别样本数量")
    ax.set_ylabel("视频数")
    plt.xticks(rotation=30)
    save(fig, "fig02_category_count.png")

    # fig03 各类别平均热度
    fig, ax = plt.subplots(figsize=(10, 5))
    g = df.groupby("video_category")["heat"].mean().sort_values(ascending=False)
    ax.bar(g.index, g.values, color="#C44E52")
    ax.set_title("各视频类别平均热度")
    ax.set_ylabel("平均热度")
    plt.xticks(rotation=30)
    save(fig, "fig03_category_avg_heat.png")

    # fig04 各类别热度箱线图（log 空间）
    fig, ax = plt.subplots(figsize=(11, 5))
    order = df.groupby("video_category")["heat_log"].median().sort_values(ascending=False).index
    sns.boxplot(data=df, x="video_category", y="heat_log", order=order, ax=ax, showfliers=False)
    ax.set_title("各视频类别热度分布（log1p 空间）")
    ax.set_ylabel("log1p(heat)")
    plt.xticks(rotation=30)
    save(fig, "fig04_category_box.png")

    # fig05 作者粉丝数分布（log1p）
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(df["author_fans_log"], bins=60, color="#8172B3")
    ax.set_title("作者粉丝数分布（log1p）")
    ax.set_xlabel("log1p(粉丝数)")
    ax.set_ylabel("视频数")
    save(fig, "fig05_fans_distribution.png")

    # fig06 粉丝数 vs 热度（log-log 散点）
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.scatter(df["author_fans_log"], df["heat_log"], s=3, alpha=0.15, color="#4C72B0")
    ax.set_xlabel("log1p(作者粉丝数)")
    ax.set_ylabel("log1p(热度)")
    ax.set_title("作者粉丝数 与 热度 的关系")
    save(fig, "fig06_fans_vs_heat.png")

    # fig07 发布小时 → 平均热度
    fig, ax = plt.subplots(figsize=(10, 4.5))
    h = df.groupby("publish_hour")["heat"].mean()
    ax.plot(h.index, h.values, marker="o", color="#DD8452")
    ax.set_xlabel("发布小时")
    ax.set_ylabel("平均热度")
    ax.set_title("发布小时 与 平均热度")
    save(fig, "fig07_hour_avg_heat.png")

    # fig08 发布星期 → 平均热度
    fig, ax = plt.subplots(figsize=(9, 4.5))
    wd = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    w = df.groupby("publish_weekday")["heat"].mean()
    ax.bar([wd[int(i)] for i in w.index], w.values, color="#55A868")
    ax.set_ylabel("平均热度")
    ax.set_title("发布星期 与 平均热度")
    save(fig, "fig08_weekday_avg_heat.png")

    # fig09 发布月份 → 平均热度
    fig, ax = plt.subplots(figsize=(9, 4.5))
    m = df.groupby("publish_month")["heat"].mean()
    ax.bar([str(int(i)) + "月" for i in m.index], m.values, color="#C44E52")
    ax.set_ylabel("平均热度")
    ax.set_title("发布月份 与 平均热度")
    save(fig, "fig09_month_avg_heat.png")

    # fig10 发布时段 → 平均热度
    fig, ax = plt.subplots(figsize=(9, 4.5))
    b = df.groupby("hour_bucket")["heat"].mean().sort_values(ascending=False)
    ax.bar(b.index, b.values, color="#8172B3")
    ax.set_ylabel("平均热度")
    ax.set_title("发布时段 与 平均热度")
    save(fig, "fig10_bucket_avg_heat.png")

    # fig11 特征相关性热力图
    fig, ax = plt.subplots(figsize=(7.5, 6))
    cols = ["author_fans_log", "publish_hour", "publish_weekday", "publish_month",
            "is_weekend", "heat_log"]
    corr = df[cols].corr()
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", ax=ax, center=0)
    ax.set_title("特征相关性热力图")
    save(fig, "fig11_correlation.png")

    # fig12 互动构成（相对播放量）
    fig, ax = plt.subplots(figsize=(9, 5))
    components = ["点赞量", "评论量", "转发量", "收藏量"]
    ratios = [float((raw[c] / raw["播放量"].replace(0, np.nan)).median() * 100) for c in components]
    ax.bar([c.replace("量", "率") for c in components], ratios, color="#4C72B0")
    ax.set_ylabel("中位比率（相对播放量，%）")
    ax.set_title("互动行为相对播放量的中位比率")
    save(fig, "fig12_interaction_ratio.png")

    # fig13 热度等级分布（按分级阈值）
    fig, ax = plt.subplots(figsize=(7.5, 5))
    labels = ["低热度(<684)", "中热度(684~15661)", "高热度(≥15661)"]
    counts = [int((heat < GRADE_THRESHOLDS[0]).sum()),
              int(((heat >= GRADE_THRESHOLDS[0]) & (heat < GRADE_THRESHOLDS[1])).sum()),
              int((heat >= GRADE_THRESHOLDS[1]).sum())]
    ax.bar(labels, counts, color=["#909399", "#E6A23C", "#F56C6C"])
    for i, c in enumerate(counts):
        ax.text(i, c, str(c), ha="center", va="bottom")
    ax.set_ylabel("视频数")
    ax.set_title("热度等级分布（K-Means 分级阈值）")
    save(fig, "fig13_grade_distribution.png")

    print("\nEDA 完成，输出目录:", FIG_DIR)


if __name__ == "__main__":
    run()
