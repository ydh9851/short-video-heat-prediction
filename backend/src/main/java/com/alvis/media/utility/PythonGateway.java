package com.alvis.media.utility;

import com.alvis.media.viewmodel.predict.BatchPredictRequestVM;
import com.alvis.media.viewmodel.predict.PredictRequestVM;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.File;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Python 算法引擎统一调用门面（HTTP 常驻服务优先 / CLI 降级 / 熔断 / 信号量 / TraceId 收口）。
 *
 * <p>设计目标：
 * <ul>
 *   <li>所有业务模块不再直接持有 {@link PythonCliRunner} 或 {@link PythonEngineClient}，
 *       统一走 {@code PythonGateway}，便于将来替换实现、加埋点、限流；</li>
 *   <li>预测请求优先走常驻 HTTP 服务（几十毫秒），失败 / 熔断时自动回落到 CLI（秒级），
 *       业务侧无需关心双轨细节；</li>
 *   <li>CLI 调用统一复用 {@link PythonCliRunner}（全局信号量 + 超时 + traceId 透传），
 *       避免各模块自行 ProcessBuilder 导致无超时 / 无并发控制。</li>
 * </ul>
 */
@Component
public class PythonGateway {

    private static final Logger log = LoggerFactory.getLogger(PythonGateway.class);

    private static final List<String> MODELS =
            Arrays.asList("lgbm", "xgb", "rf", "lr", "knn", "svm", "dt");

    @Value("${system.python.script:}")
    private String scriptPath;

    @Value("${system.python.predictScript:}")
    private String predictScript;

    private final PythonEngineClient engine;
    private final PythonCliRunner runner;
    private final ObjectMapper om = new ObjectMapper();

    public PythonGateway(PythonEngineClient engine, PythonCliRunner runner) {
        this.engine = engine;
        this.runner = runner;
    }

    // ------------------------------------------------------------------ 预测（HTTP 优先 / CLI 降级）

    /**
     * 单条热度预测：优先调用常驻推理服务，不可用时自动降级到 CLI。
     *
     * @param req     预测请求
     * @param version 线上模型版本（null 表示不锁定版本，由 Python 侧自行决定）
     * @return Python 侧输出的原始 JSON（字段：model / model_version / prediction / ...）
     */
    public JsonNode predict(PredictRequestVM req, String version) {
        validate(req);
        // 1) 常驻服务：HTTP 一次往返几十毫秒
        if (engine.available()) {
            try {
                Map<String, Object> body = new LinkedHashMap<>();
                body.put("model", req.getModel());
                body.put("category", req.getVideoCategory());
                body.put("fans", req.getAuthorFans());
                body.put("hour", req.getPublishHour());
                body.put("weekday", req.getPublishWeekday());
                body.put("month", req.getPublishMonth());
                return engine.post("/predict", body);
            } catch (Exception e) {
                log.warn("预测请求降级到 CLI 通道：{}", e.getMessage());
            }
        }
        // 2) CLI 降级：带超时与 traceId 透传，避免请求线程被 Python 进程永久挂住
        String out = runner.run(resolvePredictScript(), buildCliArgs(req, version), 600);
        try {
            return om.readTree(PythonCliRunner.lastJsonLine(out));
        } catch (Exception e) {
            throw new RuntimeException("解析热度预测结果失败: " + e.getMessage(), e);
        }
    }

    /**
     * 批量热度预测：一次提交多条视频先验特征。
     * 当前仅走 CLI（常驻服务暂无批量端点），输入写临时文件传参。
     */
    public JsonNode predictBatch(BatchPredictRequestVM req) {
        String model = req.getModel();
        if (model == null || model.isEmpty()) {
            model = "lgbm";
        }
        if (!MODELS.contains(model)) {
            throw new IllegalArgumentException("model 取值仅支持 lgbm / xgb / rf / lr / knn / svm / dt");
        }
        List<PredictRequestVM> items = req.getItems();
        if (items == null || items.isEmpty()) {
            throw new IllegalArgumentException("批量预测至少需要一条数据");
        }
        if (items.size() > 500) {
            throw new IllegalArgumentException("单次批量预测最多 500 条");
        }

        List<Map<String, Object>> payload = new ArrayList<>();
        for (PredictRequestVM it : items) {
            Map<String, Object> m = new HashMap<>();
            String cat = (it.getVideoCategory() == null || it.getVideoCategory().trim().isEmpty())
                    ? "美食" : it.getVideoCategory().trim();
            m.put("category", cat);
            m.put("fans", it.getAuthorFans() == null ? 0.0 : it.getAuthorFans());
            m.put("hour", it.getPublishHour() == null ? 20 : it.getPublishHour());
            m.put("weekday", it.getPublishWeekday() == null ? 5 : it.getPublishWeekday());
            m.put("month", it.getPublishMonth() == null ? 6 : it.getPublishMonth());
            payload.add(m);
        }

        File tmp = null;
        try {
            tmp = File.createTempFile("heat_batch_", ".json");
            om.writeValue(tmp, payload);
            String out = runner.run(resolvePredictScript(),
                    Arrays.asList("--model", model, "--batch", tmp.getAbsolutePath()));
            JsonNode node = om.readTree(PythonCliRunner.lastJsonLine(out));
            if (node.hasNonNull("error")) {
                throw new RuntimeException(node.path("error").asText());
            }
            return node;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("批量预测失败: " + e.getMessage(), e);
        } finally {
            if (tmp != null && tmp.exists()) {
                tmp.delete();
            }
        }
    }

    // ------------------------------------------------------------------ 通用 CLI 透传

    /**
     * 执行任意 Python CLI 脚本（归因 / 评估 / 分级 / 数据导入 / 注册表 等复用）。
     * 统一走全局信号量 + 超时 + traceId 透传，避免业务模块自行 ProcessBuilder。
     *
     * @param script  脚本路径
     * @param args    参数列表（可为 null）
     * @param timeout 超时秒数
     * @return 脚本 stdout 原文
     */
    public String runCli(String script, List<String> args, int timeout) {
        return runner.run(script, args, timeout);
    }

    /** 默认超时（600s）的 CLI 调用 */
    public String runCli(String script, List<String> args) {
        return runner.run(script, args);
    }

    // ------------------------------------------------------------------ 常驻服务状态

    /** DISABLED / UP / DEGRADED */
    public String engineStatus() {
        return engine.status();
    }

    /** 常驻服务是否可用（已配置且不在熔断窗口内） */
    public boolean engineAvailable() {
        return engine.available();
    }

    public String engineBaseUrl() {
        return engine.baseUrl();
    }

    public String engineLastError() {
        return engine.lastError();
    }

    /**
     * 影子模式打分：仅走常驻 HTTP 服务，不降级 CLI（避免为影子打分拉起 Python 进程）。
     * 引擎不可用或调用失败时返回 null，由调用方自行忽略。
     */
    public JsonNode predictShadow(String model, PredictRequestVM req) {
        if (!engine.available()) {
            return null;
        }
        try {
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("model", model);
            body.put("category", req.getVideoCategory());
            body.put("fans", req.getAuthorFans());
            body.put("hour", req.getPublishHour());
            body.put("weekday", req.getPublishWeekday());
            body.put("month", req.getPublishMonth());
            return engine.post("/predict", body);
        } catch (Exception e) {
            log.debug("影子打分引擎调用失败：{}", e.getMessage());
            return null;
        }
    }

    // ------------------------------------------------------------------ 内部辅助

    private void validate(PredictRequestVM req) {
        if (req.getModel() == null || req.getModel().isEmpty()) {
            req.setModel("lgbm");
        }
        if (!MODELS.contains(req.getModel())) {
            throw new IllegalArgumentException("model 取值仅支持 lgbm / xgb / rf / lr / knn / svm / dt");
        }
        if (req.getVideoCategory() == null || req.getVideoCategory().trim().isEmpty()) {
            req.setVideoCategory("美食");
        }
        if (req.getAuthorFans() == null || req.getAuthorFans() < 0) {
            req.setAuthorFans(0.0);
        }
        if (req.getPublishHour() == null || req.getPublishHour() < 0 || req.getPublishHour() > 23) {
            throw new IllegalArgumentException("请填写有效的发布小时（0-23）");
        }
        if (req.getPublishWeekday() == null || req.getPublishWeekday() < 0 || req.getPublishWeekday() > 6) {
            throw new IllegalArgumentException("请填写有效的发布星期（0-6，0=周一）");
        }
        if (req.getPublishMonth() == null || req.getPublishMonth() < 1 || req.getPublishMonth() > 12) {
            throw new IllegalArgumentException("请填写有效的发布月份（1-12）");
        }
    }

    /** 解析热度预测脚本路径：优先 predictScript，否则从 script 同目录推 predict_api.py。metrics 等复用此脚本的模块需要。 */
    public String resolvePredictScript() {
        if (predictScript != null && !predictScript.trim().isEmpty()) {
            return predictScript.trim();
        }
        if (scriptPath != null && !scriptPath.trim().isEmpty()) {
            File parent = new File(scriptPath.trim()).getParentFile();
            if (parent != null) {
                return new File(parent, "predict_api.py").getAbsolutePath();
            }
        }
        throw new IllegalStateException("未配置 Python 热度预测脚本路径（system.python.predictScript）");
    }

    /**
     * 组装 CLI 预测参数：显式绑定线上版本，保证 CLI 与缓存 key 使用同一模型。
     * 中文类别参数 URL 编码为纯 ASCII，规避 JDK/中文 Windows 下 ProcessBuilder argv 编码问题。
     */
    private List<String> buildCliArgs(PredictRequestVM req, String version) {
        List<String> args = new ArrayList<>();
        args.add("--model");
        args.add(req.getModel());
        args.add("--category");
        args.add(URLEncoder.encode(req.getVideoCategory().trim(), StandardCharsets.UTF_8));
        args.add("--fans");
        args.add(String.valueOf(req.getAuthorFans()));
        args.add("--hour");
        args.add(String.valueOf(req.getPublishHour()));
        args.add("--weekday");
        args.add(String.valueOf(req.getPublishWeekday()));
        args.add("--month");
        args.add(String.valueOf(req.getPublishMonth()));
        if (version != null) {
            args.add("--version");
            args.add(version);
        }
        return args;
    }
}
