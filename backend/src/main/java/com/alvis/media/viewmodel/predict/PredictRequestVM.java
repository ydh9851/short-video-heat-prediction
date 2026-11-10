package com.alvis.media.viewmodel.predict;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 短视频热度预测请求参数
 * 对应 algorithm/prediction/predict_api.py 的 CLI 参数。
 * 字段为「视频发布时即可获得」的先验信息（防数据泄漏，详见 preprocess.py）。
 */
@Data
public class PredictRequestVM {
    @NotBlank(message = "模型名称不能为空")
    private String model = "lgbm";            // lgbm|xgb|rf|lr|knn|svm|dt

    @NotBlank(message = "视频类别不能为空")
    private String videoCategory = "美食";    // 视频类别（美食/音乐/旅行/...）

    @NotNull(message = "粉丝数不能为空")
    @Min(value = 0, message = "粉丝数不能为负数")
    private Double authorFans = 1000.0;       // 作者粉丝数

    @NotNull(message = "发布小时不能为空")
    @Min(value = 0, message = "发布小时需在 0-23 之间")
    @Max(value = 23, message = "发布小时需在 0-23 之间")
    private Integer publishHour = 20;         // 发布小时 0-23

    @NotNull(message = "发布星期不能为空")
    @Min(value = 0, message = "发布星期需在 0-6 之间")
    @Max(value = 6, message = "发布星期需在 0-6 之间")
    private Integer publishWeekday = 5;       // 发布星期 0-6（0=周一）

    @NotNull(message = "发布月份不能为空")
    @Min(value = 1, message = "发布月份需在 1-12 之间")
    @Max(value = 12, message = "发布月份需在 1-12 之间")
    private Integer publishMonth = 6;         // 发布月份 1-12
}
