#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""根据后端 OpenAPI 契约生成接口文档 docs/API.md。

数据来源为运行中的 /v3/api-docs（springdoc 自动生成），因此文档与真实接口契约天然一致：
新增或修改接口后重启后端再重跑本脚本即可，不会出现文档与代码脱节。

用法：
    python tools/docs/api_docs.py [后端地址]      # 默认 http://127.0.0.1:8000
"""
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUTPUT = "docs/API.md"
METHODS = ["get", "post", "put", "delete", "patch"]


def params_text(op):
    """把接口参数压缩成一行可读说明。"""
    parts = []
    for p in op.get("parameters") or []:
        flag = ",必填" if p.get("required") else ""
        parts.append("%s(%s%s)" % (p.get("name", ""), p.get("in", ""), flag))
    if not parts and op.get("requestBody"):
        parts.append("body(JSON)")
    return "、".join(parts)


def main():
    with urllib.request.urlopen(BASE.rstrip("/") + "/v3/api-docs", timeout=30) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    info = doc.get("info") or {}
    paths = doc.get("paths") or {}

    groups = {}
    total = 0
    for path, item in paths.items():
        for method, op in item.items():
            if method not in METHODS:
                continue
            total += 1
            for tag in (op.get("tags") or ["未分组"]):
                groups.setdefault(tag, []).append((method.upper(), path, op))

    out = []
    out.append("# 接口文档")
    out.append("")
    out.append("> 本文件由 `python tools/docs/api_docs.py` 依据后端 OpenAPI 契约（`/v3/api-docs`）自动生成，"
               "共 **%d** 个接口，分 **%d** 组。" % (total, len(groups)))
    out.append("")
    out.append("> 在线交互式文档（可直接试调）：`%s/swagger-ui/index.html`" % BASE)
    out.append("")
    out.append("> 系统：%s　版本：%s" % (info.get("title", "-"), info.get("version", "-")))
    out.append("")
    desc = (info.get("description") or "").strip()
    if desc:
        out.append(desc)
        out.append("")
    out.append("所有响应统一为 `{ code, message, response }` 三字段结构；"
               "响应头 `X-Trace-Id` 可用于在后端日志中定位该次请求。")
    out.append("")
    out.append("## 分组总览")
    out.append("")
    out.append("| 分组 | 接口数 |")
    out.append("|---|---|")
    for tag in sorted(groups):
        out.append("| %s | %d |" % (tag, len(groups[tag])))
    out.append("")
    for tag in sorted(groups):
        out.append("## %s" % tag)
        out.append("")
        out.append("| 方法 | 路径 | 说明 | 参数 |")
        out.append("|---|---|---|---|")
        for method, path, op in sorted(groups[tag], key=lambda x: (x[0], x[1])):
            text = (op.get("summary") or op.get("description") or "").replace("\n", " ").strip()
            out.append("| `%s` | `%s` | %s | %s |"
                       % (method, path, text or "—", params_text(op) or "—"))
        out.append("")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("已生成 %s（%d 个接口 / %d 组）" % (OUTPUT, total, len(groups)))


if __name__ == "__main__":
    main()
