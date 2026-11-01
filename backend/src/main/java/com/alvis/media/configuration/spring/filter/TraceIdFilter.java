package com.alvis.media.configuration.spring.filter;

import com.alvis.media.utility.TraceContext;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * 请求级链路追踪过滤器（最高优先级，先于 Spring Security 执行）。
 *
 * <p>优先复用请求头 {@code X-Trace-Id}（便于跨系统串联），没有则生成新的；
 * 处理完成后回写同名响应头，并把 traceId 放进 MDC，供 logback 的 {@code %X{traceId}} 与
 * Python 子进程环境变量使用。
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class TraceIdFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(TraceIdFilter.class);

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String traceId = TraceContext.sanitize(request.getHeader(TraceContext.HEADER));
        if (traceId == null) {
            traceId = TraceContext.generate();
        }
        TraceContext.bind(traceId);
        response.setHeader(TraceContext.HEADER, traceId);

        long start = System.currentTimeMillis();
        try {
            chain.doFilter(request, response);
        } finally {
            log.info("{} {} -> {} ({}ms)", request.getMethod(), request.getRequestURI(),
                    response.getStatus(), System.currentTimeMillis() - start);
            TraceContext.clear();
        }
    }

    /** 静态资源不参与追踪，避免日志被 JS/CSS 请求淹没。 */
    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String uri = request.getRequestURI();
        return uri.startsWith("/admin/static") || uri.startsWith("/static")
                || uri.endsWith("favicon.ico") || uri.endsWith("favicon.svg");
    }
}
