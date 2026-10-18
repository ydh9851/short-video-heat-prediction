package com.alvis.media.controller;

import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.service.AttributionService;
import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.*;

/**
 * 热度归因分析（SHAP 可解释性）接口
 */
@RestController("AttributionController")
@RequestMapping(value = "/api/attribution")
@AllArgsConstructor
public class AttributionController extends BaseApiController {

    private final AttributionService attributionService;

    /** 全局归因：特征重要性 + SHAP 汇总图 */
    @GetMapping("/global")
    public RestResponse<JsonNode> global() {
        return RestResponse.ok(attributionService.global());
    }

    /** 单样本归因：一条视频的各特征贡献 + 运营建议 */
    @PostMapping("/explain")
    public RestResponse<JsonNode> explain(@RequestBody PredictRequestVM req) {
        return RestResponse.ok(attributionService.explain(req));
    }

    /** 部分依赖图：某特征变化对平均热度的影响 */
    @GetMapping("/pdp")
    public RestResponse<JsonNode> pdp(@RequestParam(value = "feature", required = false) String feature) {
        return RestResponse.ok(attributionService.pdp(feature));
    }
}
