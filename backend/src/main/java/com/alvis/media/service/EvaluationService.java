package com.alvis.media.service;

import com.alvis.media.viewmodel.evaluation.EvaluationRequestVM;
import com.fasterxml.jackson.databind.JsonNode;

/**
 * 模型评估与实验分析：统一调度 algorithm/evaluation、prediction/quantile_predict、
 * attribution（交互效应 / 反事实）等 Python 算法模块，提供可复现的实验结果。
 */
public interface EvaluationService {

    /** 按 mode 执行对应实验，返回 Python 端单行 JSON 解析结果 */
    JsonNode run(EvaluationRequestVM req);

    /** 返回支持的实验模式元信息（供前端渲染列表，含产出图片文件名） */
    JsonNode modes();
}
