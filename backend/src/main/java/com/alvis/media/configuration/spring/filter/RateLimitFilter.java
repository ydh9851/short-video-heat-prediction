package com.alvis.media.configuration.spring.filter;

import com.alvis.media.utility.TraceContext;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 轻量令牌桶限流（按客户端 IP），只保护「会拉起 Python 进程 / 触发重计算」的昂贵接口。
 *
 * <p>为什么不用 Bucket4j / Redis 限流：单机毕设场景下多一个依赖并不增加实际防御力，
 * 这里用一个无依赖的令牌桶就够，并且桶状态随进程重启清空，符合"演示可复现"的预期。
 * 集群部署时应换成 Redis + 滑动窗口。
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10)
public class RateLimitFilter extends OncePerRequestFilter {

    /** 需要限流的路径前缀（前缀匹配） */
    private static final Set<String> PROTECTED = Set.of(
            "/api/predict", "/api/attribution/explain", "/api/attribution/report", "/api/evaluation/submit");

    @Value("${system.api.rateLimit.enabled:true}")
    private boolean enabled;

    /** 每个 IP 每秒允许的请求数 */
    @Value("${system.api.rateLimit.qps:10}")
    private int qps;

    /** 桶容量（允许的突发量） */
    @Value("${system.api.rateLimit.burst:20}")
    private int burst;

    private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        if (!enabled) {
            return true;
        }
        String uri = request.getRequestURI();
        return PROTECTED.stream().noneMatch(uri::startsWith);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String client = clientKey(request);
        if (!buckets.computeIfAbsent(client, k -> new Bucket(burst)).tryAcquire(qps, burst)) {
            response.setStatus(429);
            response.setCharacterEncoding(StandardCharsets.UTF_8.name());
            response.setContentType("application/json;charset=UTF-8");
            String traceId = TraceContext.current();
            response.getWriter().write("{\"code\":429,\"message\":\"请求过于频繁，请稍后重试\",\"response\":null"
                    + (traceId == null ? "" : ",\"traceId\":\"" + traceId + "\"") + "}");
            return;
        }
        chain.doFilter(request, response);
    }

    private String clientKey(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (forwarded != null && !forwarded.trim().isEmpty()) {
            return forwarded.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    /** 简单令牌桶：按时间补充令牌，容量有上限。 */
    private static final class Bucket {
        private double tokens;
        private long lastRefillNanos;

        Bucket(int capacity) {
            this.tokens = capacity;
            this.lastRefillNanos = System.nanoTime();
        }

        synchronized boolean tryAcquire(int ratePerSecond, int capacity) {
            long now = System.nanoTime();
            double elapsedSec = (now - lastRefillNanos) / 1_000_000_000.0;
            tokens = Math.min(capacity, tokens + elapsedSec * ratePerSecond);
            lastRefillNanos = now;
            if (tokens >= 1.0) {
                tokens -= 1.0;
                return true;
            }
            return false;
        }
    }
}
