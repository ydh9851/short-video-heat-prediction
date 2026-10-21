# -*- coding: utf-8 -*-
"""
TikTok 多表聚合脚本
===================
把 HuggingFace tiktok-video-engagement-200k 数据集的三个 parquet 文件
join 成统一的 TikTok 视频主表，输出到 data/raw/tiktok_videos.csv，
供 ingest.py 直接导入。

输入（data/raw 下已归档的原始表）：
    - tiktok_videos_full.parquet   视频主表（209K 条）
    - tiktok_engagement_daily.parquet 每日互动快照（606 万行，累计值）
    - tiktok_creator_daily.parquet 创作者每日粉丝快照（27.8 万行）

输出：
    data/raw/tiktok_videos.csv  统一视频表（含 30 天累计互动 + 最新粉丝数）
"""
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
OUTPUT_PATH = os.path.join(RAW_DIR, "tiktok_videos.csv")

os.makedirs(RAW_DIR, exist_ok=True)

print("[1/4] Loading tiktok_videos_full.parquet ...")
videos = pd.read_parquet(os.path.join(RAW_DIR, "tiktok_videos_full.parquet"))
print(f"    -> {len(videos)} videos, columns: {list(videos.columns)}")

print("[2/4] Aggregating tiktok_engagement_daily.parquet (取每视频 days_since_post 最大的累计快照) ...")
ed = pd.read_parquet(os.path.join(RAW_DIR, "tiktok_engagement_daily.parquet"))
# 取每视频最后一天（累计最大）的互动值
idx = ed.groupby("video_id")["days_since_post"].idxmax()
engagement = ed.loc[idx, ["video_id", "play_count", "like_count",
                          "comment_count", "share_count", "collect_count"]].copy()
print(f"    -> {len(engagement)} unique videos with engagement")

print("[3/4] Aggregating tiktok_creator_daily.parquet (取每 author 最新 date 的 follower_count) ...")
cd = pd.read_parquet(os.path.join(RAW_DIR, "tiktok_creator_daily.parquet"))
idx2 = cd.groupby("author_id")["date"].idxmax()
creators = cd.loc[idx2, ["author_id", "follower_count"]].copy()
print(f"    -> {len(creators)} unique creators")

print("[4/4] Joining all tables ...")
df = videos.merge(engagement, on="video_id", how="left")
df = df.merge(creators, on="author_id", how="left")
print(f"    -> Final shape: {df.shape}")

# 提取我们需要的列，统一成 ingest.py 能识别的列名格式
result = pd.DataFrame({
    "video_id": df["video_id"].astype(str),
    "video_category": df["topic"].fillna(df["hashtags"].apply(
        lambda x: x[0]["hashtag_name"] if isinstance(x, list) and x else "未知")).astype(str),
    "author_fans": pd.to_numeric(df["follower_count"], errors="coerce").fillna(0).astype(float),
    "play_cnt": pd.to_numeric(df["play_count"], errors="coerce").fillna(0).astype(float),
    "like_cnt": pd.to_numeric(df["like_count"], errors="coerce").fillna(0).astype(float),
    "comment_cnt": pd.to_numeric(df["comment_count"], errors="coerce").fillna(0).astype(float),
    "share_cnt": pd.to_numeric(df["share_count"], errors="coerce").fillna(0).astype(float),
    "collect_cnt": pd.to_numeric(df["collect_count"], errors="coerce").fillna(0).astype(float),
    "publish_time": pd.to_datetime(df["create_time"], errors="coerce"),
})

# 过滤掉没有互动数据的（可能是新视频还没到快照时间）
before = len(result)
result = result[result["play_cnt"] > 0].copy()
print(f"    -> Drop zero-play videos: {before} -> {len(result)}")

result.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
print(f"\nDone! Saved to {OUTPUT_PATH}")
print(f"  Columns: {list(result.columns)}")
print(f"  Shape: {result.shape}")
print(f"  Play count stats: min={result['play_cnt'].min():.0f} median={result['play_cnt'].median():.0f} max={result['play_cnt'].max():.0f}")
print(f"  Category count: {result['video_category'].nunique()}")
print(f"  Fan count stats: median={result['author_fans'].median():.0f} max={result['author_fans'].max():.0f}")
