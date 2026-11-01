package com.alvis.media.utility;

import org.slf4j.MDC;

import java.util.UUID;

/**
 * 链路追踪上下文：统一 traceId 的生成、MDC 存取与外部传入校验。
 *
 * <p>一次请求的 traceId 会出现在三个位置，形成端到端可检索的链路：
 * <ol>
 *   <li>响应头 {@code X-Trace-Id}（前端 / 调用方可直接回传复现）；</li>
 *   <li>logback 日志 {@code %X{traceId}}（Java 侧每行日志）；</li>
 *   <li>Python 子进程环境变量 {@code TRACE_ID}（算法侧异常输出会带上它）。</li>
 * </ol>
 */
public final class TraceContext {

    public static final String HEADER = "X-Trace-Id";

    public static final String MDC_KEY = "traceId";

    private TraceContext() {
    }

    /** 生成 16 位 traceId。 */
    public static String generate() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    /**
     * 校验外部传入的 traceId，只接受由字母、数字、下划线、短横线组成且长度不超过 64 的值，
     * 非法内容一律丢弃并改用新生成的 id，避免日志被注入超长或换行内容。
     */
    public static String sanitize(String raw) {
        if (raw == null) {
            return null;
        }
        String value = raw.trim();
        if (value.isEmpty() || value.length() > 64) {
            return null;
        }
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            boolean allowed = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'z')
                    || (c >= 'A' && c <= 'Z') || c == '-' || c == '_';
            if (!allowed) {
                return null;
            }
        }
        return value;
    }

    /** 绑定 traceId 到当前线程的 MDC。 */
    public static void bind(String traceId) {
        MDC.put(MDC_KEY, traceId);
    }

    /** 当前线程的 traceId，未绑定时返回 null。 */
    public static String current() {
        return MDC.get(MDC_KEY);
    }

    /** 解除当前线程绑定。 */
    public static void clear() {
        MDC.remove(MDC_KEY);
    }
}
