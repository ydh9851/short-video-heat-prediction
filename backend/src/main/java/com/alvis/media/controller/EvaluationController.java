package com.alvis.media.controller;

import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.service.EvaluationService;
import com.alvis.media.viewmodel.evaluation.EvaluationRequestVM;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 模型评估与实验分析接口
 * -----------------------------------------
 * 为「论文实验章节」提供可复现的在线实验能力：交叉验证、超参数搜索、
 * 学习曲线、特征重要性对照、残差分析、特征消融、预测区间、SHAP 交互、反事实分析。
 */
@RestController("EvaluationController")
@RequestMapping(value = "/api/evaluation")
@AllArgsConstructor
public class EvaluationController extends BaseApiController {

    private final EvaluationService evaluationService;

    /** 支持的实验模式元信息（前端据此渲染实验列表） */
    @GetMapping("/modes")
    public RestResponse<JsonNode> modes() {
        return RestResponse.ok(evaluationService.modes());
    }

    /** 执行指定实验（耗时较长，前端需放宽超时） */
    @PostMapping("/run")
    public RestResponse<JsonNode> run(@RequestBody EvaluationRequestVM req) {
        return RestResponse.ok(evaluationService.run(req));
    }
}
