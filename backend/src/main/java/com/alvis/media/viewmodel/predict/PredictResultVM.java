package com.alvis.media.viewmodel.predict;

import lombok.Data;

import java.util.Map;

/**
 * 短视频热度预测结果
 */
@Data
public class PredictResultVM {
    private String model;                    // 使用的模型 lgbm|xgb|rf|lr|knn|svm|dt
    private Double prediction;               // 预测热度（原始空间，加权互动量）
    private Double predictionLog;            // 预测热度（log1p 空间）
    private Boolean trainedNow;              // 本次调用是否新训练了模型
    private Map<String, Double> metrics;     // log 空间评估指标 rmse/mae/r2（测试集）
    private Map<String, Double> metricsRaw;  // 原始热度空间评估指标 rmse/mae/r2
}
