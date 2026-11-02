package com.alvis.media.utility;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.concurrent.atomic.AtomicLong;

/**
 * Python 常驻推理服务（FastAPI sidecar）的调用客户端，带**熔断降级**。
 *
 * <p>双轨设计：
 * <ul>
 *   <li>常驻服务可用时：HTTP 调用，单次推理约几十毫秒（省掉解释器启动与 import 开销）；</li>
 *   <li>调用失败 / 未启动 / 熔断期内：抛异常由调用方**降级到原 CLI 通道**，功能不受影响。</li>
 * </ul>
 * 熔断窗口 30 秒：避免服务不可用时，每个请求都先等一次连接超时才回落。
 */
@Component
public class PythonEngineClient {

    private static final Logger log = LoggerFactory.getLogger(PythonEngineClient.class);

    /** 失败后多久内不再尝试 HTTP（毫秒） */
    private static final long DEGRADE_MILLIS = 30_000L;

    @Value("${system.python.serviceUrl:}")
    private String serviceUrl;

    @Value("${system.python.serviceTimeoutMs:5000}")
    private int readTimeoutMs;

    private final ObjectMapper om = new ObjectMapper();
    private final AtomicLong degradedUntil = new AtomicLong(0L);

    private volatile String lastError = "";
    private volatile RestTemplate restTemplate;

    /** 是否配置了常驻服务地址 */
    public boolean configured() {
        return serviceUrl != null && !serviceUrl.trim().isEmpty();
    }

    /** 当前是否可尝试 HTTP（已配置且不在熔断窗口内） */
    public boolean available() {
        return configured() && System.currentTimeMillis() >= degradedUntil.get();
    }

    /** 供前端/健康检查展示：DISABLED / UP / DEGRADED */
    public String status() {
        if (!configured()) {
            return "DISABLED";
        }
        return available() ? "UP" : "DEGRADED";
    }

    public String lastError() {
        return lastError;
    }

    public String baseUrl() {
        String url = serviceUrl == null ? "" : serviceUrl.trim();
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }

    /**
     * POST JSON 到常驻服务并返回解析后的 JSON；任何异常都会触发熔断并向上抛出。
     */
    public JsonNode post(String path, Object body) {
        if (!available()) {
            throw new IllegalStateException("常驻推理服务熔断中（" + status() + "）");
        }
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<String> entity = new HttpEntity<>(om.writeValueAsString(body), headers);
            ResponseEntity<String> resp = rest().postForEntity(baseUrl() + path, entity, String.class);
            degradedUntil.set(0L);
            return om.readTree(resp.getBody());
        } catch (Exception e) {
            lastError = e.getMessage();
            degradedUntil.set(System.currentTimeMillis() + DEGRADE_MILLIS);
            log.warn("常驻推理服务调用失败，{} 秒内自动降级为 CLI 通道：{}", DEGRADE_MILLIS / 1000, e.getMessage());
            throw new IllegalStateException("常驻推理服务不可用: " + e.getMessage(), e);
        }
    }

    private RestTemplate rest() {
        if (restTemplate == null) {
            synchronized (this) {
                if (restTemplate == null) {
                    SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
                    factory.setConnectTimeout(1000);
                    factory.setReadTimeout(readTimeoutMs);
                    restTemplate = new RestTemplate(factory);
                }
            }
        }
        return restTemplate;
    }
}
