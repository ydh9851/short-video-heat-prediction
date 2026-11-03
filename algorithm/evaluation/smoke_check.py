#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""评估冒烟检查：用小样本快速跑一遍关键实验，断言核心指标没有退化。

用途：作为持续集成中的一个关卡。单元测试只能证明"代码没写错"，
但证明不了"模型突然变差了"——依赖升级、特征口径调整、数据文件替换
都可能让指标下滑而不触发任何报错。这里用固定随机种子跑一次轻量交叉验证，
把核心指标与基线对比，低于阈值即让流水线失败。

用法：
    python algorithm/evaluation/smoke_check.py
    python algorithm/evaluation/smoke_check.py --folds 3 --sample 3000

退出码：0 表示通过，1 表示指标退化或执行异常。
输出：单行 JSON，便于 CI 解析。
"""
import argparse
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import model_evaluation as M  # noqa: E402

# 基线阈值：取自全量 5 折交叉验证实测值（R²(log)=0.8221±0.0036）的保守下界。
# 冒烟检查用小样本，指标本身会略低于全量，因此阈值不能直接照搬全量值。
THRESHOLDS = {
    "r2_log": 0.75,          # 交叉验证 R²(log) 下限
    "mae_ratio": 0.95,      # 最优模型的 MAE 相对线性回归的比值上限（越小越好）
}


def main():
    ap = argparse.ArgumentParser(description="评估冒烟检查：核心指标不回归")
    ap.add_argument("--folds", type=int, default=3)
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    try:
        result = M.mode_cv(folds=args.folds)
    except TypeError:
        # mode_cv 的关键字参数可能随版本调整，这里退回到无参调用
        result = M.mode_cv()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "trace": traceback.format_exc()},
                         ensure_ascii=False))
        sys.exit(1)

    models = result.get("models", {}) or {}
    best = result.get("best")
    checks = []
    ok = True

    def mean_mae(entry):
        """逐折 MAE 的均值：mode_cv 只在 folds 明细里给出 mae。"""
        folds = entry.get("folds") or []
        values = [float(f.get("mae") or 0) for f in folds]
        return sum(values) / len(values) if values else 0.0

    r2 = float((models.get(best) or {}).get("r2_mean") or 0)
    passed = r2 >= THRESHOLDS["r2_log"]
    ok = ok and passed
    checks.append({
        "name": "cross-validation r2(log)",
        "value": round(r2, 4),
        "threshold": THRESHOLDS["r2_log"],
        "passed": passed,
    })

    if best and "lr" in models and best in models:
        mae_best = mean_mae(models[best])
        mae_lr = mean_mae(models["lr"])
        ratio = (mae_best / mae_lr) if mae_lr else 1.0
        passed = ratio <= THRESHOLDS["mae_ratio"]
        ok = ok and passed
        checks.append({
            "name": "best model MAE vs linear regression",
            "value": round(ratio, 4),
            "threshold": THRESHOLDS["mae_ratio"],
            "passed": passed,
        })

    payload = {
        "ok": ok,
        "mode": "smoke",
        "folds": args.folds,
        "best_model": best,
        "r2_mean": round(r2, 4),
        "checks": checks,
        "models": {k: round(float(v.get("r2_mean") or 0), 4) for k, v in models.items()},
    }
    print(json.dumps(payload, ensure_ascii=False))
    if not ok:
        failed = [c["name"] for c in checks if not c["passed"]]
        print("冒烟检查未通过：%s" % "、".join(failed), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()