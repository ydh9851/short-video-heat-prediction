package com.alvis.media.controller;

import com.alvis.media.MediaApplication;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.greaterThan;
import static org.hamcrest.Matchers.is;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * 接口契约测试（MockMvc）
 *
 * <p>只覆盖「前端依赖、但最容易在重构中被悄悄改坏」的接口：
 * 统一响应体结构、实验模式清单、预测链路、数据集清单、任务查询与错误语义。
 * 不覆盖 SHAP 类重计算接口（单次数十秒，属于集成测试而非单元回归）。
 */
@SpringBootTest(classes = MediaApplication.class)
@AutoConfigureMockMvc
class ApiContractTest {

    @Autowired
    private MockMvc mvc;

    @Test
    @DisplayName("统一响应体：code/message/response 三字段")
    void responseEnvelopeIsStable() throws Exception {
        mvc.perform(get("/api/data/platforms"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code", is(1)))
                .andExpect(jsonPath("$.message").exists())
                .andExpect(jsonPath("$.response").exists());
    }

    @Test
    @DisplayName("实验模式清单包含新增的 4 个实验")
    void evaluationModesContainNewExperiments() throws Exception {
        mvc.perform(get("/api/evaluation/modes"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code", is(1)))
                .andExpect(jsonPath("$.response.length()", greaterThan(10)))
                .andExpect(jsonPath("$.response[?(@.mode=='conformal')]").isNotEmpty())
                .andExpect(jsonPath("$.response[?(@.mode=='explanation-quality')]").isNotEmpty())
                .andExpect(jsonPath("$.response[?(@.mode=='two-stage')]").isNotEmpty())
                .andExpect(jsonPath("$.response[?(@.mode=='refutation')]").isNotEmpty());
    }

    @Test
    @DisplayName("单条预测返回热度值与模型指标")
    void predictReturnsHeatAndMetrics() throws Exception {
        String body = "{\"model\":\"lgbm\",\"videoCategory\":\"美食\",\"authorFans\":50000,"
                + "\"publishHour\":20,\"publishWeekday\":5,\"publishMonth\":3}";
        mvc.perform(post("/api/predict").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code", is(1)))
                .andExpect(jsonPath("$.response.prediction", greaterThan(0.0)))
                .andExpect(jsonPath("$.response.metrics.r2", greaterThan(0.0)));
    }

    @Test
    @DisplayName("非法发布小时被拒绝（错误语义不能被吞掉）")
    void invalidPublishHourIsRejected() throws Exception {
        String body = "{\"model\":\"lgbm\",\"videoCategory\":\"美食\",\"authorFans\":1000,"
                + "\"publishHour\":99,\"publishWeekday\":5,\"publishMonth\":3}";
        mvc.perform(post("/api/predict").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(jsonPath("$.code", not(1)));
    }

    @Test
    @DisplayName("常驻推理服务状态可查询（DISABLED / UP / DEGRADED）")
    void engineStatusIsExposed() throws Exception {
        mvc.perform(get("/api/predict/engine"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code", is(1)))
                .andExpect(jsonPath("$.response.status").exists());
    }

    @Test
    @DisplayName("data/raw 文件清单可读")
    void rawFilesAreListed() throws Exception {
        mvc.perform(get("/api/data/raw-files"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code", is(1)))
                .andExpect(jsonPath("$.response.list").isArray());
    }

    @Test
    @DisplayName("实验台账可读，且缺失任务返回 404 而非 500")
    void ledgerAndMissingTask() throws Exception {
        mvc.perform(get("/api/evaluation/runs").param("limit", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code", is(1)))
                .andExpect(jsonPath("$.response").isArray());
        mvc.perform(get("/api/evaluation/task/not-exist-task-id"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code", is(404)));
    }
}
