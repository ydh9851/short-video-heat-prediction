package com.alvis.media.service.impl;

import com.alvis.media.service.EvaluationService;
import com.alvis.media.utility.PythonCliRunner;
import com.alvis.media.viewmodel.evaluation.EvaluationRequestVM;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * 模型评估与实验分析实现：
 *   mode=cv/tuning/learning-curve/importance/residual/ablation -> model_evaluation.py
 *   mode=quantile/quantile-coverage                            -> prediction/quantile_predict.py
 *   mode=interaction/counterfactual                            -> attribution/shap_analysis.py
 * 全部复用 PythonCliRunner 的「ProcessBuilder + 单行 JSON」契约。
 */
@Service
@RequiredArgsConstructor
public class EvaluationServiceImpl implements EvaluationService {

    @Value("${system.python.evaluationScript:}")
    private String evaluationScript;
    @Value("${system.python.quantileScript:}")
    private String quantileScript;
    @Value("${system.python.attributionScript:}")
    private String attributionScript;
    @Value("${system.python.growthScript:}")
    private String growthScript;

    private final PythonCliRunner runner;
    private final ObjectMapper om = new ObjectMapper();

    private static final Set<String> EVAL_MODES = new HashSet<>(Arrays.asList(
            "cv", "tuning", "learning-curve", "importance", "residual", "ablation", "drift"));
    private static final Set<String> ATTR_MODES = new HashSet<>(Arrays.asList(
            "interaction", "counterfactual", "cross-platform"));
    private static final Set<String> QUANTILE_MODES = new HashSet<>(Arrays.asList(
            "quantile", "quantile-coverage"));
    private static final Set<String> GROWTH_MODES = new HashSet<>(Arrays.asList("growth"));

    /** 实验类模式耗时较长（交叉验证 / 随机搜索），给 15 分钟超时 */
    private static final int EVAL_TIMEOUT_SECONDS = 900;

    @Override
    public JsonNode run(EvaluationRequestVM req) {
        String mode = (req == null || req.getMode() == null || req.getMode().trim().isEmpty())
                ? "cv" : req.getMode().trim();
        List<String> args = new ArrayList<>();
        String script;

        if (EVAL_MODES.contains(mode)) {
            script = require(evaluationScript, "system.python.evaluationScript");
            args.add("--mode");
            args.add(mode);
            if (req.getPlatform() != null && !req.getPlatform().trim().isEmpty()) {
                args.add("--platform");
                args.add(req.getPlatform().trim());
            }
            if ("cv".equals(mode)) {
                args.add("--folds");
                args.add(String.valueOf(nvl(req.getFolds(), 5)));
            } else if ("tuning".equals(mode)) {
                args.add("--trials");
                args.add(String.valueOf(nvl(req.getTrials(), 12)));
            } else if ("importance".equals(mode)) {
                args.add("--sample");
                args.add(String.valueOf(nvl(req.getSample(), 2000)));
            }
        } else if (QUANTILE_MODES.contains(mode)) {
            script = require(quantileScript, "system.python.quantileScript");
            if ("quantile-coverage".equals(mode)) {
                args.add("--coverage");
            } else {
                addSingleSampleArgs(args, req);
            }
        } else if (ATTR_MODES.contains(mode)) {
            script = require(attributionScript, "system.python.attributionScript");
            args.add("--mode");
            args.add(mode);
            if ("counterfactual".equals(mode)) {
                addSingleSampleArgs(args, req);
            } else if ("cross-platform".equals(mode)) {
                args.add("--sample");
                args.add(String.valueOf(nvl(req.getSample(), 1500)));
            }
        } else if (GROWTH_MODES.contains(mode)) {
            script = require(growthScript, "system.python.growthScript");
            args.add("--sample");
            args.add(String.valueOf(nvl(req.getSample(), 20000)));
        } else {
            throw new IllegalArgumentException("不支持的实验模式: " + mode);
        }

        String out = runner.run(script, args, EVAL_TIMEOUT_SECONDS);
        try {
            JsonNode node = om.readTree(PythonCliRunner.lastJsonLine(out));
            if (node.hasNonNull("error")) {
                throw new RuntimeException(node.path("error").asText());
            }
            return node;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("解析实验结果失败: " + e.getMessage(), e);
        }
    }

    @Override
    public JsonNode modes() {
        ArrayNode arr = om.createArrayNode();
        arr.add(desc("cv", "K 折交叉验证", "模型可靠性论证",
                "把数据划分为 K 份轮流验证，输出各折 RMSE/MAE/R² 的均值与标准差，证明结果稳定、非偶然。",
                "cv_scores.png", "evm", 900));
        arr.add(desc("tuning", "超参数随机搜索", "模型调优",
                "在 LightGBM 关键超参空间中随机采样多组配置并用交叉验证评估，给出最优参数与调参收益。",
                "tuning_result.png", "evm", 1200));
        arr.add(desc("learning-curve", "学习曲线", "数据量分析",
                "按 10%~100% 递增训练集规模，观察训练/验证误差变化，判断数据量是否饱和、是否存在过拟合。",
                "learning_curve.png", "evm", 900));
        arr.add(desc("importance", "特征重要性三方对照", "特征工程论证",
                "把「增益重要性 / 置换重要性 / SHAP 平均贡献」三种度量放在一起比较，交叉验证特征结论的一致性。",
                "importance_compare.png", "evm", 600));
        arr.add(desc("residual", "残差与分位数误差", "误差结构分析",
                "按热度等级拆解误差分布，并给出 P50/P90/P99 分位数误差，说明「均值误差不能代表业务可用性」。",
                "residual_analysis.png", "evm", 600));
        arr.add(desc("ablation", "特征消融实验", "特征有效性验证",
                "对比基础特征集与增强特征集（周期编码 + 作者分层）在 LightGBM 与线性模型上的表现差异。",
                "ablation.png", "evm", 900));
        arr.add(desc("drift", "跨平台分布漂移看板", "数据一致性检验",
                "以抖音为基准，用 PSI（群体稳定性指数）与 KS 检验量化各平台特征分布的偏移程度，"
                        + "回答「在一平台训练的模型迁移到另一平台是否可靠」。",
                "platform_drift.png", "evm", 600));
        arr.add(desc("growth", "热度增长曲线预测", "时序热度预测",
                "基于 TikTok 真实「每日累计」快照（第 0~30 天），用发布后 0~1 天的早期热度"
                        + "预测第 1 / 3 / 7 天的累计热度，量化冷启动期判断是否值得继续投放。",
                "growth_forecast.png", "evm", 900));
        arr.add(desc("quantile", "预测区间（分位数回归）", "业务风险量化",
                "用 LightGBM quantile 目标训练 P10/P50/P90 三个模型，给出「保守 / 中性 / 乐观」热度区间与区间覆盖率。",
                null, "evm", 600));
        arr.add(desc("interaction", "SHAP 交互效应", "组合效应分析",
                "量化两个特征共同作用带来的额外贡献，回答「除粉丝数外是否存在组合效应」。",
                "shap_interaction.png", "evm", 900));
        arr.add(desc("counterfactual", "反事实分析", "运营决策支持",
                "固定其他条件，把某个可调整维度（时段/星期/月份/类别）改到最优取值，量化热度提升幅度。",
                "counterfactual.png", "attr", 600));
        arr.add(desc("cross-platform", "跨平台特征贡献对照", "跨平台泛化分析",
                "对抖音 / YouTube / TikTok / 哔哩哔哩 4 个平台分别训练 LightGBM 并计算 SHAP 贡献占比，"
                        + "对照同一特征在不同平台的相对重要性，揭示「跨平台可迁移」与「平台特有」的影响因素。",
                "cross_platform_shap.png", "attr", 1200));
        return arr;
    }

    private ObjectNode desc(String key, String name, String tag, String desc, String figure,
                            String group, int timeoutSeconds) {
        ObjectNode n = om.createObjectNode();
        n.put("mode", key);
        n.put("name", name);
        n.put("tag", tag);
        n.put("description", desc);
        n.put("figure", figure);
        n.put("group", group);
        n.put("timeoutSeconds", timeoutSeconds);
        return n;
    }

    /** 单样本类模式共用的输入特征参数（中文类别做 URL 编码，规避 JDK 中文 argv 问题） */
    private void addSingleSampleArgs(List<String> args, EvaluationRequestVM req) {
        String category = (req.getCategory() == null || req.getCategory().trim().isEmpty())
                ? "美食" : req.getCategory().trim();
        args.add("--category");
        args.add(URLEncoder.encode(category, StandardCharsets.UTF_8));
        args.add("--fans");
        args.add(String.valueOf(req.getFans() == null ? 0.0 : req.getFans()));
        args.add("--hour");
        args.add(String.valueOf(nvl(req.getHour(), 20)));
        args.add("--weekday");
        args.add(String.valueOf(nvl(req.getWeekday(), 5)));
        args.add("--month");
        args.add(String.valueOf(nvl(req.getMonth(), 6)));
    }

    private static int nvl(Integer v, int def) {
        return v == null ? def : v;
    }

    private static String require(String path, String key) {
        if (path == null || path.trim().isEmpty()) {
            throw new IllegalStateException("未配置 Python 脚本路径（" + key + "）");
        }
        return path.trim();
    }
}
