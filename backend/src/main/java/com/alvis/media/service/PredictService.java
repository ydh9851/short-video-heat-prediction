package com.alvis.media.service;

import com.alvis.media.viewmodel.predict.BatchPredictRequestVM;
import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.alvis.media.viewmodel.predict.PredictResultVM;
import com.fasterxml.jackson.databind.JsonNode;

public interface PredictService {

    /** 单条热度预测 */
    PredictResultVM predict(PredictRequestVM req);

    /** 批量热度预测（含热度等级） */
    JsonNode predictBatch(BatchPredictRequestVM req);

    /** 各已缓存模型的评估指标（多模型对照实验） */
    JsonNode metrics();
}
