package com.alvis.media.controller;

import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.service.PredictService;
import com.alvis.media.viewmodel.predict.BatchPredictRequestVM;
import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.alvis.media.viewmodel.predict.PredictResultVM;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController("PredictController")
@RequestMapping(value = "/api/predict")
@AllArgsConstructor
public class PredictController extends BaseApiController {

    private final PredictService predictService;

    /** 单条热度预测 */
    @PostMapping
    public RestResponse<PredictResultVM> predict(@RequestBody PredictRequestVM req) {
        return RestResponse.ok(predictService.predict(req));
    }

    /** 批量热度预测（含热度等级） */
    @PostMapping("/batch")
    public RestResponse<JsonNode> predictBatch(@RequestBody BatchPredictRequestVM req) {
        return RestResponse.ok(predictService.predictBatch(req));
    }

    /** 多模型对照：各模型评估指标 */
    @GetMapping("/metrics")
    public RestResponse<JsonNode> metrics() {
        return RestResponse.ok(predictService.metrics());
    }
}
