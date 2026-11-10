package com.alvis.media.service.impl;

import com.alvis.media.service.ModelRegistryService;
import com.alvis.media.service.PredictService;
import com.alvis.media.service.ShadowService;
import com.alvis.media.utility.PythonCliRunner;
import com.alvis.media.utility.PythonGateway;
import com.alvis.media.viewmodel.predict.BatchPredictRequestVM;
import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.alvis.media.viewmodel.predict.PredictResultVM;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 短视频热度预测：调用 algorithm/prediction/predict_api.py
 * （LightGBM 为主，模型缓存于 model_cache/，首次调用自动训练，之后秒级返回）。
 *
 * <p>预测走 {@link PythonGateway}（HTTP 常驻服务优先 / CLI 降级），
 * 其余保形区间 / what-if / 指标等走 gateway 的 CLI 透传。
 */
@Service
public class PredictServiceImpl implements PredictService {

    /** 保形预测脚本（区间需要「拟合集 + 校准集」两段式训练，故与普通预测分开） */
    @Value("${system.python.conformalScript:}")
    private String conformalScript;

    /** 交互式 what-if 脚本（扫描参数取值，输出响应曲线） */
    @Value("${system.python.whatIfScript:}")
    private String whatIfScript;

    private final StringRedisTemplate redisTemplate;
    private final PythonGateway gateway;
    private final ShadowService shadow;
    private final MeterRegistry meterRegistry;
    private final ModelRegistryService registry;
    private final ObjectMapper om = new ObjectMapper();

    public PredictServiceImpl(StringRedisTemplate redisTemplate, PythonGateway gateway,
                              ShadowService shadow, MeterRegistry meterRegistry,
                              ModelRegistryService registry) {
        this.redisTemplate = redisTemplate;
        this.gateway = gateway;
        this.shadow = shadow;
        this.meterRegistry = meterRegistry;
        this.registry = registry;
    }

    @Override
    public PredictResultVM predict(PredictRequestVM req) {
        // 缓存 key 带上线上版本：promote/rollback 后不会命中旧版本结果
        String activeVersion = registry.activeVersion(req.getModel());
        String cacheKey = "predict:" + req.getModel() + ":" + (activeVersion == null ? "none" : activeVersion)
                + ":" + req.getVideoCategory() + ":"
                + req.getAuthorFans() + ":" + req.getPublishHour() + ":"
                + req.getPublishWeekday() + ":" + req.getPublishMonth();
        try {
            String cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                meterRegistry.counter("predict.requests", "source", "cache").increment();
                return om.readValue(cached, PredictResultVM.class);
            }
        } catch (Exception ignore) {
        }
        long startNanos = System.nanoTime();
        // 统一走 gateway：HTTP 优先，失败自动降级 CLI（降级在 gateway 内部完成）
        String source = "engine";
        PredictResultVM result;
        try {
            JsonNode node = gateway.predict(req, activeVersion);
            result = parse(node);
        } catch (Exception e) {
            // gateway 内部已尝试 HTTP + CLI，都失败才到这里
            throw new RuntimeException("短视频热度预测服务调用失败: " + e.getMessage(), e);
        }
        // 区分来源：gateway 不直接暴露来源标识，这里用降级计数近似（引擎失败会记 fallback counter）
        meterRegistry.counter("predict.requests", "source", source).increment();
        meterRegistry.timer("predict.latency", "source", source)
                .record(System.nanoTime() - startNanos, TimeUnit.NANOSECONDS);
        cacheResult(cacheKey, result);
        // 影子模式：异步给候选模型打分并记录差异，不阻塞本次返回
        if (result.getPrediction() != null) {
            shadow.recordAsync(req, req.getModel(), result.getPrediction());
        }
        return result;
    }

    private void cacheResult(String cacheKey, PredictResultVM vm) {
        try {
            redisTemplate.opsForValue().set(cacheKey, om.writeValueAsString(vm), 1, TimeUnit.HOURS);
        } catch (Exception ignore) {
            // 缓存失败不影响预测结果
        }
    }

    @Override
    public JsonNode predictBatch(BatchPredictRequestVM req) {
        return gateway.predictBatch(req);
    }

    @Override
    public JsonNode metrics() {
        String out = gateway.runCli(gateway.resolvePredictScript(), Arrays.asList("--metrics"));
        try {
            JsonNode node = om.readTree(PythonCliRunner.lastJsonLine(out));
            if (node.hasNonNull("error")) {
                throw new RuntimeException(node.path("error").asText());
            }
            return node;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("解析模型指标失败: " + e.getMessage(), e);
        }
    }

    /**
     * 90% 保形预测区间（Split Conformal + Mondrian 条件覆盖）。
     * 与普通预测分开实现：保形区间需要「拟合集 + 校准集」两段式训练，
     * 校准残差分位数 q̂ 决定区间宽度，并在样本可交换假设下给出有限样本覆盖保证。
     */
    @Override
    public JsonNode interval(PredictRequestVM req) {
        if (req.getVideoCategory() == null || req.getVideoCategory().trim().isEmpty()) {
            req.setVideoCategory("美食");
        }
        if (req.getAuthorFans() == null || req.getAuthorFans() < 0) {
            req.setAuthorFans(0.0);
        }
        if (req.getPublishHour() == null) req.setPublishHour(20);
        if (req.getPublishWeekday() == null) req.setPublishWeekday(5);
        if (req.getPublishMonth() == null) req.setPublishMonth(6);
        if (conformalScript == null || conformalScript.trim().isEmpty()) {
            throw new IllegalStateException("未配置保形预测脚本（system.python.conformalScript）");
        }
        List<String> args = new ArrayList<>();
        args.add("--mode");
        args.add("point");
        args.add("--model");
        args.add(req.getModel() == null || req.getModel().trim().isEmpty() ? "lgbm" : req.getModel().trim());
        args.add("--alpha");
        args.add("0.1");
        args.add("--category");
        args.add(URLEncoder.encode(req.getVideoCategory().trim(), StandardCharsets.UTF_8));
        args.add("--fans");
        args.add(String.valueOf(req.getAuthorFans()));
        args.add("--hour");
        args.add(String.valueOf(req.getPublishHour()));
        args.add("--weekday");
        args.add(String.valueOf(req.getPublishWeekday()));
        args.add("--month");
        args.add(String.valueOf(req.getPublishMonth()));
        try {
            String out = gateway.runCli(conformalScript, args, 180);
            String json = PythonCliRunner.lastJsonLine(out);
            JsonNode node = om.readTree(json);
            if (node.hasNonNull("error")) {
                throw new RuntimeException(node.path("error").asText());
            }
            return node;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("计算保形预测区间失败：" + e.getMessage(), e);
        }
    }

    /**
     * 交互式 what-if：扫描某个参数的全部候选取值，返回响应曲线与最优建议。
     *
     * <p>与反事实分析的区别：反事实回答「改成哪个值」，what-if 把所有取值一次列出，
     * 便于前端画曲线做交互式探索。
     */
    @Override
    public JsonNode whatIf(String dimension, PredictRequestVM req) {
        if (whatIfScript == null || whatIfScript.trim().isEmpty()) {
            throw new IllegalStateException("未配置 what-if 脚本（system.python.whatIfScript）");
        }
        String dim = (dimension == null || dimension.trim().isEmpty()) ? "publishHour" : dimension.trim();
        List<String> args = new ArrayList<>();
        args.add("--dimension");
        args.add(dim);
        args.add("--category");
        args.add(URLEncoder.encode(req.getVideoCategory() == null || req.getVideoCategory().trim().isEmpty()
                ? "美食" : req.getVideoCategory().trim(), StandardCharsets.UTF_8));
        args.add("--fans");
        args.add(String.valueOf(req.getAuthorFans() == null ? 0.0 : req.getAuthorFans()));
        args.add("--hour");
        args.add(String.valueOf(req.getPublishHour() == null ? 20 : req.getPublishHour()));
        args.add("--weekday");
        args.add(String.valueOf(req.getPublishWeekday() == null ? 5 : req.getPublishWeekday()));
        args.add("--month");
        args.add(String.valueOf(req.getPublishMonth() == null ? 6 : req.getPublishMonth()));
        args.add("--model");
        args.add(req.getModel() == null || req.getModel().trim().isEmpty() ? "lgbm" : req.getModel().trim());
        try {
            String out = gateway.runCli(whatIfScript, args, 180);
            String json = PythonCliRunner.lastJsonLine(out);
            JsonNode node = om.readTree(json);
            if (node.hasNonNull("error")) {
                throw new RuntimeException(node.path("error").asText());
            }
            return node;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("计算 what-if 响应曲线失败：" + e.getMessage(), e);
        }
    }

    private PredictResultVM parse(JsonNode root) throws Exception {
        if (root.hasNonNull("error")) {
            throw new RuntimeException(root.path("error").asText());
        }
        PredictResultVM vm = new PredictResultVM();
        vm.setModel(root.path("model").asText());
        // 回传实际参与推理的模型版本，供前端展示与问题追溯
        vm.setModelVersion(root.hasNonNull("model_version") ? root.get("model_version").asText() : null);
        vm.setPrediction(root.hasNonNull("prediction") ? root.get("prediction").asDouble() : null);
        vm.setPredictionLog(root.hasNonNull("prediction_log") ? root.get("prediction_log").asDouble() : null);
        vm.setTrainedNow(root.path("trained_now").asBoolean(false));
        vm.setMetrics(parseMetrics(root.path("metrics")));
        vm.setMetricsRaw(parseMetrics(root.path("metrics_raw")));
        return vm;
    }

    private Map<String, Double> parseMetrics(JsonNode m) {
        Map<String, Double> metrics = new HashMap<>();
        for (String k : new String[]{"rmse", "mae", "r2"}) {
            if (m.hasNonNull(k)) {
                metrics.put(k, m.get(k).asDouble());
            }
        }
        return metrics;
    }
}
