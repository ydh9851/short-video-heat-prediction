# -*- coding: utf-8 -*-
"""
B 站（哔哩哔哩）视频数据采集脚本
=================================
Kaggle 上没有权威的大规模 B 站数据集，本脚本通过 B 站**公开接口**采集排行榜视频，
产出与抖音原始表结构一致的文件（data/raw/bilibili_video_data.csv），
之后可直接用 algorithm/datasets/ingest.py --platform bilibili 归一化入系统。

采集口径：
    视频ID / 视频类别（分区名）/ 作者粉丝数（UP 主粉丝数）/
    播放量 / 点赞量 / 评论量 / 转发量 / 收藏量 / 发布时间

接口：
    排行榜  https://api.bilibili.com/x/web-interface/ranking/v2?rid={分区}&type=all
    UP 粉丝 https://api.bilibili.com/x/relation/stat?vmid={mid}

用法：
    python algorithm/data_collection/bilibili_crawler.py                # 采集全部默认分区
    python algorithm/data_collection/bilibili_crawler.py --rids 0,4,36  # 只采集指定分区
    python algorithm/data_collection/bilibili_crawler.py --with-fans    # 额外逐 UP 主查询粉丝数（较慢）

注意：
    - 仅采集公开的排行榜元数据，不下载视频内容，请遵守 B 站 robots 与使用条款；
    - 请求间隔默认 1.2s，避免给接口造成压力；
    - 如需提高频率限制，可设置环境变量 BILI_SESSDATA 传入自己的登录 Cookie。
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))       # .../algorithm/data_collection
ALGO_DIR = os.path.dirname(SCRIPT_DIR)
SYSTEM_ROOT = os.path.dirname(ALGO_DIR)
RAW_DIR = os.path.join(SYSTEM_ROOT, "data", "raw")
OUT_PATH = os.path.join(RAW_DIR, "bilibili_video_data.csv")

RANK_API = "https://api.bilibili.com/x/web-interface/ranking/v2?rid={rid}&type=all"
FANS_API = "https://api.bilibili.com/x/relation/stat?vmid={mid}"

# 常用分区 rid -> 名称（与前台分区名保持一致，便于与抖音类别做跨平台对照）
RIDS = {
    0: "全站", 1: "动画", 3: "音乐", 4: "游戏", 5: "娱乐", 36: "科技",
    119: "鬼畜", 129: "舞蹈", 155: "时尚", 160: "生活", 168: "国创",
    181: "影视", 188: "数码", 199: "纪录片", 211: "美食", 217: "动物",
    223: "汽车", 234: "运动",
}

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json, text/plain, */*",
}
_sessdata = os.environ.get("BILI_SESSDATA")
if _sessdata:
    HEADERS["Cookie"] = "SESSDATA=" + _sessdata


def _get(url: str, retries: int = 3, timeout: int = 15) -> dict:
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:                       # 网络抖动 / 限流：退避重试
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"请求失败 {url}：{last}")


def fetch_rank(rid: int, sleep: float) -> list:
    """采集某分区排行榜（单次最多 100 条）。"""
    data = _get(RANK_API.format(rid=rid))
    if data.get("code") != 0:
        print(f"  [跳过] 分区 {RIDS.get(rid, rid)} 返回 code={data.get('code')} {data.get('message')}")
        return []
    items = (data.get("data") or {}).get("list") or []
    rows = []
    for it in items:
        stat = it.get("stat") or {}
        owner = it.get("owner") or {}
        rows.append({
            "视频ID": it.get("bvid") or it.get("aid"),
            "视频类别": it.get("tname") or RIDS.get(rid, "未知"),
            "作者粉丝数": None,                       # 稍后按需补
            "播放量": stat.get("view", 0),
            "点赞量": stat.get("like", 0),
            "评论量": stat.get("reply", 0),
            "转发量": stat.get("share", 0),
            "收藏量": stat.get("favorite", 0),
            "发布时间": (datetime.fromtimestamp(it["pubdate"]).strftime("%Y-%m-%d %H:%M:%S")
                     if it.get("pubdate") else ""),
            "_mid": owner.get("mid"),
            "_up": owner.get("name"),
        })
    print(f"  [{RIDS.get(rid, rid)}] 采集 {len(rows)} 条")
    time.sleep(sleep)
    return rows


def fill_fans(rows: list, sleep: float):
    """逐 UP 主查询粉丝数（同一 UP 只查一次）。"""
    cache = {}
    for r in rows:
        mid = r.get("_mid")
        if not mid or r.get("作者粉丝数") is not None:
            continue
        if mid not in cache:
            try:
                data = _get(FANS_API.format(mid=mid))
                cache[mid] = (data.get("data") or {}).get("follower") if data.get("code") == 0 else 0
            except Exception as e:
                print(f"    [警告] 查询 UP {mid} 粉丝数失败：{e}")
                cache[mid] = 0
            time.sleep(sleep)
        r["作者粉丝数"] = cache[mid]


def main():
    ap = argparse.ArgumentParser(description="B 站排行榜视频元数据采集")
    ap.add_argument("--rids", help="分区 rid，逗号分隔，默认全部分区")
    ap.add_argument("--with-fans", action="store_true",
                    help="逐 UP 主查询粉丝数（默认不查；不查时粉丝数留空由后续补全）")
    ap.add_argument("--sleep", type=float, default=1.2, help="请求间隔秒数，默认 1.2")
    ap.add_argument("--out", default=OUT_PATH, help="输出 CSV 路径")
    args = ap.parse_args()

    rids = ([int(x) for x in args.rids.split(",") if x.strip()] if args.rids
            else list(RIDS.keys()))

    print(f"开始采集 B 站排行榜：{len(rids)} 个分区")
    all_rows = []
    for rid in rids:
        try:
            all_rows.extend(fetch_rank(rid, args.sleep))
        except Exception as e:
            print(f"  [失败] 分区 {RIDS.get(rid, rid)}：{e}")

    # 按视频 ID 去重（不同分区的榜单会重叠）
    seen, rows = set(), []
    for r in all_rows:
        if r["视频ID"] in seen:
            continue
        seen.add(r["视频ID"])
        rows.append(r)

    if args.with_fans:
        print(f"开始补全 UP 主粉丝数（{len(rows)} 条，去重后查询）…")
        fill_fans(rows, args.sleep)

    if not rows:
        print("未采集到任何数据，请检查网络或稍后重试。")
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    cols = ["视频ID", "视频类别", "作者粉丝数", "播放量", "点赞量",
            "评论量", "转发量", "收藏量", "发布时间"]
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"\n采集完成：{len(rows)} 条视频 -> {args.out}")
    if not args.with_fans:
        print("提示：未查询粉丝数，作者粉丝数为空。可用 --with-fans 重跑补齐，"
              "或用 ingest.py 导入后再用 enrich 脚本补全。")
    print("下一步：python algorithm/datasets/ingest.py --platform bilibili")
    return 0


if __name__ == "__main__":
    sys.exit(main())
