package com.alvis.media.controller;

import io.swagger.v3.oas.annotations.tags.Tag;
import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.domain.User;
import com.alvis.media.service.HeatLogService;
import com.alvis.media.service.PredictService;
import com.alvis.media.utility.PythonEngineClient;
import com.alvis.media.viewmodel.predict.BatchPredictRequestVM;
import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.alvis.media.viewmodel.predict.PredictResultVM;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController("PredictController")
@Tag(name = "热度预测")
@RequestMapping(value = "/api/predict")
@AllArgsConstructor
public class PredictController extends BaseApiController {

    private final PredictService predictService;
    private final HeatLogService heatLogService;
    private final PythonEngineClient engineClient;

    /**
     * 90% 保形预测区间：给定同样的输入，返回点预测与保形区间。
     * 区间在样本可交换假设下满足 P(y ∈ [lo, hi]) ≥ 1−α（实测覆盖率见实验中心）。
     */
    @PostMapping("/interval")
    public RestResponse<JsonNode> interval(@RequestBody PredictRequestVM req) {
        return RestResponse.ok(predictService.interval(req));
    }

    /** 常驻推理服务状态：DISABLED（未配置）/ UP / DEGRADED（熔断中，已降级回 CLI） */
    @GetMapping("/engine")
    public RestResponse<Map<String, Object>> engine() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("status", engineClient.status());
        data.put("url", engineClient.baseUrl());
        data.put("lastError", engineClient.lastError());
        return RestResponse.ok(data);
    }

    /** 单条热度预测（并记录） */
    @PostMapping
    public RestResponse<PredictResultVM> predict(@RequestBody PredictRequestVM req) {
        PredictResultVM vm = predictService.predict(req);
        heatLogService.save(req.getModel(), req.getVideoCategory(), req.getAuthorFans(),
                req.getPublishHour(), req.getPublishWeekday(), req.getPublishMonth(),
                vm.getPrediction(), vm.getPredictionLog(), "single", currentUserId());
        return RestResponse.ok(vm);
    }

    /** 批量热度预测（含热度等级，逐条记录） */
    @PostMapping("/batch")
    public RestResponse<JsonNode> predictBatch(@RequestBody BatchPredictRequestVM req) {
        JsonNode node = predictService.predictBatch(req);
        List<PredictRequestVM> items = req.getItems();
        JsonNode results = node.path("results");
        if (items != null && results.isArray()) {
            Integer uid = currentUserId();
            for (int i = 0; i < results.size() && i < items.size(); i++) {
                PredictRequestVM it = items.get(i);
                JsonNode r = results.get(i);
                heatLogService.save(req.getModel(), it.getVideoCategory(), it.getAuthorFans(),
                        it.getPublishHour(), it.getPublishWeekday(), it.getPublishMonth(),
                        r.path("prediction").asDouble(), r.path("prediction_log").asDouble(),
                        "batch", uid);
            }
        }
        return RestResponse.ok(node);
    }

    /** 多模型对照：各模型评估指标 */
    @GetMapping("/metrics")
    public RestResponse<JsonNode> metrics() {
        return RestResponse.ok(predictService.metrics());
    }

    /** 预测记录分页查询 */
    @GetMapping("/logs")
    public RestResponse<JsonNode> logs(@RequestParam(value = "page", defaultValue = "1") int page,
                                       @RequestParam(value = "size", defaultValue = "10") int size) {
        return RestResponse.ok(heatLogService.page(page, size));
    }

    /** 当前登录用户 ID（未登录返回 null，不影响预测） */
    private Integer currentUserId() {
        try {
            User u = getCurrentUser();
            return u == null ? null : u.getId();
        } catch (Exception e) {
            return null;
        }
    }
}
