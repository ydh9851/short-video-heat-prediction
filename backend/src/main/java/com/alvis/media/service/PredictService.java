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

    /**
     * 90% 保形预测区间（Split Conformal + Mondrian 条件覆盖）。
     * 返回 {prediction, lo, hi, grade, qhat_used, target_coverage, ...}。
     */
    JsonNode interval(PredictRequestVM req);

    /**
     * 交互式 what-if：扫描某个参数的候选取值，返回预测值序列与最优建议。
     *
     * @param dimension 扫描维度：publishHour / publishWeekday / publishMonth / videoCategory
     * @param req       当前参数（作为基线）
     * @return {dimension, baseline, candidates:[{value,label,prediction,grade,gain,gain_pct}], best}
     */
    JsonNode whatIf(String dimension, PredictRequestVM req);
}
