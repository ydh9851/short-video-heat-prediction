package com.alvis.media.service.impl;

import com.alvis.media.service.GradingService;
import com.alvis.media.service.ModelRegistryService;
import com.alvis.media.utility.PythonCliRunner;
import com.alvis.media.utility.PythonGateway;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.concurrent.TimeUnit;

/**
 * 热度分级服务：调用 algorithm/grading/grade_cluster.py
 */
@Service
public class GradingServiceImpl implements GradingService {

    private final PythonGateway gateway;
    private final StringRedisTemplate redisTemplate;
    private final ModelRegistryService registry;
    private final ObjectMapper om = new ObjectMapper();

    @Value("${system.python.gradingScript:}")
    private String gradingScript;

    public GradingServiceImpl(PythonGateway gateway, StringRedisTemplate redisTemplate,
                              ModelRegistryService registry) {
        this.gateway = gateway;
        this.redisTemplate = redisTemplate;
        this.registry = registry;
    }

    @Override
    public JsonNode grade(int k) {
        if (k != 3 && k != 4 && k != 5) {
            k = 3;
        }
        // 缓存 key 携带线上模型版本：重训/promote 后旧阈值缓存自动失效
        String version = registry.activeVersion("lgbm");
        String cacheKey = "grading:" + (version == null ? "none" : version) + ":k" + k;
        try {
            String s = redisTemplate.opsForValue().get(cacheKey);
            if (s != null) {
                return om.readTree(s);
            }
        } catch (Exception ignore) {
        }
        String out = gateway.runCli(gradingScript, Arrays.asList("--k", String.valueOf(k)));
        try {
            JsonNode node = om.readTree(PythonCliRunner.lastJsonLine(out));
            if (node.hasNonNull("error")) {
                throw new RuntimeException(node.path("error").asText());
            }
            redisTemplate.opsForValue().set(cacheKey, om.writeValueAsString(node), 12, TimeUnit.HOURS);
            return node;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("解析热度分级结果失败: " + e.getMessage(), e);
        }
    }
}
