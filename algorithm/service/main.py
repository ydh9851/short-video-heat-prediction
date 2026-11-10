"""
短视频热度预测 —— 常驻推理服务（FastAPI sidecar）

为什么需要它：
    原来每次预测都由 Java 用 ProcessBuilder 拉起一次 Python 进程，单次开销约 1.5~2.5 秒
    （解释器启动 + 导入 lightgbm/pandas/numpy）。改成常驻服务后模型只加载一次，
    单次推理降到几十毫秒。

设计原则（与原有链路兼容）：
    1. 输出字段与 predict_api.py 的 CLI JSON **完全一致**，Java 侧解析逻辑无需改动；
    2. 旧 CLI 通道保留，Java 侧调用失败会自动降级回 CLI（双轨）；
    3. 端口默认 8100，只监听本机 127.0.0.1。

启动：
    .venv\\Scripts\\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8100
    或直接运行 run_engine_service.cmd

接口：
    GET  /health          健康检查（含特征版本、已加载模型）
    POST /predict         单条预测 {model, category, fans, hour, weekday, month}
    POST /predict/batch   批量预测 {model, items:[...]}
"""
import os
import sys
import threading
import time
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PREDICTION_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "prediction")
sys.path.insert(0, PREDICTION_DIR)
import predict_api as P  # noqa: E402

MODEL_CHOICES = ("lgbm", "xgb", "rf", "lr", "knn", "svm", "dt")
WARMUP_MODEL = os.environ.get("WARMUP_MODEL", "lgbm")

# 已加载的模型 bundle 缓存：{(model, resolvedVersion): (bundle, trained_now)}
# resolvedVersion 变化（promote/rollback）时自动重新加载对应归档，实现治理闭环
_bundle_cache = {}
_loaded = set()
_bundle_lock = threading.Lock()


class PredictIn(BaseModel):
    model: str = Field(default="lgbm")
    category: str = Field(default="美食")
    fans: float = Field(default=0.0, ge=0)
    hour: int = Field(default=20, ge=0, le=23)
    weekday: int = Field(default=5, ge=0, le=6)
    month: int = Field(default=6, ge=1, le=12)


class BatchIn(BaseModel):
    model: str = Field(default="lgbm")
    items: list[PredictIn] = Field(default_factory=list)


def _bundle(name, version=None):
    if name not in MODEL_CHOICES:
        raise HTTPException(status_code=400, detail="model 取值仅支持 " + " / ".join(MODEL_CHOICES))
    resolved = version or P.active_version(name)
    key = (name, resolved or "cache")
    with _bundle_lock:
        if key not in _bundle_cache:
            bundle, trained_now = P.load_or_train(name, version=version)
            _bundle_cache[key] = (bundle, trained_now)
            _loaded.add(name)
        return _bundle_cache[key]


def _predict_one(bundle, item):
    """与 predict_api.predict 完全同口径，额外带上模型指标便于前端展示。"""
    model, meta = bundle["model"], bundle["meta"]
    hour, weekday = int(item.hour), int(item.weekday)
    row = pd.DataFrame([{
        "video_category": str(item.category or "美食"),
        "hour_bucket": P._hour_bucket(hour),
        "author_fans_log": np.log1p(max(float(item.fans or 0), 0.0)),
        "publish_hour": float(hour),
        "publish_weekday": float(weekday),
        "publish_month": float(item.month),
        "is_weekend": 1 if weekday in (5, 6) else 0,
    }])
    X = P._encode_frame(row, meta["cat_maps"], meta["cat_modes"])
    pred_log = float(model.predict(X)[0])
    return {
        "model": item.model,
        "model_version": bundle.get("model_version"),
        "prediction": float(np.expm1(pred_log)),
        "prediction_log": pred_log,
        "metrics": bundle.get("metrics"),
        "metrics_raw": bundle.get("metrics_raw"),
    }


@asynccontextmanager
async def lifespan(_app):
    """启动即预热主模型，避免第一个真实请求承担训练/加载开销。"""
    try:
        P.load_or_train(WARMUP_MODEL)
        _loaded.add(WARMUP_MODEL)
        print("[engine] 预热完成: " + WARMUP_MODEL, flush=True)
    except Exception as exc:  # 预热失败不阻止启动，后续请求会重试
        print("[engine] 预热失败（首次请求将重试）: %s" % exc, flush=True)
    yield


app = FastAPI(title="short-video-heat-engine", version="1.0", lifespan=lifespan)


@app.get("/health")
def health():
    # 暴露已加载模型的版本，便于确认 promote/rollback 后服务是否切换到了对应归档
    loaded_versions = {}
    for name in sorted(_loaded):
        key = (name, P.active_version(name) or "cache")
        cached = _bundle_cache.get(key)
        loaded_versions[name] = cached[0].get("model_version") if cached else None
    return {
        "status": "UP",
        "featureVersion": P.FEATURE_VERSION,
        "warmupModel": WARMUP_MODEL,
        "activeVersion": P.active_version(WARMUP_MODEL),
        "loadedModels": sorted(_loaded),
        "loadedVersions": loaded_versions,
        "pid": os.getpid(),
    }


@app.post("/predict")
def predict(item: PredictIn):
    t0 = time.perf_counter()
    bundle, trained_now = _bundle(item.model)
    result = _predict_one(bundle, item)
    result["trained_now"] = trained_now
    result["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return result


@app.post("/predict/batch")
def predict_batch(payload: BatchIn):
    if not payload.items:
        raise HTTPException(status_code=400, detail="批量预测至少需要一条数据")
    if len(payload.items) > 500:
        raise HTTPException(status_code=400, detail="单次批量预测最多 500 条")
    t0 = time.perf_counter()
    bundle, trained_now = _bundle(payload.model)
    items = []
    for it in payload.items:
        it.model = payload.model
        one = _predict_one(bundle, it)
        one["category"] = it.category
        one["fans"] = it.fans
        one["hour"] = it.hour
        one["weekday"] = it.weekday
        one["month"] = it.month
        items.append(one)
    return {
        "model": payload.model,
        "model_version": bundle.get("model_version"),
        "trained_now": trained_now,
        "count": len(items),
        # 键名与 CLI 批量输出保持一致（Java 侧按 results 解析）
        "results": items,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
    }
