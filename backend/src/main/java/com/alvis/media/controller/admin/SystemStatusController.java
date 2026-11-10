package com.alvis.media.controller.admin;

import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.configuration.spring.task.EvaluationTaskConfig;
import com.alvis.media.service.ShadowService;
import com.alvis.media.utility.PythonGateway;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.lang.management.ManagementFactory;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 系统状态总览（仅 ADMIN）：聚合推理引擎、实验线程池、预测指标与 JVM 运行状态，
 * 供前端「系统状态页」一屏展示，答辩时可直接证明系统可观测性。
 */
@RestController
@RequestMapping("/api/admin/system")
public class SystemStatusController extends BaseApiController {

    private final PythonGateway pythonGateway;
    private final ThreadPoolTaskExecutor evaluationExecutor;
    private final MeterRegistry meterRegistry;
    private final ShadowService shadowService;

    public SystemStatusController(PythonGateway pythonGateway,
                                  @Qualifier(EvaluationTaskConfig.EXECUTOR_NAME) ThreadPoolTaskExecutor evaluationExecutor,
                                  MeterRegistry meterRegistry,
                                  ShadowService shadowService) {
        this.pythonGateway = pythonGateway;
        this.evaluationExecutor = evaluationExecutor;
        this.meterRegistry = meterRegistry;
        this.shadowService = shadowService;
    }

    @GetMapping("/status")
    public RestResponse<Map<String, Object>> status() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("engine", engineSection());
        data.put("evaluationPool", poolSection());
        data.put("predict", predictSection());
        data.put("shadow", shadowSection());
        data.put("jvm", jvmSection());
        return RestResponse.ok(data);
    }

    /** 常驻推理引擎：状态 / 地址 / 最近错误 */
    private Map<String, Object> engineSection() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("status", pythonGateway.engineStatus());
        m.put("baseUrl", pythonGateway.engineBaseUrl());
        m.put("lastError", pythonGateway.engineLastError());
        return m;
    }

    /** 实验线程池：活跃线程 / 队列积压 / 累计完成 */
    private Map<String, Object> poolSection() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("activeCount", evaluationExecutor.getActiveCount());
        m.put("poolSize", evaluationExecutor.getPoolSize());
        m.put("corePoolSize", evaluationExecutor.getCorePoolSize());
        m.put("maxPoolSize", evaluationExecutor.getMaxPoolSize());
        m.put("queueSize", evaluationExecutor.getThreadPoolExecutor().getQueue().size());
        m.put("queueCapacity", evaluationExecutor.getThreadPoolExecutor().getQueue().remainingCapacity()
                + evaluationExecutor.getThreadPoolExecutor().getQueue().size());
        m.put("completedTaskCount", evaluationExecutor.getThreadPoolExecutor().getCompletedTaskCount());
        m.put("taskCount", evaluationExecutor.getThreadPoolExecutor().getTaskCount());
        return m;
    }

    /** 预测请求指标：按来源（cache/engine/cli）计数与延迟 */
    private Map<String, Object> predictSection() {
        Map<String, Object> m = new LinkedHashMap<>();
        Map<String, Double> requests = new LinkedHashMap<>();
        for (Counter c : meterRegistry.find("predict.requests").counters()) {
            String source = c.getId().getTag("source");
            requests.put(source == null ? "unknown" : source, c.count());
        }
        m.put("requests", requests);
        double total = requests.values().stream().mapToDouble(Double::doubleValue).sum();
        m.put("total", total);
        Timer timer = meterRegistry.find("predict.latency").timer();
        if (timer != null && timer.count() > 0) {
            m.put("count", timer.count());
            m.put("meanMs", Math.round(timer.mean(TimeUnit.MILLISECONDS) * 10) / 10.0);
            m.put("maxMs", Math.round(timer.max(TimeUnit.MILLISECONDS) * 10) / 10.0);
        }
        return m;
    }

    /** 影子模式：开启状态与样本量 */
    private Map<String, Object> shadowSection() {
        Map<String, Object> m = new LinkedHashMap<>();
        try {
            m.put("stats", shadowService.stats(1));
        } catch (Exception e) {
            m.put("error", e.getMessage());
        }
        return m;
    }

    /** JVM：运行时长 / 内存水位 */
    private Map<String, Object> jvmSection() {
        Map<String, Object> m = new LinkedHashMap<>();
        Runtime rt = Runtime.getRuntime();
        long uptimeMs = ManagementFactory.getRuntimeMXBean().getUptime();
        m.put("uptimeSeconds", uptimeMs / 1000);
        m.put("processors", rt.availableProcessors());
        long max = rt.maxMemory();
        long used = rt.totalMemory() - rt.freeMemory();
        m.put("memoryUsedMB", used / 1024 / 1024);
        m.put("memoryMaxMB", max / 1024 / 1024);
        m.put("memoryUsagePercent", max > 0 ? Math.round(used * 1000.0 / max) / 10.0 : 0);
        return m;
    }
}
