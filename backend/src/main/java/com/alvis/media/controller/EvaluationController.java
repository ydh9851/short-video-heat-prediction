package com.alvis.media.controller;

import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.service.EvaluationService;
import com.alvis.media.service.EvaluationTaskService;
import com.alvis.media.viewmodel.evaluation.EvaluationRequestVM;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 模型评估与实验分析接口
 * -----------------------------------------
 * 为「论文实验章节」提供可复现的在线实验能力：交叉验证、超参数搜索、
 * 学习曲线、特征重要性对照、残差分析、特征消融、预测区间、SHAP 交互、反事实分析。
 *
 * <p>三类接口：
 * <ul>
 *   <li>{@code /submit} + {@code /task/{id}}：异步执行（推荐，前端轮询进度，不会被 15 分钟超时卡住）；</li>
 *   <li>{@code /run}：同步执行，保留给脚本 / 调试场景；</li>
 *   <li>{@code /tasks}：最近实验任务列表。</li>
 * </ul>
 */
@RestController("EvaluationController")
@RequestMapping(value = "/api/evaluation")
@AllArgsConstructor
public class EvaluationController extends BaseApiController {

    private final EvaluationService evaluationService;

    private final EvaluationTaskService evaluationTaskService;

    /** 支持的实验模式元信息（前端据此渲染实验列表） */
    @GetMapping("/modes")
    public RestResponse<JsonNode> modes() {
        return RestResponse.ok(evaluationService.modes());
    }

    /** 异步提交实验：立即返回 taskId，实验在线程池中执行 */
    @PostMapping("/submit")
    public RestResponse<Map<String, Object>> submit(@RequestBody EvaluationRequestVM req) {
        String taskId = evaluationTaskService.submit(req);
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("taskId", taskId);
        data.put("status", "QUEUED");
        return RestResponse.ok(data);
    }

    /** 查询实验任务状态：QUEUED / RUNNING / DONE / FAILED，DONE 时带 result */
    @GetMapping("/task/{taskId}")
    public RestResponse<Map<String, Object>> task(@PathVariable("taskId") String taskId) {
        Map<String, Object> task = evaluationTaskService.get(taskId);
        if (task == null) {
            return RestResponse.fail(404, "实验任务不存在或已过期（任务状态保留 24 小时）");
        }
        return RestResponse.ok(task);
    }

    /** 最近 30 条实验任务（摘要，不含 result） */
    @GetMapping("/tasks")
    public RestResponse<List<Map<String, Object>>> tasks() {
        return RestResponse.ok(evaluationTaskService.recent());
    }

    /**
     * 同步执行指定实验（耗时较长，仅建议脚本/调试使用）。
     * 前端已改为 /submit + /task 轮询，避免长连接等待。
     */
    @PostMapping("/run")
    public RestResponse<JsonNode> run(@RequestBody EvaluationRequestVM req) {
        return RestResponse.ok(evaluationService.run(req));
    }
}
