package com.alvis.media.service.impl;

import com.alvis.media.service.AttributionService;
import com.alvis.media.utility.PythonCliRunner;
import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * 归因分析服务：调用 algorithm/attribution/shap_analysis.py
 * （全局重要性 / 单样本 SHAP 瀑布图 / 部分依赖图；结果含图名与 JSON 摘要）
 */
@Service
public class AttributionServiceImpl implements AttributionService {

    private final PythonCliRunner runner;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper om = new ObjectMapper();

    @Value("${system.python.attributionScript:}")
    private String attributionScript;

    public AttributionServiceImpl(PythonCliRunner runner, StringRedisTemplate redisTemplate) {
        this.runner = runner;
        this.redisTemplate = redisTemplate;
    }

    @Override
    public JsonNode global() {
        String cacheKey = "attribution:global";
        JsonNode cached = readCache(cacheKey);
        if (cached != null) {
            return cached;
        }
        JsonNode node = exec(Arrays.asList("--mode", "global"));
        writeCache(cacheKey, node, 12);
        return node;
    }

    @Override
    public JsonNode explain(PredictRequestVM req) {
        if (req.getVideoCategory() == null || req.getVideoCategory().trim().isEmpty()) {
            req.setVideoCategory("美食");
        }
        if (req.getAuthorFans() == null || req.getAuthorFans() < 0) {
            req.setAuthorFans(0.0);
        }
        if (req.getPublishHour() == null) req.setPublishHour(20);
        if (req.getPublishWeekday() == null) req.setPublishWeekday(5);
        if (req.getPublishMonth() == null) req.setPublishMonth(6);

        String cacheKey = "attribution:explain:" + req.getVideoCategory() + ":" + req.getAuthorFans()
                + ":" + req.getPublishHour() + ":" + req.getPublishWeekday() + ":" + req.getPublishMonth();
        JsonNode cached = readCache(cacheKey);
        if (cached != null) {
            return cached;
        }
        List<String> args = new ArrayList<>();
        args.addAll(Arrays.asList("--mode", "explain"));
        args.addAll(Arrays.asList("--category",
                URLEncoder.encode(req.getVideoCategory().trim(), StandardCharsets.UTF_8)));
        args.addAll(Arrays.asList("--fans", String.valueOf(req.getAuthorFans())));
        args.addAll(Arrays.asList("--hour", String.valueOf(req.getPublishHour())));
        args.addAll(Arrays.asList("--weekday", String.valueOf(req.getPublishWeekday())));
        args.addAll(Arrays.asList("--month", String.valueOf(req.getPublishMonth())));
        JsonNode node = exec(args);
        writeCache(cacheKey, node, 1);
        return node;
    }

    @Override
    public JsonNode pdp(String feature) {
        if (feature == null || feature.trim().isEmpty()) {
            feature = "author_fans_log";
        }
        String cacheKey = "attribution:pdp:" + feature;
        JsonNode cached = readCache(cacheKey);
        if (cached != null) {
            return cached;
        }
        JsonNode node = exec(Arrays.asList("--mode", "pdp", "--feature", feature.trim()));
        writeCache(cacheKey, node, 12);
        return node;
    }

    private JsonNode exec(List<String> args) {
        String out = runner.run(attributionScript, args);
        try {
            JsonNode node = om.readTree(PythonCliRunner.lastJsonLine(out));
            if (node.hasNonNull("error")) {
                throw new RuntimeException(node.path("error").asText());
            }
            return node;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("解析归因分析结果失败: " + e.getMessage(), e);
        }
    }

    private JsonNode readCache(String key) {
        try {
            String s = redisTemplate.opsForValue().get(key);
            if (s != null) {
                return om.readTree(s);
            }
        } catch (Exception ignore) {
        }
        return null;
    }

    private void writeCache(String key, JsonNode node, long hours) {
        try {
            redisTemplate.opsForValue().set(key, om.writeValueAsString(node), hours, TimeUnit.HOURS);
        } catch (Exception ignore) {
        }
    }
}
