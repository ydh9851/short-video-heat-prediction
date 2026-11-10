package com.alvis.media.service.impl;

import com.alvis.media.domain.RehearsalReport;
import com.alvis.media.exception.BusinessException;
import com.alvis.media.repository.RehearsalReportMapper;
import com.alvis.media.service.JobService;
import com.alvis.media.service.ModelRegistryService;
import com.alvis.media.service.RehearsalService;
import com.alvis.media.utility.PythonCliRunner;
import com.alvis.media.utility.PythonGateway;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.Date;
import java.util.List;
import java.util.Map;

/**
 * 上线预演实现：调用 rehearsal.py 让候选版本与当前线上版本在真实采样上并行打分，
 * 报告落 t_rehearsal_report 并缓存「该（模型, 版本）最新一份」到 Redis。
 *
 * <p>门禁语义：只有「通过」且**基于当前线上版本**的预演报告才允许直接 promote；
 * 否则返回 409（冲突），前端据此提示「先预演 / 重新预演 / 强制上线」。
 */
@Service
public class RehearsalServiceImpl implements RehearsalService {

    private static final Logger log = LoggerFactory.getLogger(RehearsalServiceImpl.class);

    private static final String LATEST_KEY_PREFIX = "rehearsal:";

    private final JobService jobService;
    private final RehearsalReportMapper rehearsalReportMapper;
    private final ModelRegistryService registryService;
    private final PythonGateway gateway;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper om = new ObjectMapper();

    @Value("${system.python.rehearsalScript:../algorithm/prediction/rehearsal.py}")
    private String rehearsalScript;

    public RehearsalServiceImpl(JobService jobService,
                                RehearsalReportMapper rehearsalReportMapper,
                                ModelRegistryService registryService,
                                PythonGateway gateway,
                                StringRedisTemplate redisTemplate) {
        this.jobService = jobService;
        this.rehearsalReportMapper = rehearsalReportMapper;
        this.registryService = registryService;
        this.gateway = gateway;
        this.redisTemplate = redisTemplate;
    }

    @Override
    public Long submit(String model, String version) {
        if (model == null || model.trim().isEmpty() || version == null || version.trim().isEmpty()) {
            throw new IllegalArgumentException("缺少模型或版本参数");
        }
        String active = registryService.activeVersion(model.trim());
        if (active == null) {
            throw new BusinessException(409, "模型 " + model + " 当前没有可加载的线上版本，请先同步注册表");
        }
        if (active.equals(version.trim())) {
            throw new IllegalArgumentException("候选版本与线上版本相同，无需预演");
        }
        return jobService.submit("model.rehearsal",
                Map.of("model", model.trim(), "version", version.trim()));
    }

    @Override
    public JsonNode execute(Long jobId, String params) {
        JsonNode p;
        try {
            p = om.readTree(params);
        } catch (Exception e) {
            throw new RuntimeException("预演任务参数无法解析", e);
        }
        String model = p.path("model").asText();
        String version = p.path("version").asText();

        String out = gateway.runCli(rehearsalScript,
                List.of("--model", model, "--version", version, "--sample", "300"), 600);
        JsonNode node;
        try {
            node = om.readTree(PythonCliRunner.lastJsonLine(out));
        } catch (Exception e) {
            throw new RuntimeException("解析预演结果失败: " + e.getMessage(), e);
        }
        if (node.hasNonNull("error")) {
            throw new RuntimeException(node.path("error").asText());
        }

        RehearsalReport report = new RehearsalReport();
        report.setModel(model);
        report.setCandidateVersion(version);
        report.setActiveVersion(node.path("activeVersion").asText(null));
        report.setSampleSize(node.path("sampleSize").asInt());
        report.setMeanAbsDiffPct(node.path("meanAbsDiffPct").asDouble());
        report.setP50AbsDiffPct(node.path("p50AbsDiffPct").asDouble());
        report.setP90AbsDiffPct(node.path("p90AbsDiffPct").asDouble());
        report.setMaxAbsDiffPct(node.path("maxAbsDiffPct").asDouble());
        report.setPearsonCorr(node.path("pearsonCorr").asDouble());
        report.setTop10Overlap(node.path("top10Overlap").asDouble());
        report.setPassed(node.path("passed").asBoolean());
        ObjectNode detail = om.createObjectNode();
        detail.set("thresholds", node.path("thresholds"));
        detail.set("worstCases", node.path("worstCases"));
        report.setDetailJson(detail.toString());
        report.setJobId(jobId);
        report.setCreateTime(new Date());
        rehearsalReportMapper.insert(report);
        log.info("上线预演完成：{} {} vs {} meanAbsDiff={}% corr={} passed={}",
                model, version, report.getActiveVersion(),
                report.getMeanAbsDiffPct(), report.getPearsonCorr(), report.getPassed());

        ObjectNode summary = toJson(report);
        try {
            redisTemplate.opsForValue().set(latestKey(model, version), summary.toString());
        } catch (Exception e) {
            log.warn("预演报告缓存失败（不影响结果）：{}", e.getMessage());
        }
        return summary;
    }

    @Override
    public JsonNode latest(String model, String version) {
        try {
            String cached = redisTemplate.opsForValue().get(latestKey(model, version));
            if (cached != null) {
                return om.readTree(cached);
            }
        } catch (Exception e) {
            log.warn("读取预演报告缓存失败，回退数据库：{}", e.getMessage());
        }
        RehearsalReport report = latestReport(model, version);
        return report == null ? null : toJson(report);
    }

    @Override
    public void requirePassed(String model, String version) {
        RehearsalReport report = latestReport(model, version);
        if (report == null) {
            throw new BusinessException(409,
                    "版本 " + version + " 尚未进行上线预演，请先运行预演（或确认风险后强制上线）");
        }
        if (!Boolean.TRUE.equals(report.getPassed())) {
            throw new BusinessException(409, String.format(
                    "版本 %s 预演未通过：平均偏差 %.2f%%、相关性 %.4f、头部重合 %.2f（阈值 10%%/0.95/0.70），可强制上线",
                    version, nz(report.getMeanAbsDiffPct()), nz(report.getPearsonCorr()), nz(report.getTop10Overlap())));
        }
        String active = registryService.activeVersion(model);
        if (active != null && !active.equals(report.getActiveVersion())) {
            throw new BusinessException(409,
                    "线上版本已变化（" + report.getActiveVersion() + " → " + active + "），预演结果失效，请重新预演");
        }
    }

    private RehearsalReport latestReport(String model, String version) {
        return rehearsalReportMapper.selectOne(new LambdaQueryWrapper<RehearsalReport>()
                .eq(RehearsalReport::getModel, model)
                .eq(RehearsalReport::getCandidateVersion, version)
                .orderByDesc(RehearsalReport::getId)
                .last("LIMIT 1"));
    }

    private ObjectNode toJson(RehearsalReport report) {
        ObjectNode node = om.valueToTree(report);
        try {
            node.set("detail", om.readTree(report.getDetailJson() == null ? "{}" : report.getDetailJson()));
        } catch (Exception e) {
            node.putObject("detail");
        }
        node.remove("detailJson");
        return node;
    }

    private String latestKey(String model, String version) {
        return LATEST_KEY_PREFIX + model + ":" + version;
    }

    private double nz(Double v) {
        return v == null ? 0.0 : v;
    }
}
