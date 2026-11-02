package com.alvis.media.configuration.spring;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * OpenAPI（Swagger UI）文档配置。
 *
 * <p>访问地址：
 * <ul>
 *   <li>交互式文档：{@code http://localhost:8000/swagger-ui/index.html}</li>
 *   <li>OpenAPI JSON：{@code http://localhost:8000/v3/api-docs}</li>
 * </ul>
 *
 * <p>接口按业务分组（@Tag）：热度预测 / 热度分级 / 归因分析 / 模型评估与实验 /
 * 数据治理 / 模型治理 / 用户管理 / 消息管理 / 文件上传 / 错误处理。
 */
@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI heatPredictionOpenApi() {
        return new OpenAPI()
                .info(new Info()
                        .title("短视频热度预测与归因分析系统 API")
                        .version("1.0.0")
                        .description("毕业设计 Web 系统的后端接口文档。覆盖热度预测、热度分级、可解释归因、"
                                + "17 类可复现实验、数据治理与模型治理六组能力。"
                                + "所有响应统一为 { code, message, response } 三字段结构，"
                                + "响应头携带 X-Trace-Id 便于在后端日志中定位。")
                        .license(new License().name("Academic Project")))
                .addServersItem(new Server().url("/").description("当前服务"));
    }
}