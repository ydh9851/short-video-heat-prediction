package com.alvis.media.service;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * 数据管理服务：读取清洗后的规范化数据集，提供总览统计与样本分页预览
 */
public interface DataService {

    /** 数据集总览：样本量、类别分布、热度分位、时间跨度、等级分布等 */
    JsonNode overview();

    /** 样本分页预览（可按类别筛选） */
    JsonNode samples(int page, int size, String category);
}
