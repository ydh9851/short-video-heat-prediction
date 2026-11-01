package com.alvis.media.service;

import com.alvis.media.configuration.spring.task.EvaluationTaskConfig;
import com.alvis.media.utility.TraceContext;
import com.alvis.media.viewmodel.evaluation.EvaluationRequestVM;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.RejectedExecutionException;

/**
 * 实验任务调度服务：把分钟级实验从 HTTP 请求线程搬到独立线程池，任务状态存 Redis。
 *
 * <p>任务状态机：{@code QUEUED -> RUNNING -> DONE | FAILED}。
 * 状态存放在 Redis Hash（{@code eval:task:<taskId>}，24 小时过期），
 * 任务 id 追加进 {@code eval:recent} 列表（保留最近 30 条），因此不依赖数据库新增表，
 * 部署时无需额外执行 SQL 迁移。
 */
@Service
public class EvaluationTaskService {

    private static final Logger log = LoggerFactory.getLogger(EvaluationTaskService.class);

    private static final String KEY_PREFIX = "eval:task:";
    private static final String RECENT_KEY = "eval:recent";
    private static final int KEEP_RECENT = 30;
    private static final Duration TTL = Duration.ofHours(24);
    private static final DateTimeFormatter TIME_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final EvaluationService evaluationService;
    private final StringRedisTemplate redisTemplate;
    private final ThreadPoolTaskExecutor executor;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public EvaluationTaskService(EvaluationService evaluationService,
                                 StringRedisTemplate redisTemplate,
                                 @Qualifier(EvaluationTaskConfig.EXECUTOR_NAME) ThreadPoolTaskExecutor executor) {
        this.evaluationService = evaluationService;
        this.redisTemplate = redisTemplate;
        this.executor = executor;
    }

    /**
     * 提交实验，立即返回 taskId（不等待实验跑完）。
     */
    public String submit(EvaluationRequestVM req) {
        if (req == null || req.getMode() == null || req.getMode().trim().isEmpty()) {
            throw new IllegalArgumentException("缺少实验模式 mode");
        }
        String taskId = TraceContext.generate();
        Map<String, String> state = new LinkedHashMap<>();
        state.put("taskId", taskId);
        state.put("mode", req.getMode());
        state.put("status", "QUEUED");
        state.put("submittedAt", LocalDateTime.now().format(TIME_FORMAT));
        writeState(taskId, state);
        rememberRecent(taskId);

        String traceId = TraceContext.current();
        try {
            executor.execute(() -> runTask(taskId, req, traceId));
        } catch (RejectedExecutionException e) {
            update(taskId, "status", "FAILED", "error", "实验队列已满，请稍后重试");
            throw new IllegalStateException("实验队列已满，请稍后重试");
        }
        return taskId;
    }

    /** 查询单个任务状态；不存在返回 null。 */
    public Map<String, Object> get(String taskId) {
        if (taskId == null || taskId.trim().isEmpty()) {
            return null;
        }
        Map<Object, Object> raw = redisTemplate.opsForHash().entries(KEY_PREFIX + taskId.trim());
        if (raw == null || raw.isEmpty()) {
            return null;
        }
        return toView(raw);
    }

    /** 最近提交的任务列表（新的在前），用于前端展示实验历史。 */
    public List<Map<String, Object>> recent() {
        List<String> ids = redisTemplate.opsForList().range(RECENT_KEY, 0, KEEP_RECENT - 1);
        if (ids == null || ids.isEmpty()) {
            return Collections.emptyList();
        }
        List<Map<String, Object>> list = new ArrayList<>(ids.size());
        for (String id : ids) {
            Map<String, Object> view = get(id);
            if (view == null) {
                continue;
            }
            // 列表只需要摘要，去掉体积最大的 result 字段
            view.remove("result");
            list.add(view);
        }
        return list;
    }

    private void runTask(String taskId, EvaluationRequestVM req, String traceId) {
        if (traceId != null) {
            TraceContext.bind(traceId);
        }
        long start = System.currentTimeMillis();
        try {
            update(taskId, "status", "RUNNING", "startedAt", LocalDateTime.now().format(TIME_FORMAT));
            JsonNode result = evaluationService.run(req);
            long cost = System.currentTimeMillis() - start;
            Map<String, String> state = new LinkedHashMap<>();
            state.put("status", "DONE");
            state.put("finishedAt", LocalDateTime.now().format(TIME_FORMAT));
            state.put("elapsedMs", String.valueOf(cost));
            state.put("result", objectMapper.writeValueAsString(result));
            writeState(taskId, state);
            log.info("实验任务完成 taskId={} mode={} 耗时={}ms", taskId, req.getMode(), cost);
        } catch (Exception e) {
            log.error("实验任务失败 taskId={} mode={}", taskId, req.getMode(), e);
            Map<String, String> state = new LinkedHashMap<>();
            state.put("status", "FAILED");
            state.put("finishedAt", LocalDateTime.now().format(TIME_FORMAT));
            state.put("elapsedMs", String.valueOf(System.currentTimeMillis() - start));
            state.put("error", e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage());
            writeState(taskId, state);
        } finally {
            TraceContext.clear();
        }
    }

    private void writeState(String taskId, Map<String, String> fields) {
        String key = KEY_PREFIX + taskId;
        redisTemplate.opsForHash().putAll(key, fields);
        redisTemplate.expire(key, TTL);
    }

    private void update(String taskId, String... fieldValues) {
        Map<String, String> fields = new LinkedHashMap<>();
        for (int i = 0; i + 1 < fieldValues.length; i += 2) {
            fields.put(fieldValues[i], fieldValues[i + 1]);
        }
        writeState(taskId, fields);
    }

    private void rememberRecent(String taskId) {
        redisTemplate.opsForList().leftPush(RECENT_KEY, taskId);
        redisTemplate.opsForList().trim(RECENT_KEY, 0, KEEP_RECENT - 1);
    }

    private Map<String, Object> toView(Map<Object, Object> raw) {
        Map<String, Object> view = new LinkedHashMap<>();
        raw.forEach((k, v) -> view.put(String.valueOf(k), v));
        Object resultJson = view.get("result");
        if (resultJson instanceof String) {
            try {
                view.put("result", objectMapper.readTree((String) resultJson));
            } catch (Exception e) {
                // 结果不是合法 JSON 时保留原始字符串，避免影响状态查询
                log.warn("实验任务结果解析失败: {}", e.getMessage());
            }
        }
        return view;
    }
}
