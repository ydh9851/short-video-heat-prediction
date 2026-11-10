package com.alvis.media.service;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;

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

    /**
     * 批量保存预测记录：一次 round-trip 写入多行（batchUpdate），
     * 避免 N 次 INSERT 的网络与事务开销（500 条批量预测从 500 次插入降为 1 次）。
     */
    void saveBatch(List<Entry> entries);

    /** 分页查询预测记录（按时间倒序） */
    JsonNode page(int page, int size);

    /** 批量写库的记录单元 */
    class Entry {
        public final String model;
        public final String category;
        public final Double fans;
        public final Integer hour;
        public final Integer weekday;
        public final Integer month;
        public final Double prediction;
        public final Double predictionLog;
        public final String source;
        public final Integer creatorId;

        public Entry(String model, String category, Double fans, Integer hour, Integer weekday, Integer month,
                     Double prediction, Double predictionLog, String source, Integer creatorId) {
            this.model = model;
            this.category = category;
            this.fans = fans;
            this.hour = hour;
            this.weekday = weekday;
            this.month = month;
            this.prediction = prediction;
            this.predictionLog = predictionLog;
            this.source = source;
            this.creatorId = creatorId;
        }
    }
}
