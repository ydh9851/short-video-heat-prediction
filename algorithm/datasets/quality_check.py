"""
数据质量门禁（Data Quality Gate）

在数据进入建模之前做一轮断言式检查，把「脏数据导致的模型异常」挡在入口，
而不是等到指标难看时才回头怀疑数据。参考 Great Expectations / Evidently Test Suites
的「断言 + 报告」思路，本地化为 8 项检查：

  硬性（HARD，失败即判 FAIL，应阻断导入）：
    1. 文件存在且行数 ≥ 100
    2. 统一 schema 字段齐全（video_id / video_category / author_fans / play_cnt /
       like_cnt / comment_cnt / share_cnt / heat / publish_time）
    3. 关键字段缺失率 ≤ 5%（video_id / publish_time / author_fans）
    4. 互动量非负（播放/点赞/评论/转发不得为负）
  软性（SOFT，失败判 WARN，仅提示）：
    5. 主键重复率 ≤ 20%
    6. 类别覆盖：类别数 ≥ 2 且最大类别占比 ≤ 90%
    7. 热度分布 PSI（相对注册表基准分位）≤ 0.25
    8. 发布时间落在合理区间（2000-01-01 ~ 明天）

CLI（单行 JSON，与其它算法脚本一致）：
  python quality_check.py --platform douyin [--write]
"""
import argparse
import json
import os
import sys
import traceback

import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
PROCESSED_DIR = os.path.join(SYSTEM_ROOT, "data", "processed")
REGISTRY = os.path.join(PROCESSED_DIR, "dataset_registry.json")
REPORT = os.path.join(PROCESSED_DIR, "quality_report.json")

REQUIRED = ["video_id", "video_category", "author_fans", "play_cnt", "like_cnt",
            "comment_cnt", "share_cnt", "heat", "publish_time"]
KEY_COLS = ["video_id", "publish_time", "author_fans"]
COUNT_COLS = ["play_cnt", "like_cnt", "comment_cnt", "share_cnt"]
MIN_ROWS = 100
MAX_MISSING = 0.05
MAX_DUP = 0.20
MAX_CATEGORY_SHARE = 0.90
PSI_WARN = 0.25


def _psi(expected_pct, actual_pct, eps=1e-4):
    """Population Stability Index：分布漂移的常用度量，<0.1 稳定，0.1~0.25 轻微，>0.25 显著。"""
    score = 0.0
    for e, a in zip(expected_pct, actual_pct):
        e = max(float(e), eps)
        a = max(float(a), eps)
        score += (a - e) * np.log(a / e)
    return float(score)


def _baseline_heat(registry, platform):
    """从注册表取基准热度分位；缺失时返回 None（跳过 PSI 检查）。"""
    try:
        ds = (registry or {}).get("datasets", {}).get(platform, {})
        heat = ds.get("heat") or {}
        edges = [heat.get("min"), heat.get("q25"), heat.get("median"),
                 heat.get("q75"), heat.get("p90"), heat.get("max")]
        if any(v is None for v in edges):
            return None
        edges = [float(v) for v in edges]
        if any(b <= a for a, b in zip(edges, edges[1:])):
            return None
        # 与分位定义对应的期望占比：25% / 25% / 25% / 15% / 10%
        return edges, [0.25, 0.25, 0.25, 0.15, 0.10]
    except Exception:
        return None


def run(platform="douyin", write=False):
    checks = []

    def add(name, ok, detail, level="HARD"):
        checks.append({"name": name, "level": level,
                       "status": "PASS" if ok else ("FAIL" if level == "HARD" else "WARN"),
                       "detail": detail})

    path = os.path.join(PROCESSED_DIR, "%s_clean.csv" % platform)
    exists = os.path.isfile(path)

    # 1. 文件与行数
    if not exists:
        add("文件存在且行数充足", False,
            "未找到 data/processed/%s_clean.csv，请先执行导入" % platform)
        return _finish(platform, checks, None, write)

    usecols = None
    df = pd.read_csv(path, low_memory=False)
    add("文件存在且行数充足", len(df) >= MIN_ROWS,
        "行数 = %d（阈值 ≥ %d）" % (len(df), MIN_ROWS))

    # 2. schema 完整性
    missing_cols = [c for c in REQUIRED if c not in df.columns]
    add("统一 schema 字段齐全", not missing_cols,
        "缺失字段：" + "、".join(missing_cols) if missing_cols else "9 个统一字段齐全")

    # 3. 关键字段缺失率
    miss_rows = []
    for c in KEY_COLS:
        if c in df.columns:
            rate = float(df[c].isna().mean())
            if rate > MAX_MISSING:
                miss_rows.append("%s %.1f%%" % (c, rate * 100))
    add("关键字段缺失率 ≤ 5%", not miss_rows,
        "超标字段：" + "、".join(miss_rows) if miss_rows else "video_id / publish_time / author_fans 缺失率均达标")

    # 4. 互动量非负
    neg_rows = []
    for c in COUNT_COLS:
        if c in df.columns:
            vals = pd.to_numeric(df[c], errors="coerce")
            n_neg = int((vals < 0).sum())
            if n_neg:
                neg_rows.append("%s 有 %d 条负值" % (c, n_neg))
    add("互动量非负", not neg_rows,
        "；".join(neg_rows) if neg_rows else "播放/点赞/评论/转发均无负值")

    # 5. 主键重复率（软性：跨平台聚合数据允许一定重复）
    if "video_id" in df.columns:
        dup = float(df["video_id"].duplicated().mean())
        add("主键重复率 ≤ 20%", dup <= MAX_DUP,
            "重复率 = %.2f%%（阈值 ≤ %.0f%%）" % (dup * 100, MAX_DUP * 100), level="SOFT")

    # 6. 类别覆盖
    if "video_category" in df.columns:
        vc = df["video_category"].astype(str).value_counts(normalize=True)
        n_cat = int(len(vc))
        top_share = float(vc.iloc[0]) if n_cat else 0.0
        add("类别覆盖合理", n_cat >= 2 and top_share <= MAX_CATEGORY_SHARE,
            "类别数 = %d，最大类别占比 = %.1f%%" % (n_cat, top_share * 100), level="SOFT")

    # 7. 热度分布 PSI（与注册表基准对比）
    psi_value = None
    base = None
    if os.path.isfile(REGISTRY):
        try:
            with open(REGISTRY, encoding="utf-8") as f:
                base = _baseline_heat(json.load(f), platform)
        except Exception:
            base = None
    if base and "heat" in df.columns:
        edges, expected = base
        heat = pd.to_numeric(df["heat"], errors="coerce").dropna().values
        if len(heat):
            idx = np.digitize(heat, bins=edges[1:-1])
            actual = np.bincount(idx, minlength=len(expected))[:len(expected)]
            actual = (actual / max(len(heat), 1)).tolist()
            psi_value = _psi(expected, actual)
            add("热度分布 PSI ≤ 0.25", psi_value <= PSI_WARN,
                "PSI = %.4f（0.1 内稳定 / 0.25 内轻微 / 超过即显著漂移）" % psi_value, level="SOFT")
    else:
        add("热度分布 PSI ≤ 0.25", True, "注册表缺少基准分位，跳过 PSI 检查", level="SOFT")

    # 8. 发布时间区间
    if "publish_time" in df.columns:
        # 统一转 UTC：不同平台的时间列可能带时区（如 YouTube），与朴素时间戳直接比较会抛 TypeError
        ts = pd.to_datetime(df["publish_time"], errors="coerce", utc=True)
        bad = int(ts.isna().sum())
        lower = pd.Timestamp("2000-01-01", tz="UTC")
        upper = pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=1)
        out_of_range = int(((ts < lower) | (ts > upper)).sum())
        add("发布时间区间合理", out_of_range == 0,
            "解析失败 %d 条，超出合理区间 %d 条" % (bad, out_of_range))

    return _finish(platform, checks, {"rows": int(len(df)), "psi": psi_value}, write)


def _finish(platform, checks, stats, write):
    failed = [c["name"] for c in checks if c["status"] == "FAIL"]
    warned = [c["name"] for c in checks if c["status"] == "WARN"]
    status = "FAIL" if failed else ("WARN" if warned else "PASS")
    result = {
        "mode": "quality-check",
        "platform": platform,
        "status": status,
        "checks": checks,
        "passed": len([c for c in checks if c["status"] == "PASS"]),
        "failed": failed,
        "warned": warned,
        "stats": stats or {},
        "summary": {"total": len(checks), "pass": len([c for c in checks if c["status"] == "PASS"]),
                    "fail": len(failed), "warn": len(warned)},
    }
    if write and os.path.isdir(PROCESSED_DIR):
        try:
            with open(REPORT, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["reportFile"] = "data/processed/quality_report.json"
        except Exception:
            pass
    return result


def main():
    ap = argparse.ArgumentParser(description="数据质量门禁（断言 + 质量报告）")
    ap.add_argument("--platform", default="douyin",
                    choices=["douyin", "youtube", "tiktok", "bilibili"])
    ap.add_argument("--write", action="store_true", help="把报告写入 data/processed/quality_report.json")
    args = ap.parse_args()
    try:
        print(json.dumps(run(args.platform, args.write), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc(),
                          "trace_id": os.environ.get("TRACE_ID")}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
