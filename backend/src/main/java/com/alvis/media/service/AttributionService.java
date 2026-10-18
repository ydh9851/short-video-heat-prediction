package com.alvis.media.service;

import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.fasterxml.jackson.databind.JsonNode;

/**
 * 热度归因分析（SHAP 可解释性）服务
 */
public interface AttributionService {

    /** 全局归因：特征重要性 / SHAP 汇总（含图） */
    JsonNode global();

    /** 单样本归因：某条视频各特征对预测热度的推高/拉低贡献 + 运营建议 */
    JsonNode explain(PredictRequestVM req);

    /** 部分依赖图：某特征变化对平均热度的影响 */
    JsonNode pdp(String feature);
}
