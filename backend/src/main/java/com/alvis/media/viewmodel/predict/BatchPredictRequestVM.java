package com.alvis.media.viewmodel.predict;

import lombok.Data;

import java.util.List;

/**
 * 批量热度预测请求：一次提交多条视频的先验特征
 */
@Data
public class BatchPredictRequestVM {
    private String model = "lgbm";              // 统一使用的模型
    private List<PredictRequestVM> items;       // 待预测的多条视频
}
