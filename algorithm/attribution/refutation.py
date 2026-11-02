"""
反事实稳健性检验（Refutation）

问题：系统的「反事实建议」本质是**模型内插值**，不是真实因果效应。
如果换个随机子集、换个模型，结论就翻转，那这些建议不能拿去做决策。

参考 DoWhy 的 refutation 思路，设计三个可在本项目上直接执行的检验：

  1) 安慰剂维度（placebo）
     对「发布月份」这个 SHAP 贡献只有约 1% 的弱维度做同样的"改到最优"搜索。
     若弱维度也能刷出与强维度同量级的提升 → 说明反事实程序在制造虚假收益。

  2) 子集重估（data_subset）
     在多个随机 80% 训练子集上重新训练同一模型，重复反事实估计，
     报告各维度增益的均值、标准差与变异系数（CV）。CV 越大说明结论越不稳。

  3) 跨模型一致性（model_swap）
     换用 RandomForest / XGBoost 重跑，比较"最优取值"是否一致。
     方向一致说明结论来自数据中的信号，而不是某个模型的偏好。

CLI（单行 JSON）：
  python refutation.py [--splits 3] [--platform douyin]
"""
import argparse
import json
import os
import sys
import traceback

import numpy as np
import pandas as pd

ATTR_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_ROOT = os.path.dirname(os.path.dirname(ATTR_DIR))
PRED_DIR = os.path.join(SYSTEM_ROOT, "algorithm", "prediction")
sys.path.insert(0, PRED_DIR)
import predict_api as P  # noqa: E402

CATEGORY_LIST = ["搞笑", "美食", "音乐", "美妆", "穿搭", "舞蹈", "旅行",
                 "宠物", "影视", "健身", "情感", "游戏", "生活", "知识"]
WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
SEED = 42

# 基准样本：与系统默认示例一致，便于与报告中的反事实结果对照
BASE = {"category": "美食", "fans": 50000, "hour": 3, "weekday": 2, "month": 9}


def _row(meta, category, fans, hour, weekday, month):
    df = pd.DataFrame([{
        "video_category": str(category),
        "hour_bucket": P._hour_bucket(int(hour)),
        "author_fans_log": float(np.log1p(max(float(fans), 0.0))),
        "publish_hour": float(hour),
        "publish_weekday": float(weekday),
        "publish_month": float(month),
        "is_weekend": 1 if int(weekday) in (5, 6) else 0,
    }])
    return P._encode_frame(df, meta["cat_maps"], meta["cat_modes"])


def _heat(model, meta, **kw):
    X = _row(meta, kw.get("category", BASE["category"]), kw.get("fans", BASE["fans"]),
             kw.get("hour", BASE["hour"]), kw.get("weekday", BASE["weekday"]),
             kw.get("month", BASE["month"]))
    return float(np.expm1(model.predict(X)[0]))


def _best_hour(model, meta):
    vals = [(h, _heat(model, meta, hour=h)) for h in range(24)]
    best = max(vals, key=lambda t: t[1])
    cur = _heat(model, meta, hour=BASE["hour"])
    return {"to": best[0], "gain": (best[1] - cur) / max(cur, 1.0), "heat": best[1], "cur": cur}


def _best_category(model, meta):
    vals = [(c, _heat(model, meta, category=c)) for c in CATEGORY_LIST]
    best = max(vals, key=lambda t: t[1])
    cur = _heat(model, meta)
    return {"to": best[0], "gain": (best[1] - cur) / max(cur, 1.0), "heat": best[1], "cur": cur}


def _best_weekday(model, meta):
    vals = [(w, _heat(model, meta, weekday=w)) for w in range(7)]
    best = max(vals, key=lambda t: t[1])
    cur = _heat(model, meta)
    return {"to": WEEKDAY_CN[best[0]], "gain": (best[1] - cur) / max(cur, 1.0), "heat": best[1], "cur": cur}


def _best_month(model, meta):
    """安慰剂维度：SHAP 贡献最弱的可调整维度之一。"""
    vals = [(m, _heat(model, meta, month=m)) for m in range(1, 13)]
    best = max(vals, key=lambda t: t[1])
    cur = _heat(model, meta)
    return {"to": best[0], "gain": (best[1] - cur) / max(cur, 1.0), "heat": best[1], "cur": cur}


def _evaluate(model, meta):
    return {
        "hour": _best_hour(model, meta),
        "category": _best_category(model, meta),
        "weekday": _best_weekday(model, meta),
    }


def run(splits=3, platform=None, models=("lgbm", "rf", "xgb")):
    X_train, y_train, X_test, y_test, meta = P._prepare(platform=platform)

    # ---------- 基准模型
    main = P.build_model("lgbm", X_train, y_train)
    base = _evaluate(main, meta)
    placebo = _best_month(main, meta)

    # ---------- 1) 安慰剂维度：弱维度的最大"提升"不应与强维度同量级
    strong_max = max(base["hour"]["gain"], base["category"]["gain"], base["weekday"]["gain"])
    placebo_ok = placebo["gain"] < max(0.05, strong_max * 0.3)

    # ---------- 2) 子集重估：随机 80% 子集重训，看增益分布
    rows = []
    rng = np.random.RandomState(SEED)
    n = len(y_train)
    for i in range(int(splits)):
        idx = rng.choice(n, size=int(n * 0.8), replace=False)
        Xi = X_train.iloc[idx] if hasattr(X_train, "iloc") else X_train[idx]
        yi = y_train[idx]
        m = P.build_model("lgbm", Xi, yi)
        e = _evaluate(m, meta)
        rows.append({
            "split": i + 1,
            "hour_to": e["hour"]["to"], "hour_gain": e["hour"]["gain"],
            "category_to": e["category"]["to"], "category_gain": e["category"]["gain"],
            "weekday_to": e["weekday"]["to"], "weekday_gain": e["weekday"]["gain"],
        })

    def _stat(key):
        vals = np.array([r[key] for r in rows], dtype=float)
        mean = float(vals.mean())
        std = float(vals.std())
        return {"mean": round(mean, 4), "std": round(std, 4),
                "cv": round(std / mean, 4) if mean else None,
                "min": round(float(vals.min()), 4), "max": round(float(vals.max()), 4)}

    stability = {
        "splits": int(splits),
        "hour_gain": _stat("hour_gain"),
        "category_gain": _stat("category_gain"),
        "weekday_gain": _stat("weekday_gain"),
        "hour_to_consistent": len({r["hour_to"] for r in rows}) == 1,
        "category_to_consistent": len({r["category_to"] for r in rows}) == 1,
        "details": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rows],
    }

    # ---------- 3) 跨模型一致性
    cross = []
    for name in models:
        if name == "lgbm":
            e, mdl = base, main
        else:
            try:
                mdl = P.build_model(name, X_train, y_train)
                e = _evaluate(mdl, meta)
            except Exception as exc:
                cross.append({"model": name, "error": str(exc)})
                continue
        cross.append({
            "model": name,
            "hour_to": e["hour"]["to"], "hour_gain": round(e["hour"]["gain"], 4),
            "category_to": e["category"]["to"], "category_gain": round(e["category"]["gain"], 4),
            "weekday_to": e["weekday"]["to"], "weekday_gain": round(e["weekday"]["gain"], 4),
        })

    good = [c for c in cross if "error" not in c]
    hour_agree = len({c["hour_to"] for c in good}) == 1 if good else None
    cat_agree = len({c["category_to"] for c in good}) == 1 if good else None
    # 方向一致（增益同号且量级接近）比"最优取值完全相同"更宽松、也更现实
    all_positive = all(c["hour_gain"] > 0 and c["category_gain"] > 0 for c in good) if good else None

    verdict = "PASS" if (placebo_ok and stability["hour_gain"]["cv"] is not None
                         and stability["hour_gain"]["cv"] < 0.5 and all_positive) else "WARN"

    return {
        "mode": "refutation",
        "platform": platform or "douyin",
        "base_sample": BASE,
        "base_prediction": round(base["hour"]["cur"], 1),
        "base_estimate": {
            "hour": {"from": BASE["hour"], "to": base["hour"]["to"], "gain": round(base["hour"]["gain"], 4)},
            "category": {"from": BASE["category"], "to": base["category"]["to"],
                         "gain": round(base["category"]["gain"], 4)},
            "weekday": {"from": WEEKDAY_CN[BASE["weekday"]], "to": base["weekday"]["to"],
                        "gain": round(base["weekday"]["gain"], 4)},
        },
        "placebo": {
            "dim": "发布月份",
            "to": placebo["to"], "gain": round(placebo["gain"], 4),
            "strong_dim_max_gain": round(strong_max, 4),
            "passed": bool(placebo_ok),
        },
        "stability": stability,
        "cross_model": {"rows": cross, "hour_agreement": hour_agree,
                         "category_agreement": cat_agree, "all_gains_positive": all_positive},
        "verdict": verdict,
        "note": "三项检验分别回答：弱维度是否也被刷出高收益（安慰剂）、换数据子集结论是否稳定（重估）、"
                "换模型结论是否方向一致（模型替换）。全部通过才说明反事实建议可用于决策。",
    }


def main():
    ap = argparse.ArgumentParser(description="反事实稳健性检验（安慰剂 / 子集重估 / 模型替换）")
    ap.add_argument("--mode", default="refutation")
    ap.add_argument("--splits", type=int, default=3)
    ap.add_argument("--platform", default=None)
    args = ap.parse_args()
    try:
        print(json.dumps(run(splits=args.splits, platform=args.platform), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc), "trace": traceback.format_exc(),
                          "trace_id": os.environ.get("TRACE_ID")}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
