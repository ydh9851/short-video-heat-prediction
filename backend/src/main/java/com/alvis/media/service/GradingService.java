package com.alvis.media.service;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * 热度分级服务（K-Means 聚类定等级 + 分类模型预测等级）
 */
public interface GradingService {

    /** 训练/获取热度分级结果：等级名称、阈值、分布、分类指标与图 */
    JsonNode grade(int k);
}
