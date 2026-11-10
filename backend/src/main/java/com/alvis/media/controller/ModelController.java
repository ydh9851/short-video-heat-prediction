package com.alvis.media.controller;

import io.swagger.v3.oas.annotations.tags.Tag;
import com.alvis.media.annotation.OperationLog;
import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.domain.Job;
import com.alvis.media.exception.BusinessException;
import com.alvis.media.service.DriftService;
import com.alvis.media.service.JobService;
import com.alvis.media.service.ModelRegistryService;
import com.alvis.media.service.RehearsalService;
import com.alvis.media.service.ShadowService;
import com.alvis.media.utility.DerivedCacheEvictor;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 模型治理接口：注册表（版本 + 阶段）、影子模式、漂移监控与上线预演。
 *
 * <p>治理闭环：漂移监控回答「数据分布是否还稳定」；上线预演回答「换版本后输出会跳变多少」，
 * 预演通过才允许直接 promote（可人工强制）；版本切换 / 回滚后主动失效派生缓存。
 */
@RestController("ModelController")
@Tag(name = "模型治理")
@RequestMapping(value = "/api/models")
@AllArgsConstructor
public class ModelController extends BaseApiController {

    private final ModelRegistryService registryService;

    private final ShadowService shadowService;

    private final DriftService driftService;

    private final RehearsalService rehearsalService;

    private final JobService jobService;

    private final DerivedCacheEvictor cacheEvictor;

    /** 静态常量：lombok @AllArgsConstructor 不会注入静态字段 */
    private static final ObjectMapper OM = new ObjectMapper();

    /** 模型注册表摘要（不触发扫描） */
    @GetMapping
    public RestResponse<JsonNode> list() {
        return RestResponse.ok(registryService.list());
    }

    /** 扫描 model_cache，把新训练的模型登记进注册表（新版本默认 staging） */
    @PostMapping("/sync")
    @OperationLog("model.sync")
    public RestResponse<JsonNode> sync() {
        return RestResponse.ok(registryService.sync());
    }

    /**
     * 把指定版本切为线上（production），其余归档。
     * 默认要求该版本已通过上线预演；force=true 跳过门禁（保留审计日志）。
     */
    @PostMapping("/{model}/promote")
    @OperationLog("model.promote")
    public RestResponse<JsonNode> promote(@PathVariable("model") String model,
                                          @RequestParam("version") String version,
                                          @RequestParam(value = "force", defaultValue = "false") boolean force) {
        if (!force) {
            rehearsalService.requirePassed(model, version);
        }
        JsonNode result = registryService.promote(model, version);
        // 版本切换联动：旧版本 key 的预测/归因/分级缓存立即失效，避免「切换了但页面没变」
        cacheEvictor.evictAll();
        return RestResponse.ok(result);
    }

    /** 回滚到上一个可用版本 */
    @PostMapping("/{model}/rollback")
    @OperationLog("model.rollback")
    public RestResponse<JsonNode> rollback(@PathVariable("model") String model) {
        JsonNode result = registryService.rollback(model);
        cacheEvictor.evictAll();
        return RestResponse.ok(result);
    }

    /** 影子模式统计：样本数、平均/中位/90 分位绝对偏差、最近记录 */
    @GetMapping("/shadow")
    public RestResponse<JsonNode> shadow(@RequestParam(value = "recent", defaultValue = "10") int recent) {
        return RestResponse.ok(shadowService.stats(recent));
    }

    /** 提交漂移检测任务（异步执行，前端轮询 job 状态） */
    @PostMapping("/drift/run")
    @OperationLog("model.drift")
    public RestResponse<JsonNode> driftRun() {
        Long jobId = driftService.submit();
        ObjectNode node = OM.createObjectNode();
        node.put("jobId", jobId);
        return RestResponse.ok(node);
    }

    /** 最新一份漂移报告（含逐平台×特征明细），无报告时 response 为 null */
    @GetMapping("/drift/latest")
    public RestResponse<JsonNode> driftLatest() {
        return RestResponse.ok(driftService.latest());
    }

    /** 提交上线预演任务：候选版本 vs 当前线上版本，真实采样并行打分 */
    @PostMapping("/{model}/rehearsal")
    @OperationLog("model.rehearsal")
    public RestResponse<JsonNode> rehearsalRun(@PathVariable("model") String model,
                                               @RequestParam("version") String version) {
        Long jobId = rehearsalService.submit(model, version);
        ObjectNode node = OM.createObjectNode();
        node.put("jobId", jobId);
        return RestResponse.ok(node);
    }

    /** 该（模型, 候选版本）最新一份预演报告 */
    @GetMapping("/{model}/rehearsal")
    public RestResponse<JsonNode> rehearsalLatest(@PathVariable("model") String model,
                                                  @RequestParam("version") String version) {
        return RestResponse.ok(rehearsalService.latest(model, version));
    }

    /**
     * 治理任务状态查询（前端轮询用）。
     * 仅放行治理类任务（漂移/预演），平台通用任务仍走 /api/admin/job。
     */
    @GetMapping("/job/{id}")
    public RestResponse<Job> job(@PathVariable("id") Long id) {
        Job job = jobService.get(id);
        if (job == null || !(("model.drift".equals(job.getJobType()) || "model.rehearsal".equals(job.getJobType())))) {
            throw new BusinessException(404, "任务不存在");
        }
        return RestResponse.ok(job);
    }
}
