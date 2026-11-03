package com.alvis.media.service.impl;

import com.alvis.media.service.PredictService;
import com.alvis.media.service.ShadowService;
import com.alvis.media.utility.PythonCliRunner;
import com.alvis.media.utility.PythonEngineClient;
import com.alvis.media.viewmodel.predict.BatchPredictRequestVM;
import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.alvis.media.viewmodel.predict.PredictResultVM;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 短视频热度预测：调用 algorithm/prediction/predict_api.py
 * （LightGBM 为主，模型缓存于 model_cache/，首次调用自动训练，之后秒级返回）。
 */
@Service
public class PredictServiceImpl implements PredictService {

    @Value("${system.python.path:python}")
    private String pythonPath;
    @Value("${system.python.script:}")
    private String scriptPath;
    @Value("${system.python.predictScript:}")
    private String predictScript;

    /** 保形预测脚本（区间需要「拟合集 + 校准集」两段式训练，故与普通预测分开） */
    @Value("${system.python.conformalScript:}")
    private String conformalScript;

    /** 交互式 what-if 脚本（扫描参数取值，输出响应曲线） */
    @Value("${system.python.whatIfScript:}")
    private String whatIfScript;

    private static final Logger log = LoggerFactory.getLogger(PredictServiceImpl.class);

    private final StringRedisTemplate redisTemplate;
    private final PythonCliRunner runner;
    private final PythonEngineClient engine;
    private final ShadowService shadow;
    private final MeterRegistry meterRegistry;
    private final ObjectMapper om = new ObjectMapper();

    private static final List<String> MODELS =
            Arrays.asList("lgbm", "xgb", "rf", "lr", "knn", "svm", "dt");

    public PredictServiceImpl(StringRedisTemplate redisTemplate, PythonCliRunner runner,
                              PythonEngineClient engine, ShadowService shadow,
                              MeterRegistry meterRegistry) {
        this.redisTemplate = redisTemplate;
        this.runner = runner;
        this.engine = engine;
        this.shadow = shadow;
        this.meterRegistry = meterRegistry;
    }

    @Override
    public PredictResultVM predict(PredictRequestVM req) {
        validate(req);
        String cacheKey = "predict:" + req.getModel() + ":" + req.getVideoCategory() + ":"
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
        // 首选常驻推理服务（几十毫秒）；不可用时自动降级到 CLI 通道
        String source = "engine";
        PredictResultVM result = callEngine(req);
        if (result == null) {
            source = "cli";
            try {
                result = parse(callPython(req));
            } catch (Exception e) {
                throw new RuntimeException("短视频热度预测服务调用失败: " + e.getMessage(), e);
            }
        }
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

    /** 走常驻推理服务；未启用/熔断/失败都返回 null，由调用方回落到 CLI。 */
    private PredictResultVM callEngine(PredictRequestVM req) {
        if (!engine.available()) {
            return null;
        }
        try {
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("model", req.getModel());
            body.put("category", req.getVideoCategory());
            body.put("fans", req.getAuthorFans());
            body.put("hour", req.getPublishHour());
            body.put("weekday", req.getPublishWeekday());
            body.put("month", req.getPublishMonth());
            return parse(engine.post("/predict", body).toString());
        } catch (Exception e) {
            meterRegistry.counter("predict.engine.fallback").increment();
            log.warn("预测请求降级到 CLI 通道：{}", e.getMessage());
            return null;
        }
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
        String model = req.getModel();
        if (model == null || model.isEmpty()) {
            model = "lgbm";
        }
        if (!MODELS.contains(model)) {
            throw new IllegalArgumentException("model 取值仅支持 lgbm / xgb / rf / lr / knn / svm / dt");
        }
        List<PredictRequestVM> items = req.getItems();
        if (items == null || items.isEmpty()) {
            throw new IllegalArgumentException("批量预测至少需要一条数据");
        }
        if (items.size() > 500) {
            throw new IllegalArgumentException("单次批量预测最多 500 条");
        }

        // 组装 Python 端批量预测所需的 JSON（字段名：category/fans/hour/weekday/month）
        List<Map<String, Object>> payload = new ArrayList<>();
        for (PredictRequestVM it : items) {
            Map<String, Object> m = new HashMap<>();
            String cat = (it.getVideoCategory() == null || it.getVideoCategory().trim().isEmpty())
                    ? "美食" : it.getVideoCategory().trim();
            m.put("category", cat);   // 写入文件传输，无需 URL 编码
            m.put("fans", it.getAuthorFans() == null ? 0.0 : it.getAuthorFans());
            m.put("hour", it.getPublishHour() == null ? 20 : it.getPublishHour());
            m.put("weekday", it.getPublishWeekday() == null ? 5 : it.getPublishWeekday());
            m.put("month", it.getPublishMonth() == null ? 6 : it.getPublishMonth());
            payload.add(m);
        }

        File tmp = null;
        try {
            tmp = File.createTempFile("heat_batch_", ".json");
            om.writeValue(tmp, payload);   // ObjectMapper 默认写 UTF-8
            String out = runner.run(resolvePredictScript(),
                    Arrays.asList("--model", model, "--batch", tmp.getAbsolutePath()));
            JsonNode node = om.readTree(PythonCliRunner.lastJsonLine(out));
            if (node.hasNonNull("error")) {
                throw new RuntimeException(node.path("error").asText());
            }
            return node;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("批量预测失败: " + e.getMessage(), e);
        } finally {
            if (tmp != null && tmp.exists()) {
                tmp.delete();
            }
        }
    }

    @Override
    public JsonNode metrics() {
        String out = runner.run(resolvePredictScript(), Arrays.asList("--metrics"));
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

    private void validate(PredictRequestVM req) {
        if (req.getModel() == null || req.getModel().isEmpty()) {
            req.setModel("lgbm");
        }
        if (!MODELS.contains(req.getModel())) {
            throw new IllegalArgumentException("model 取值仅支持 lgbm / xgb / rf / lr / knn / svm / dt");
        }
        if (req.getVideoCategory() == null || req.getVideoCategory().trim().isEmpty()) {
            req.setVideoCategory("美食");
        }
        if (req.getAuthorFans() == null || req.getAuthorFans() < 0) {
            req.setAuthorFans(0.0);
        }
        if (req.getPublishHour() == null || req.getPublishHour() < 0 || req.getPublishHour() > 23) {
            throw new IllegalArgumentException("请填写有效的发布小时（0-23）");
        }
        if (req.getPublishWeekday() == null || req.getPublishWeekday() < 0 || req.getPublishWeekday() > 6) {
            throw new IllegalArgumentException("请填写有效的发布星期（0-6，0=周一）");
        }
        if (req.getPublishMonth() == null || req.getPublishMonth() < 1 || req.getPublishMonth() > 12) {
            throw new IllegalArgumentException("请填写有效的发布月份（1-12）");
        }
    }

    private String resolvePredictScript() {
        if (predictScript != null && !predictScript.trim().isEmpty()) {
            return predictScript.trim();
        }
        if (scriptPath != null && !scriptPath.trim().isEmpty()) {
            File parent = new File(scriptPath.trim()).getParentFile();
            if (parent != null) {
                return new File(parent, "predict_api.py").getAbsolutePath();
            }
        }
        throw new IllegalStateException("未配置 Python 热度预测脚本路径（system.python.predictScript）");
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
            String out = runner.run(conformalScript, args, 180);
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
            String out = runner.run(whatIfScript, args, 180);
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

    private String callPython(PredictRequestVM req) throws Exception {
        List<String> cmd = new ArrayList<>();
        cmd.add(pythonPath);
        cmd.add(resolvePredictScript());
        cmd.add("--model"); cmd.add(req.getModel());
        // 中文类别参数改为 URL 编码后传递（纯 ASCII），
        // 规避 JDK/中文 Windows 下 ProcessBuilder argv 按本地代码页编码可能破坏非 ASCII 参数的坑
        cmd.add("--category"); cmd.add(URLEncoder.encode(req.getVideoCategory().trim(), StandardCharsets.UTF_8));
        cmd.add("--fans"); cmd.add(String.valueOf(req.getAuthorFans()));
        cmd.add("--hour"); cmd.add(String.valueOf(req.getPublishHour()));
        cmd.add("--weekday"); cmd.add(String.valueOf(req.getPublishWeekday()));
        cmd.add("--month"); cmd.add(String.valueOf(req.getPublishMonth()));

        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectErrorStream(true);
        Process p = pb.start();
        StringBuilder sb = new StringBuilder();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line).append('\n');
            }
        }
        int code = p.waitFor();
        if (code != 0) {
            throw new RuntimeException("python exit " + code + ": " + sb);
        }
        return sb.toString().trim();
    }

    private PredictResultVM parse(String json) throws Exception {
        // python 输出可能混入告警行，只取最后一行非空文本作为 JSON
        String lastLine = json;
        for (String line : json.split("\\r?\\n")) {
            if (!line.trim().isEmpty()) {
                lastLine = line.trim();
            }
        }
        JsonNode root = om.readTree(lastLine);
        if (root.hasNonNull("error")) {
            throw new RuntimeException(root.path("error").asText());
        }
        PredictResultVM vm = new PredictResultVM();
        vm.setModel(root.path("model").asText());
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
