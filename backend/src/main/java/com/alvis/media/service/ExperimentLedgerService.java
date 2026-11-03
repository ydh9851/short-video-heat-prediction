package com.alvis.media.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
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
import java.util.List;

/**
 * 轻量级实验台账（Experiment Ledger）。
 *
 * <p>参考 MLflow Tracking 的「一次实验 = 一条 run 记录」思路，但存储用追加式 JSONL
 * （{@code data/logs/experiment_runs.jsonl}），原因：
 * <ul>
 *   <li>不需要为毕设环境额外建表 / 跑迁移，克隆仓库即可用；</li>
 *   <li>只追加不修改，天然可回溯，也方便直接 grep / 用 pandas 二次分析；</li>
 *   <li>一条记录含参数、指标、耗时、traceId 与数据平台。</li>
 * </ul>
 * 需要并发安全的场景（多实例部署）应换成数据库，这里单机场景足够。
 */
@Service
public class ExperimentLedgerService {

    private static final Logger log = LoggerFactory.getLogger(ExperimentLedgerService.class);

    private static final String FILE_NAME = "experiment_runs.jsonl";
    private static final DateTimeFormatter TIME_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Value("${system.data.logDir:../data/logs}")
    private String logDir;

    private final ObjectMapper om = new ObjectMapper();

    /** 追加一条实验记录（synchronized 保证同一进程内写入不交错）。 */
    public synchronized void append(String runId, String mode, String platform, Object params,
                                    String status, long elapsedMs, String traceId, JsonNode result) {
        ObjectNode record = om.createObjectNode();
        record.put("runId", runId);
        record.put("mode", mode);
        record.put("platform", platform == null ? "douyin" : platform);
        record.put("status", status);
        record.put("elapsedMs", elapsedMs);
        record.put("traceId", traceId);
        record.put("finishedAt", LocalDateTime.now().format(TIME_FORMAT));
        record.set("params", params == null ? om.createObjectNode() : om.valueToTree(params));
        if (result != null) {
            record.set("result", result);
        }
        try {
            Path dir = Paths.get(logDir).toAbsolutePath().normalize();
            Files.createDirectories(dir);
            Path file = dir.resolve(FILE_NAME);
            Files.writeString(file, om.writeValueAsString(record) + System.lineSeparator(),
                    StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException e) {
            // 记账失败不能影响实验本身，只记录告警
            log.warn("写入实验台账失败: {}", e.getMessage());
        }
    }

    /** 最近 N 条实验记录（新的在前）。 */
    public List<JsonNode> recent(int limit) {
        int size = limit <= 0 ? 20 : Math.min(limit, 200);
        Path file = Paths.get(logDir).toAbsolutePath().normalize().resolve(FILE_NAME);
        if (!Files.isRegularFile(file)) {
            return Collections.emptyList();
        }
        try {
            List<String> lines = Files.readAllLines(file, StandardCharsets.UTF_8);
            List<JsonNode> out = new ArrayList<>();
            for (int i = lines.size() - 1; i >= 0 && out.size() < size; i--) {
                String line = lines.get(i).trim();
                if (line.isEmpty()) {
                    continue;
                }
                try {
                    out.add(om.readTree(line));
                } catch (Exception ignore) {
                    // 跳过损坏行，不影响其它历史记录
                }
            }
            return out;
        } catch (IOException e) {
            throw new RuntimeException("读取实验台账失败：" + e.getMessage(), e);
        }
    }

    /**
     * 取某个实验模式最近一次成功运行的结果（用于在业务页面直接引用实验结论）。
     * 没有则返回 null——调用方据此决定是否展示"尚未运行"的提示。
     */
    public JsonNode latestResult(String mode, int lookback) {
        if (mode == null || mode.trim().isEmpty()) {
            return null;
        }
        int limit = lookback <= 0 ? 200 : Math.min(lookback, 500);
        for (JsonNode record : recent(limit)) {
            if (!mode.equals(record.path("mode").asText())) {
                continue;
            }
            if (!"DONE".equals(record.path("status").asText())) {
                continue;
            }
            JsonNode result = record.path("result");
            if (result != null && !result.isMissingNode() && !result.isNull()) {
                return result;
            }
        }
        return null;
    }
}
