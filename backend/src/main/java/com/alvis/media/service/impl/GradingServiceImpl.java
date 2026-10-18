package com.alvis.media.service.impl;

import com.alvis.media.service.GradingService;
import com.alvis.media.utility.PythonCliRunner;
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

    private final PythonCliRunner runner;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper om = new ObjectMapper();

    @Value("${system.python.gradingScript:}")
    private String gradingScript;

    public GradingServiceImpl(PythonCliRunner runner, StringRedisTemplate redisTemplate) {
        this.runner = runner;
        this.redisTemplate = redisTemplate;
    }

    @Override
    public JsonNode grade(int k) {
        if (k != 3 && k != 4 && k != 5) {
            k = 3;
        }
        String cacheKey = "grading:k" + k;
        try {
            String s = redisTemplate.opsForValue().get(cacheKey);
            if (s != null) {
                return om.readTree(s);
            }
        } catch (Exception ignore) {
        }
        String out = runner.run(gradingScript, Arrays.asList("--k", String.valueOf(k)));
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
