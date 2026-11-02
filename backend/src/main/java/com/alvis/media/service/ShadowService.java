package com.alvis.media.service;

import com.alvis.media.utility.PythonEngineClient;
import com.alvis.media.utility.TraceContext;
import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 影子模式（Shadow Deployment）：线上模型照常返回结果，另一个候选模型**并行打分**，
 * 只记录差异、不影响返回。用于在真正切换模型前，用真实流量验证新模型的偏差。
 *
 * <p>实现约束：
 * <ul>
 *   <li>必须在**异步线程**里执行，绝不能拖慢主请求；</li>
 *   <li>只在常驻推理服务可用时生效，避免为影子打分反复拉起 Python 进程；</li>
 *   <li>结果追加到 {@code data/logs/shadow_predictions.jsonl}，可直接用 pandas 分析。</li>
 * </ul>
 */
@Service
public class ShadowService {

    private static final Logger log = LoggerFactory.getLogger(ShadowService.class);
    private static final String FILE_NAME = "shadow_predictions.jsonl";
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Value("${system.model.shadowEnabled:true}")
    private boolean shadowEnabled;

    @Value("${system.model.shadowModel:rf}")
    private String shadowModel;

    @Value("${system.data.logDir:../data/logs}")
    private String logDir;

    private final PythonEngineClient engine;
    private final ObjectMapper om = new ObjectMapper();

    private final ExecutorService executor = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "shadow-scorer");
        t.setDaemon(true);
        return t;
    });

    public ShadowService(PythonEngineClient engine) {
        this.engine = engine;
    }

    /** 该请求是否需要影子打分（同一模型自比没有意义）。 */
    public boolean enabledFor(String primaryModel) {
        return shadowEnabled && shadowModel != null && !shadowModel.trim().isEmpty()
                && !shadowModel.trim().equals(primaryModel);
    }

    /**
     * 异步记录一次影子打分；任何异常只记日志，绝不影响主流程。
     */
    public void recordAsync(PredictRequestVM req, String primaryModel, double primaryPrediction) {
        if (!enabledFor(primaryModel) || !engine.available()) {
            return;
        }
        String traceId = TraceContext.current();
        try {
            executor.submit(() -> {
                try {
                    Map<String, Object> body = new LinkedHashMap<>();
                    body.put("model", shadowModel.trim());
                    body.put("category", req.getVideoCategory());
                    body.put("fans", req.getAuthorFans());
                    body.put("hour", req.getPublishHour());
                    body.put("weekday", req.getPublishWeekday());
                    body.put("month", req.getPublishMonth());
                    JsonNode node = engine.post("/predict", body);
                    double shadow = node.path("prediction").asDouble();
                    double diffPct = primaryPrediction == 0 ? 0 : (shadow - primaryPrediction) / primaryPrediction * 100.0;

                    ObjectNode rec = om.createObjectNode();
                    rec.put("ts", LocalDateTime.now().format(TIME));
                    rec.put("traceId", traceId);
                    rec.put("primaryModel", primaryModel);
                    rec.put("shadowModel", shadowModel.trim());
                    rec.put("primary", Math.round(primaryPrediction * 100) / 100.0);
                    rec.put("shadow", Math.round(shadow * 100) / 100.0);
                    rec.put("diffPct", Math.round(diffPct * 100) / 100.0);
                    append(rec);
                } catch (Exception e) {
                    log.debug("影子打分失败（不影响主流程）：{}", e.getMessage());
                }
            });
        } catch (Exception e) {
            log.debug("影子任务提交失败：{}", e.getMessage());
        }
    }

    private synchronized void append(ObjectNode rec) {
        try {
            Path dir = Paths.get(logDir).toAbsolutePath().normalize();
            Files.createDirectories(dir);
            Files.writeString(dir.resolve(FILE_NAME), om.writeValueAsString(rec) + System.lineSeparator(),
                    StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException e) {
            log.warn("写入影子打分记录失败：{}", e.getMessage());
        }
    }

    /** 影子对比统计：样本数、平均/中位绝对偏差、最近记录。 */
    public JsonNode stats(int recentLimit) {
        ObjectNode root = om.createObjectNode();
        root.put("enabled", shadowEnabled);
        root.put("shadowModel", shadowModel);
        root.put("engineStatus", engine.status());
        Path file = Paths.get(logDir).toAbsolutePath().normalize().resolve(FILE_NAME);
        ArrayNode recent = root.putArray("recent");
        if (!Files.isRegularFile(file)) {
            root.put("count", 0);
            return root;
        }
        List<Double> diffs = new ArrayList<>();
        List<String> lines = Collections.emptyList();
        try {
            lines = Files.readAllLines(file, StandardCharsets.UTF_8);
        } catch (IOException e) {
            root.put("count", 0);
            return root;
        }
        for (String line : lines) {
            if (line.trim().isEmpty()) {
                continue;
            }
            try {
                JsonNode rec = om.readTree(line);
                diffs.add(Math.abs(rec.path("diffPct").asDouble()));
            } catch (Exception ignore) {
                // 跳过损坏行
            }
        }
        for (int i = lines.size() - 1; i >= 0 && recent.size() < Math.max(1, recentLimit); i--) {
            try {
                recent.add(om.readTree(lines.get(i)));
            } catch (Exception ignore) {
                // 同上
            }
        }
        if (diffs.isEmpty()) {
            root.put("count", 0);
            return root;
        }
        Collections.sort(diffs);
        double mean = diffs.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        root.put("count", diffs.size());
        root.put("meanAbsDiffPct", Math.round(mean * 100) / 100.0);
        root.put("p50AbsDiffPct", Math.round(quantile(diffs, 0.5) * 100) / 100.0);
        root.put("p90AbsDiffPct", Math.round(quantile(diffs, 0.9) * 100) / 100.0);
        return root;
    }

    private double quantile(List<Double> sorted, double q) {
        if (sorted.isEmpty()) {
            return 0;
        }
        int idx = (int) Math.min(sorted.size() - 1, Math.max(0, Math.round(q * (sorted.size() - 1))));
        return sorted.get(idx);
    }
}
