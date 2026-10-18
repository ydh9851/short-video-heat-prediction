package com.alvis.media.service;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * 预测记录服务：把每次热度预测落库，并提供分页查询
 */
public interface HeatLogService {

    /**
     * 保存一条预测记录（热度等级由服务内部按阈值推导）。
     *
     * @param source single=单条预测 / batch=批量预测
     */
    void save(String model, String category, Double fans, Integer hour, Integer weekday, Integer month,
              Double prediction, Double predictionLog, String source, Integer creatorId);

    /** 分页查询预测记录（按时间倒序） */
    JsonNode page(int page, int size);
}
