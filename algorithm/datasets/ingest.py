# -*- coding: utf-8 -*-
"""
多平台数据集导入器
==================
把各平台原始导出文件（csv / xlsx / json / parquet）归一化为统一 Schema，
写出 data/processed/<platform>_clean.csv，并维护数据集注册表 dataset_registry.json。

用法示例：
    # 导入抖音（用 data/raw 下的 douyin_video_data.xlsx）
    python algorithm/datasets/ingest.py --platform douyin

    # 导入 YouTube（指定文件）
    python algorithm/datasets/ingest.py --platform youtube --input data/raw/youtube_trending.csv

    # 自动扫描并导入 data/raw 下所有能识别到的平台文件
    python algorithm/datasets/ingest.py --all

    # 查看已导入的数据集
    python algorithm/datasets/ingest.py --list

输出：单行 JSON（供后端 DatasetService 直接解析），字段：
    {"code":1,"platform":"youtube","message":"...","detail":{...}}
出错时 code=0 且 message 说明原因。
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))       # .../algorithm/datasets
ALGO_DIR = os.path.dirname(SCRIPT_DIR)                        # .../algorithm
SYSTEM_ROOT = os.path.dirname(ALGO_DIR)                       # 系统根目录
DATA_DIR = os.path.join(SYSTEM_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
REGISTRY_PATH = os.path.join(PROCESSED_DIR, "dataset_registry.json")

sys.path.insert(0, SCRIPT_DIR)
from platform_schema import (  # noqa: E402
    UNIFIED_COLUMNS, PLATFORM_NAMES, resolve_columns, compute_heat,
)

# 各平台在 data/raw 下用于自动识别的文件名关键字
RAW_PATTERNS = {
    "douyin": ["douyin", "抖音"],
    "youtube": ["youtube", "yt_", "_yt"],
    "tiktok": ["tiktok", "tt_"],
    "bilibili": ["bilibili", "b站", "bili_"],
}


# ------------------------------------------------------------------ 工具函数
def _hour_bucket(h) -> str:
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


def _find_raw_file(platform: str):
    """在 data/raw 下按关键字查找该平台的原始文件（支持一层子目录）。"""
    if not os.path.isdir(RAW_DIR):
        return None
    kws = [k.lower() for k in RAW_PATTERNS.get(platform, [platform])]
    cands = []
    for root, _dirs, files in os.walk(RAW_DIR):
        for fn in files:
            low = fn.lower()
            if low.startswith(".") or low.endswith((".zip", ".rar", ".7z")):
                continue
            if not low.endswith((".csv", ".xlsx", ".xls", ".json", ".parquet", ".tsv")):
                continue
            if any(k in low for k in kws):
                cands.append(os.path.join(root, fn))
    if not cands:
        return None
    # 优先 parquet/csv，其次 xlsx，最后 json
    order = {".parquet": 0, ".csv": 1, ".tsv": 1, ".xlsx": 2, ".xls": 2, ".json": 3}
    cands.sort(key=lambda p: (order.get(os.path.splitext(p)[1].lower(), 9), len(p)))
    return cands[0]


def _flatten_tiktok_scraper_json(obj):
    """把 tiktok-scraper 导出的嵌套 JSON（含 collector[].stats/authorStats）摊平。"""
    items = obj.get("collector") if isinstance(obj, dict) else obj
    if not isinstance(items, list):
        return None
    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        stats = it.get("stats") or {}
        author = it.get("authorStats") or it.get("authorMeta") or {}
        rows.append({
            "视频ID": it.get("id"),
            "视频类别": it.get("textExtra", [{}])[0].get("hashtagName") if isinstance(it.get("textExtra"), list) and it.get("textExtra") else it.get("category"),
            "作者粉丝数": author.get("followerCount") or author.get("fans"),
            "播放量": stats.get("playCount"),
            "点赞量": stats.get("diggCount") or stats.get("likeCount"),
            "评论量": stats.get("commentCount"),
            "转发量": stats.get("shareCount"),
            "收藏量": stats.get("collectCount") or stats.get("saveCount"),
            "发布时间": it.get("createTimeISO") or it.get("createTime"),
        })
    return pd.DataFrame(rows) if rows else None


def _read_any(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".csv", ".tsv"):
        for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
            try:
                sep = "\t" if ext == ".tsv" else ","
                return pd.read_csv(path, encoding=enc, sep=sep, low_memory=False)
            except UnicodeDecodeError:
                continue
        raise RuntimeError(f"无法识别文件编码：{path}")
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    if ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        flat = _flatten_tiktok_scraper_json(obj)
        if flat is not None:
            return flat
        return pd.json_normalize(obj)
    raise RuntimeError(f"不支持的文件类型：{ext}")


# ------------------------------------------------------------------ 注册表
def load_registry() -> dict:
    if os.path.isfile(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                reg = json.load(f)
            reg.setdefault("datasets", {})
            return reg
        except Exception:
            pass
    return {"defaultPlatform": "douyin", "datasets": {}}


def save_registry(reg: dict):
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    reg["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reg.setdefault("defaultPlatform", "douyin")
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)


def dataset_overview(clean: pd.DataFrame) -> dict:
    """从归一化后的数据生成供前端/论文使用的元信息。"""
    heat = pd.to_numeric(clean["heat"], errors="coerce").dropna()
    fans = pd.to_numeric(clean["author_fans"], errors="coerce").dropna()
    pt = pd.to_datetime(clean["publish_time"], errors="coerce").dropna()

    def q(s, p):
        return float(s.quantile(p)) if len(s) else 0.0

    return {
        "rows": int(len(clean)),
        "categoryCount": int(clean["video_category"].nunique()),
        "categories": (clean["video_category"].value_counts().head(15)
                       .to_dict()),
        "timeStart": pt.min().strftime("%Y-%m-%d") if len(pt) else "",
        "timeEnd": pt.max().strftime("%Y-%m-%d") if len(pt) else "",
        "heat": {"min": float(heat.min()) if len(heat) else 0.0,
                 "q25": q(heat, .25), "median": q(heat, .5), "q75": q(heat, .75),
                 "p90": q(heat, .9), "max": float(heat.max()) if len(heat) else 0.0,
                 "mean": float(heat.mean()) if len(heat) else 0.0},
        "fans": {"median": q(fans, .5), "p90": q(fans, .9),
                 "max": float(fans.max()) if len(fans) else 0.0},
    }


# ------------------------------------------------------------------ 核心导入
def ingest(platform: str, path: str, display_name: str = None) -> dict:
    display = display_name or PLATFORM_NAMES.get(platform, platform)
    if not path or not os.path.isfile(path):
        return {"code": 0, "platform": platform,
                "message": f"未找到原始数据文件，请把 {display} 的数据放到 data/raw 目录，"
                           f"或用 --input 指定具体文件路径"}

    raw = _read_any(path)
    if raw is None or raw.empty:
        return {"code": 0, "platform": platform, "message": f"文件读取为空：{path}"}

    mapping = resolve_columns(raw, platform)
    missing = [k for k in ("video_id", "publish_time") if not mapping.get(k)]
    if missing:
        cols = "、".join(str(c) for c in list(raw.columns)[:20])
        return {"code": 0, "platform": platform,
                "message": "无法识别关键列 " + "、".join(missing) +
                           f"（{display}）。文件实际列名：{cols}。"
                           "可在 algorithm/datasets/platform_schema.py 中补充别名后重试"}

    out = pd.DataFrame()
    out["platform"] = platform
    out["video_id"] = raw[mapping["video_id"]].astype(str)
    out["video_category"] = (raw[mapping["video_category"]].astype(str)
                             if mapping.get("video_category") else "未知")
    for key in ("author_fans", "play_cnt", "like_cnt", "comment_cnt",
                "share_cnt", "collect_cnt"):
        src = mapping.get(key)
        out[key] = pd.to_numeric(raw[src], errors="coerce") if src else np.nan
    out["publish_time"] = pd.to_datetime(raw[mapping["publish_time"]], errors="coerce")

    # 转发字段缺失的平台（如 YouTube）按 0 计入，并在注册表中如实标注
    share_available = bool(mapping.get("share_cnt"))
    if not share_available:
        out["share_cnt"] = 0.0

    before = len(out)
    out = out.dropna(subset=["publish_time"]).copy()     # 无发布时间无法构造时间特征
    out["video_category"] = out["video_category"].fillna("未知").astype(str)
    out["author_fans"] = pd.to_numeric(out["author_fans"], errors="coerce").clip(lower=0)
    fans_median = out["author_fans"].median()
    out["author_fans"] = out["author_fans"].fillna(0.0 if pd.isna(fans_median) else fans_median)

    out["heat"] = compute_heat(out, share_available)
    out = out[out["heat"] >= 0]

    # 与 preprocess.py 保持一致的派生列，便于跨平台模块直接复用
    dt = out["publish_time"].dt
    out["publish_hour"] = dt.hour.astype("float")
    out["publish_weekday"] = dt.weekday.astype("float")
    out["publish_month"] = dt.month.astype("float")
    out["is_weekend"] = dt.weekday.isin([5, 6]).astype(int)
    out["hour_bucket"] = out["publish_hour"].apply(_hour_bucket)
    out["author_fans_log"] = np.log1p(out["author_fans"])
    out["heat_log"] = np.log1p(out["heat"])

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    clean_path = os.path.join(PROCESSED_DIR, f"{platform}_clean.csv")
    out.to_csv(clean_path, index=False, encoding="utf-8-sig")

    meta = dataset_overview(out)
    meta.update({
        "platform": platform,
        "displayName": display,
        "rawFile": os.path.relpath(path, SYSTEM_ROOT).replace("\\", "/"),
        "processedFile": f"data/processed/{platform}_clean.csv",
        "shareAvailable": share_available,
        "droppedRows": int(before - len(out)),
        "columnMapping": {k: (str(v) if v else None) for k, v in mapping.items()
                          if k in UNIFIED_COLUMNS},
        "importTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    reg = load_registry()
    reg["datasets"][platform] = meta
    if not reg.get("defaultPlatform"):
        reg["defaultPlatform"] = platform
    save_registry(reg)

    return {
        "code": 1,
        "platform": platform,
        "message": f"{display} 数据集导入成功：{meta['rows']} 行，"
                   f"{meta['categoryCount']} 个类别，时间跨度 {meta['timeStart']} ~ {meta['timeEnd']}"
                   + ("" if share_available else "（该平台无转发字段，热度口径中转发按 0 计）"),
        "detail": meta,
    }


def ingest_all() -> list:
    results = []
    for pf in RAW_PATTERNS:
        path = _find_raw_file(pf)
        if path:
            results.append(ingest(pf, path))
    return results


# ------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description="多平台短视频数据集导入器")
    ap.add_argument("--platform", choices=list(RAW_PATTERNS.keys()), help="目标平台")
    ap.add_argument("--input", help="原始数据文件路径（缺省时自动在 data/raw 下查找）")
    ap.add_argument("--name", help="平台展示名（可选）")
    ap.add_argument("--all", action="store_true", help="自动扫描 data/raw 并导入所有可识别平台")
    ap.add_argument("--list", action="store_true", help="列出已导入的数据集")
    args = ap.parse_args()

    if args.list:
        reg = load_registry()
        print(json.dumps({"code": 1, "registry": reg}, ensure_ascii=False))
        return 0

    if args.all:
        res = ingest_all()
        if not res:
            print(json.dumps({"code": 0, "message":
                              "data/raw 下未发现可识别的平台文件（文件名需含 douyin/youtube/tiktok/bilibili 关键字）"},
                             ensure_ascii=False))
            return 0
        print(json.dumps({"code": 1 if all(r["code"] == 1 for r in res) else 0,
                          "results": res}, ensure_ascii=False))
        return 0

    platform = args.platform or "douyin"
    path = args.input or _find_raw_file(platform)
    print(json.dumps(ingest(platform, path, args.name), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
