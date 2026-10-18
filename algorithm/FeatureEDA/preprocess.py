# -*- coding: utf-8 -*-
"""
数据清洗与特征工程脚本（短视频热度预测与归因分析系统）
====================================================
本脚本为系统的共享流水线，供以下模块复用：
    1) 特征探索分析 EDA（algorithm/FeatureEDA/eda.py）
    2) 热度预测（algorithm/prediction/predict_api.py）
    3) 归因分析（algorithm/attribution/shap_analysis.py）

数据集（抖音公开短视频数据集 douyin_video_data.xlsx，45476 行 × 9 列）原始字段：
    视频ID / 视频类别 / 作者粉丝数 / 播放量 / 点赞量 / 评论量 / 转发量 / 收藏量 / 发布时间

预测目标（热度 heat，加权互动量）：
    heat = 播放量 + 3×点赞量 + 5×评论量 + 8×转发量
    长尾严重（中位数约 3.4e2、最大 2.7e8），建模前做 log1p 变换，推理时 expm1 还原。

特征工程原则（防数据泄漏，重要）：
    播放量 / 点赞量 / 评论量 / 转发量 / 收藏量 都是热度目标的组成部分，
    属于"结果变量"，**不能作为特征**，否则模型只是把目标换个方式还原，预测失去意义。
    因此只使用「视频发布时即可获得」的先验信息：
        - 视频类别 video_category（类别特征）
        - 作者粉丝数 author_fans（数值，做 log1p 缓解量纲/长尾）
        - 发布时间派生：publish_hour / publish_weekday / publish_month / is_weekend / hour_bucket

用法：
    python algorithm/FeatureEDA/preprocess.py     # 运行并将结果存到 data/processed
    from preprocess import build_data             # 供 EDA/建模脚本 import 复用
"""
import os
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

# ---- 系统工程目录常量（基于脚本自身位置定位，任意目录执行均可） ----
#   short-video-heat-prediction/
#   ├── data/
#   │   ├── raw/                # 原始数据（douyin_video_data.xlsx）
#   │   ├── train.csv           # 带 heat 标签的训练样本
#   │   └── processed/          # 清洗产物（各算法模块共享）
#   └── algorithm/
#       └── FeatureEDA/         # 本模块所在
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))    # .../algorithm/FeatureEDA
ALGO_DIR = os.path.dirname(SCRIPT_DIR)                     # .../algorithm
SYSTEM_ROOT = os.path.dirname(ALGO_DIR)                    # 系统根目录
DATA_DIR = os.path.join(SYSTEM_ROOT, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# 原始中文字段 -> 规范英文列名
RAW_MAP = {
    "视频ID": "video_id",
    "视频类别": "video_category",
    "作者粉丝数": "author_fans",
    "播放量": "play_cnt",
    "点赞量": "like_cnt",
    "评论量": "comment_cnt",
    "转发量": "share_cnt",
    "收藏量": "collect_cnt",
    "发布时间": "publish_time",
}

# 建模实际使用的特征（顺序固定，predict_api / 归因分析保持一致）
CAT_FEATURES = ["video_category", "hour_bucket"]
NUM_FEATURES = ["author_fans_log", "publish_hour", "publish_weekday", "publish_month", "is_weekend"]
FEATURE_NAMES = NUM_FEATURES + CAT_FEATURES
TARGET_RAW = "heat"
TARGET_LOG = "heat_log"


def _hour_bucket(h: float) -> str:
    """把发布小时粗分时段：凌晨/上午/下午/晚间，作为类别特征"""
    if pd.isna(h):
        return "未知"
    h = int(h)
    if 0 <= h < 6:
        return "凌晨(0-5)"
    if 6 <= h < 12:
        return "上午(6-11)"
    if 12 <= h < 18:
        return "下午(12-17)"
    return "晚间(18-23)"


def preprocess(df: pd.DataFrame, is_train: bool = True) -> pd.DataFrame:
    """清洗 + 特征工程。返回带特征与目标列（train 时含 heat/heat_log）的 DataFrame。"""
    df = df.rename(columns=RAW_MAP).copy()

    # ---------- 1. 日期解析与时间派生特征 ----------
    df["publish_time"] = pd.to_datetime(df["publish_time"], errors="coerce")
    dt = df["publish_time"].dt
    df["publish_hour"] = dt.hour.astype("float")
    df["publish_weekday"] = dt.weekday.astype("float")   # 0=周一 ... 6=周日
    df["publish_month"] = dt.month.astype("float")
    df["is_weekend"] = dt.weekday.isin([5, 6]).astype("int")
    df["hour_bucket"] = df["publish_hour"].apply(_hour_bucket)

    # ---------- 2. 数值清洗 ----------
    df["author_fans"] = pd.to_numeric(df["author_fans"], errors="coerce").clip(lower=0)
    fans_median = df["author_fans"].median()
    df["author_fans"] = df["author_fans"].fillna(0.0 if pd.isna(fans_median) else fans_median)
    df["author_fans_log"] = np.log1p(df["author_fans"])

    # ---------- 3. 类别特征缺失兜底 ----------
    df["video_category"] = df["video_category"].fillna("未知").astype(str)

    # ---------- 4. 目标变量：热度（加权互动量）与 log1p ----------
    if is_train:
        if TARGET_RAW in df.columns:
            df[TARGET_RAW] = pd.to_numeric(df[TARGET_RAW], errors="coerce")
            df.loc[df[TARGET_RAW] < 0, TARGET_RAW] = np.nan
            df[TARGET_RAW] = df[TARGET_RAW].fillna(df[TARGET_RAW].median())
        else:
            # 未带 heat 时按定义计算：播放 + 3×点赞 + 5×评论 + 8×转发
            df[TARGET_RAW] = (df["play_cnt"] + 3 * df["like_cnt"]
                              + 5 * df["comment_cnt"] + 8 * df["share_cnt"]).astype(float)
        df[TARGET_LOG] = np.log1p(df[TARGET_RAW])

    # ---------- 5. 时间异常兜底 ----------
    df["publish_hour"] = df["publish_hour"].fillna(-1)
    df["publish_weekday"] = df["publish_weekday"].fillna(-1)
    df["publish_month"] = df["publish_month"].fillna(-1)

    return df


def build_data(test_size: float = 0.2, random_state: int = 42):
    """构建并返回清洗后的 train / test，同时落盘到 data/processed（跨模块共享）。"""
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    raw = pd.read_csv(os.path.join(DATA_DIR, "train.csv"))
    full = preprocess(raw, is_train=True)

    # 按 8:2 划分训练/测试集（固定随机种子，保证实验可复现）
    rng = np.random.RandomState(random_state)
    idx = rng.permutation(len(full))
    n_test = int(len(full) * test_size)
    test_idx, train_idx = idx[:n_test], idx[n_test:]
    train, test = full.iloc[train_idx].copy(), full.iloc[test_idx].copy()

    train.to_csv(os.path.join(PROCESSED_DIR, "train_clean.csv"), index=False, encoding="utf-8-sig")
    test.to_csv(os.path.join(PROCESSED_DIR, "test_clean.csv"), index=False, encoding="utf-8-sig")
    return train, test


def _summary(df: pd.DataFrame, name: str):
    print(f"\n[cleaned {name}] shape = {df.shape}")
    print(f"类别数: {df['video_category'].nunique()}  时段分布: "
          f"{df['hour_bucket'].value_counts().to_dict()}")
    print(f"粉丝数中位数: {df['author_fans'].median():.0f}  "
          f"热度中位数: {df[TARGET_RAW].median():.0f}  最大: {df[TARGET_RAW].max():.0f}")
    print(f"特征列: {FEATURE_NAMES}")


if __name__ == "__main__":
    train, test = build_data()
    _summary(train, "train")
    _summary(test, "test")
    print(f"\n处理结果已保存到: {PROCESSED_DIR}")
    print("train_clean.csv / test_clean.csv")
