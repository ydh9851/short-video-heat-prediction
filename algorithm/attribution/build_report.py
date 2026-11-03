"""
归因报告导出（自包含 HTML）

为什么不用「截图 + Word」：
    运营场景需要的是可追溯的证据链，而不是一堆图片。本脚本把一次预测的
    预测值、区间、单样本 SHAP 贡献、全局贡献排名、反事实建议、模型版本与 traceId
    一起写进**单个 HTML 文件**（图片 base64 内嵌，无外链），可以直接发邮件、离线打开、
    也可作为系统输出示例单独分发。

参考 MAIF/shapash 的 generate_report() 思路：把「全局解释 + 局部解释 + 结论」打包成审计文档。

CLI（单行 JSON）：
  python build_report.py --category 美食 --fans 50000 --hour 3 --weekday 2 --month 9
"""
import argparse
import base64
import io
import json
import os
import sys
import time
import traceback
from datetime import datetime

import numpy as np
import pandas as pd

ATTR_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_ROOT = os.path.dirname(os.path.dirname(ATTR_DIR))
PRED_DIR = os.path.join(SYSTEM_ROOT, "algorithm", "prediction")
sys.path.insert(0, PRED_DIR)
import predict_api as P  # noqa: E402

REPORT_DIR = os.path.join(SYSTEM_ROOT, "data", "reports")
FIG_DIR = os.path.join(ATTR_DIR, "figures")

CATEGORY_LIST = ["搞笑", "美食", "音乐", "美妆", "穿搭", "舞蹈", "旅行",
                 "宠物", "影视", "健身", "情感", "游戏", "生活", "知识"]
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

CN_FEATURE = {
    "video_category": "视频类别", "hour_bucket": "发布时段", "author_fans_log": "作者粉丝数(log)",
    "publish_hour": "发布小时", "publish_weekday": "发布星期", "publish_month": "发布月份",
    "is_weekend": "是否周末",
}


# ------------------------------------------------------------------ 基础工具
def _row(category, fans, hour, weekday, month):
    return pd.DataFrame([{
        "video_category": str(category),
        "hour_bucket": P._hour_bucket(int(hour)),
        "author_fans_log": float(np.log1p(max(float(fans), 0.0))),
        "publish_hour": float(hour),
        "publish_weekday": float(weekday),
        "publish_month": float(month),
        "is_weekend": 1 if int(weekday) in (5, 6) else 0,
    }])


def _predict(model, meta, category, fans, hour, weekday, month):
    X = P._encode_frame(_row(category, fans, hour, weekday, month), meta["cat_maps"], meta["cat_modes"])
    pred_log = float(model.predict(X)[0])
    return pred_log, float(np.expm1(pred_log)), X


def _bar_chart(labels, values, title, color_by_sign=True):
    """把贡献值画成横向条形图并返回 PNG 字节（不落盘，直接内嵌）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(7.2, max(2.4, 0.42 * len(labels) + 1.0)), dpi=140)
    colors = ["#ef4444" if (v >= 0) else "#10b981" for v in values] if color_by_sign else ["#6366f1"] * len(values)
    bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.62)
    ax.axvline(0, color="#94a3b8", linewidth=0.8)
    ax.set_title(title, fontsize=11)
    ax.tick_params(labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for bar, val in zip(bars, values[::-1]):
        offset = 0.01 * (max(values) - min(values) or 1)
        ax.text(val + (offset if val >= 0 else -offset), bar.get_y() + bar.get_height() / 2,
                ("%+.3f" % val), va="center", ha="left" if val >= 0 else "right", fontsize=8.5)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _png_bytes(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def _b64(data):
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


# ------------------------------------------------------------------ 主流程
def build(category="美食", fans=50000, hour=3, weekday=2, month=9, model_name="lgbm"):
    t0 = time.perf_counter()
    bundle, trained_now = P.load_or_train(model_name)
    model, meta = bundle["model"], bundle["meta"]

    pred_log, pred_heat, X = _predict(model, meta, category, fans, hour, weekday, month)
    grade = P.grade_of(pred_heat)

    # ---- 单样本 SHAP
    import shap
    explainer = shap.TreeExplainer(model)
    sv = np.ravel(np.asarray(explainer.shap_values(X)))
    base_value = explainer.expected_value
    base_value = float(np.ravel(np.asarray(base_value))[0]) if np.size(base_value) else 0.0

    names = [CN_FEATURE.get(n, n) for n in P.FEATURE_NAMES]
    pairs = sorted(zip(names, sv.tolist()), key=lambda t: -abs(t[1]))
    top = pairs[:5]
    waterfall = _b64(_bar_chart([p[0] for p in top], [p[1] for p in top],
                                "单条视频的 SHAP 贡献（log 空间，红=推高，绿=拉低）"))

    # ---- 全局贡献（重新在测试集上算一次平均 |SHAP|，避免依赖历史图片）
    _X_train, _y_train, X_test, _y_test, _m = P._prepare()
    sample_n = min(800, len(X_test))
    Xs = X_test.iloc[:sample_n] if hasattr(X_test, "iloc") else X_test[:sample_n]
    mean_abs = np.abs(np.asarray(explainer.shap_values(Xs))).mean(axis=0)
    mean_abs = np.ravel(mean_abs)
    g_order = np.argsort(-mean_abs)[:6]
    global_chart = _b64(_bar_chart([names[i] for i in g_order], [float(mean_abs[i]) for i in g_order],
                                   "全局平均 |SHAP| 贡献（Top 6）", color_by_sign=False))

    # ---- 反事实建议：逐个维度搜索更优取值
    suggestions = []
    for h in range(24):
        _, heat, _x = _predict(model, meta, category, fans, h, weekday, month)
        suggestions.append(("发布小时", "%d 点" % h, heat))
    best_hour = max(suggestions, key=lambda t: t[2])
    cur_hour = [s for s in suggestions if s[1] == "%d 点" % int(hour)][0]

    cat_cf = []
    for c in CATEGORY_LIST:
        _, heat, _x = _predict(model, meta, c, fans, hour, weekday, month)
        cat_cf.append(("视频类别", c, heat))
    best_cat = max(cat_cf, key=lambda t: t[2])
    cur_cat = [s for s in cat_cf if s[1] == str(category)]
    cur_cat = cur_cat[0] if cur_cat else ("视频类别", str(category), pred_heat)

    wd_cf = []
    for w in range(7):
        _, heat, _x = _predict(model, meta, category, fans, hour, w, month)
        wd_cf.append(("发布星期", WEEKDAY_CN[w], heat))
    best_wd = max(wd_cf, key=lambda t: t[2])

    for dim, cur, best in (("发布小时", cur_hour, best_hour),
                           ("视频类别", cur_cat, best_cat),
                           ("发布星期", ("发布星期", WEEKDAY_CN[int(weekday)], pred_heat), best_wd)):
        gain = (best[2] - cur[2]) / max(cur[2], 1.0)
        if gain > 0.01:
            suggestions.append((dim, cur[1], best[1], cur[2], best[2], gain))
    suggestions = [s for s in suggestions if len(s) == 6]
    suggestions.sort(key=lambda s: -s[5])
    suggestions = suggestions[:3]

    # ---- 预测区间（分位数回归缓存模型）
    interval = None
    try:
        import quantile_predict as Q
        lo_b, _ = Q.load_or_train(0.1)
        hi_b, _ = Q.load_or_train(0.9)
        lo = float(np.expm1(lo_b["model"].predict(X)[0]))
        hi = float(np.expm1(hi_b["model"].predict(X)[0]))
        interval = (min(lo, hi), max(lo, hi))
    except Exception:
        interval = None

    # ---- 组装 HTML
    trace_id = os.environ.get("TRACE_ID") or "-"
    metrics = bundle.get("metrics") or {}
    intervals_html = ("P10 ~ P90：<b>%s ~ %s</b>" % (format(round(interval[0]), ","), format(round(interval[1]), ","))
                      if interval else "分位数模型不可用")

    def row_html(pairs_):
        out = []
        for name, val in pairs_:
            cls = "pos" if val >= 0 else "neg"
            out.append("<tr><td>%s</td><td class='%s'>%+.4f</td></tr>" % (name, cls, val))
        return "".join(out)

    sugg_html = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s → <b>%s</b></td><td class='pos'>+%.1f%%</td></tr>"
        % (dim, cur, best, format(round(a), ","), format(round(b), ","), gain * 100)
        for dim, cur, best, a, b, gain in suggestions) or \
        "<tr><td colspan='5' class='muted'>当前输入已接近该维度最优取值，无明显可改进项</td></tr>"

    html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>短视频热度归因报告</title>
<style>
 body{font-family:"Microsoft YaHei",system-ui,sans-serif;margin:0;background:#f6f7fb;color:#1f2430}
 .wrap{max-width:900px;margin:0 auto;padding:28px 24px 48px;background:#fff;min-height:100vh;box-shadow:0 0 24px rgba(15,23,42,.06)}
 h1{font-size:22px;margin:0 0 4px}
 .sub{color:#6b7280;font-size:13px;margin-bottom:22px}
 .kpi{display:flex;gap:14px;flex-wrap:wrap;margin:16px 0 26px}
 .card{flex:1 1 190px;border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;background:#fbfcff}
 .card .l{font-size:12px;color:#6b7280}
 .card .v{font-size:20px;font-weight:700;margin-top:4px}
 h2{font-size:15px;margin:26px 0 10px;padding-left:9px;border-left:3px solid #6366f1}
 table{width:100%;border-collapse:collapse;font-size:13px}
 th,td{padding:7px 10px;border-bottom:1px solid #eef1f6;text-align:left}
 th{background:#f8fafc;color:#475569;font-weight:600}
 .pos{color:#dc2626}.neg{color:#059669}.muted{color:#94a3b8}
 img{max-width:100%;border:1px solid #eef1f6;border-radius:8px;margin:6px 0}
 .foot{margin-top:34px;padding-top:14px;border-top:1px dashed #e5e7eb;font-size:12px;color:#94a3b8;line-height:1.8}
 code{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px}
</style></head><body><div class="wrap">
<h1>短视频热度归因报告</h1>
<div class="sub">生成时间 __TIME__ ｜ 模型 <code>__MODEL__</code> ｜ 特征版本 v__FV__ ｜ traceId <code>__TRACE__</code></div>

<div class="kpi">
  <div class="card"><div class="l">预测热度（加权互动量）</div><div class="v">__HEAT__</div></div>
  <div class="card"><div class="l">热度等级</div><div class="v">__GRADE__</div></div>
  <div class="card"><div class="l">90% 预测区间</div><div class="v" style="font-size:14px;font-weight:600">__INTERVAL__</div></div>
  <div class="card"><div class="l">模型 R²(log) / MAE(log)</div><div class="v">__R2__ / __MAE__</div></div>
</div>

<h2>输入的先验信息</h2>
<table><tr><th>视频类别</th><th>作者粉丝数</th><th>发布小时</th><th>发布星期</th><th>发布月份</th><th>是否周末</th></tr>
<tr><td>__CAT__</td><td>__FANS__</td><td>__HOUR__ 点</td><td>__WD__</td><td>__MONTH__ 月</td><td>__WK__</td></tr></table>

<h2>为什么是这个结果（单条归因）</h2>
<img src="__WATERFALL__" alt="单条 SHAP 贡献">
<table><tr><th>特征</th><th>SHAP 贡献（log 空间）</th></tr>__TOP_ROWS__</table>
<p class="muted" style="font-size:12.5px">基准值（全体样本平均预测）log = __BASE__；各特征贡献之和 + 基准值 = 该条预测 log = __PREDLOG__。</p>

<h2>模型整体在关注什么（全局归因）</h2>
<img src="__GLOBAL__" alt="全局平均 |SHAP|">

<h2>可执行的调整建议（反事实分析）</h2>
<table><tr><th>可调整维度</th><th>当前取值</th><th>建议取值</th><th>预计热度</th><th>提升幅度</th></tr>__SUGG__</table>
<p class="muted" style="font-size:12.5px">反事实结果来自「固定其他条件、只改一个维度」的模型内插值，用于相对比较，不代表真实因果效应。</p>

<div class="foot">
  报告由 <code>algorithm/attribution/build_report.py</code> 生成，图片已内嵌，可离线分享。<br>
  热度口径：heat = 播放量 + 3×点赞 + 5×评论 + 8×转发；模型 <code>__MODEL__</code>，特征版本 v__FV__。<br>
  防泄漏说明：播放/点赞/评论/转发本身是目标组成部分，未作为特征进入模型。
</div>
</div></body></html>"""

    html = (html
            .replace("__TIME__", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            .replace("__MODEL__", model_name)
            .replace("__FV__", str(P.FEATURE_VERSION))
            .replace("__TRACE__", trace_id)
            .replace("__HEAT__", format(round(pred_heat), ","))
            .replace("__GRADE__", grade)
            .replace("__INTERVAL__", intervals_html)
            .replace("__R2__", ("%.4f" % metrics.get("r2")) if metrics.get("r2") is not None else "-")
            .replace("__MAE__", ("%.4f" % metrics.get("mae")) if metrics.get("mae") is not None else "-")
            .replace("__CAT__", str(category))
            .replace("__FANS__", format(round(float(fans)), ","))
            .replace("__HOUR__", str(int(hour)))
            .replace("__WD__", WEEKDAY_CN[int(weekday)])
            .replace("__MONTH__", str(int(month)))
            .replace("__WK__", "是" if int(weekday) in (5, 6) else "否")
            .replace("__WATERFALL__", waterfall)
            .replace("__GLOBAL__", global_chart)
            .replace("__TOP_ROWS__", row_html(top))
            .replace("__BASE__", "%.4f" % base_value)
            .replace("__PREDLOG__", "%.4f" % pred_log)
            .replace("__SUGG__", sugg_html))

    os.makedirs(REPORT_DIR, exist_ok=True)
    name = "explain_%s.html" % datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    return {
        "mode": "explain-report",
        "file": "data/reports/" + name,
        "url": "/reports/" + name,
        "sizeKB": round(os.path.getsize(path) / 1024.0, 1),
        "prediction": round(pred_heat, 1),
        "grade": grade,
        "trainedNow": trained_now,
        "elapsedMs": round((time.perf_counter() - t0) * 1000, 0),
    }


def main():
    ap = argparse.ArgumentParser(description="生成自包含的归因分析报告（HTML）")
    ap.add_argument("--category", default="美食")
    ap.add_argument("--fans", type=float, default=50000)
    ap.add_argument("--hour", type=int, default=3)
    ap.add_argument("--weekday", type=int, default=2)
    ap.add_argument("--month", type=int, default=9)
    ap.add_argument("--model", default="lgbm")
    args = ap.parse_args()
    # 与其它脚本一致：Java 侧用 URL 编码传中文类别，这里解码还原
    from urllib.parse import unquote_plus
    category = unquote_plus(args.category) if "%" in args.category else args.category
    try:
        print(json.dumps(build(category, args.fans, args.hour, args.weekday, args.month, args.model),
                         ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc(),
                          "trace_id": os.environ.get("TRACE_ID")}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
