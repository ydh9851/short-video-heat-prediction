#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""数据集版本登记：为每次导入的清洗结果生成指纹与版本号。

模型注册表记录了模型版本与特征版本，但没记录该模型用的是哪一版数据。
数据文件被替换后，指标变化无法归因——是模型改坏了，还是数据换了。

做法：对清洗后的 CSV 计算内容指纹（SHA-256 前段），配合时间戳形成版本号，
写入 data/processed/dataset_versions.json；指纹未变则不新增记录，
避免同一份数据反复导入把清单冲刷成噪声。
"""
import hashlib
import json
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROCESSED_DIR = os.path.join(ROOT, "data", "processed")
VERSIONS_PATH = os.path.join(PROCESSED_DIR, "dataset_versions.json")


def fingerprint(path):
    """文件内容指纹：分块读取，避免大文件占内存。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def load_versions():
    if not os.path.isfile(VERSIONS_PATH):
        return {"datasets": {}}
    try:
        with open(VERSIONS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"datasets": {}}


def save_versions(data):
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    with open(VERSIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def register(platform, path, meta=None):
    """登记一个数据集版本；内容指纹相同则返回已有版本，不新增记录。"""
    if not os.path.isfile(path):
        return {}
    data = load_versions()
    datasets = data.setdefault("datasets", {})
    entries = datasets.setdefault(platform, [])

    digest = fingerprint(path)
    for item in entries:
        if item.get("fingerprint") == digest:
            return item

    version = "v%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), digest[:6])
    entry = {
        "version": version,
        "fingerprint": digest,
        "file": os.path.basename(path),
        "rows": int(meta.get("rows", 0)) if meta else 0,
        "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if meta:
        for key in ("heat_median", "heat_p90", "category_count"):
            if key in meta:
                entry[key] = meta[key]
    entries.append(entry)
    save_versions(data)
    return entry


def current_version(platform):
    """该平台最近登记的版本号；没有则返回空串。"""
    entries = (load_versions().get("datasets") or {}).get(platform) or []
    return entries[-1]["version"] if entries else ""


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(load_versions(), ensure_ascii=False, indent=2))