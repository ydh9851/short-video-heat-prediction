package com.alvis.media.configuration.property;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.List;


/**
 *@author 奇趣
 */
@ConfigurationProperties(prefix = "system")
@Data
public class SystemConfig {
    private PasswordKeyConfig pwdKey;
    private List<String> securityIgnoreUrls;
    /**
     * 允许跨域携带凭据的来源（逗号分隔或 YAML 列表）。
     * 生产环境通过 CORS_ALLOWED_ORIGINS 注入，禁止使用通配符。
     */
    private List<String> corsAllowedOrigins;
    private WxConfig wx;
    private QnConfig qn;
}
