package com.alvis.media.controller;

import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.domain.User;
import com.alvis.media.service.HeatLogService;
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
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController("PredictController")
@RequestMapping(value = "/api/predict")
@AllArgsConstructor
public class PredictController extends BaseApiController {

    private final PredictService predictService;
    private final HeatLogService heatLogService;

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
