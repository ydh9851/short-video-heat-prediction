package com.alvis.media.viewmodel.predict;

import lombok.Data;

/**
 * 短视频热度预测请求参数
 * 对应 algorithm/prediction/predict_api.py 的 CLI 参数。
 * 字段为「视频发布时即可获得」的先验信息（防数据泄漏，详见 preprocess.py）。
 */
@Data
public class PredictRequestVM {
    private String model = "lgbm";            // lgbm|xgb|rf|lr|knn|svm|dt
    private String videoCategory = "美食";    // 视频类别（美食/音乐/旅行/...）
    private Double authorFans = 1000.0;       // 作者粉丝数
    private Integer publishHour = 20;         // 发布小时 0-23
    private Integer publishWeekday = 5;       // 发布星期 0-6（0=周一）
    private Integer publishMonth = 6;         // 发布月份 1-12
}
