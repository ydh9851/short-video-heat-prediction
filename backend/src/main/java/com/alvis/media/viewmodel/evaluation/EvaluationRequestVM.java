package com.alvis.media.viewmodel.evaluation;

import lombok.Data;

/**
 * 模型评估 / 实验分析请求参数。
 * mode 决定调用哪个算法模块与参数组合，其余字段按需使用。
 */
@Data
public class EvaluationRequestVM {

    /** 实验模式：cv / tuning / learning-curve / importance / residual / ablation
     *  / quantile / quantile-coverage / interaction / counterfactual */
    private String mode;

    /** 数据集平台标识：douyin（默认）/ youtube / tiktok / bilibili */
    private String platform;

    /** 交叉验证折数（mode=cv） */
    private Integer folds;

    /** 随机搜索试验次数（mode=tuning） */
    private Integer trials;

    /** SHAP 采样行数（mode=importance） */
    private Integer sample;

    /** 部分依赖图 / 交互分析的特征（可选） */
    private String feature;

    /** 以下为单样本类模式（quantile / counterfactual）的输入特征 */
    private String category;
    private Double fans;
    private Integer hour;
    private Integer weekday;
    private Integer month;
}
