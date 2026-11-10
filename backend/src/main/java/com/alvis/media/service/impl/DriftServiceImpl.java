package com.alvis.media.service.impl;

import com.alvis.media.domain.DriftReport;
import com.alvis.media.repository.DriftReportMapper;
import com.alvis.media.service.DriftService;
import com.alvis.media.service.JobService;
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

import java.util.Collections;
import java.util.Date;
import java.util.List;

/**
 * 漂移监控实现：复用实验脚本的 drift 模式（跨平台特征 PSI/KS），
 * 结果落 t_drift_report 并把最新一份缓存进 Redis，治理页秒级读取。
 */
@Service
public class DriftServiceImpl implements DriftService {

    private static final Logger log = LoggerFactory.getLogger(DriftServiceImpl.class);

    private static final String LATEST_KEY = "drift:latest";

    private final JobService jobService;
    private final DriftReportMapper driftReportMapper;
    private final PythonGateway gateway;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper om = new ObjectMapper();

    @Value("${system.python.evaluationScript:../algorithm/evaluation/model_evaluation.py}")
    private String evaluationScript;

    public DriftServiceImpl(JobService jobService,
                            DriftReportMapper driftReportMapper,
                            PythonGateway gateway,
                            StringRedisTemplate redisTemplate) {
        this.jobService = jobService;
        this.driftReportMapper = driftReportMapper;
        this.gateway = gateway;
        this.redisTemplate = redisTemplate;
    }

    @Override
    public Long submit() {
        return jobService.submit("model.drift", Collections.emptyMap());
    }

    @Override
    public JsonNode execute(Long jobId) {
        String out = gateway.runCli(evaluationScript, List.of("--mode", "drift"), 900);
        JsonNode node;
        try {
            node = om.readTree(PythonCliRunner.lastJsonLine(out));
        } catch (Exception e) {
            throw new RuntimeException("解析漂移检测结果失败: " + e.getMessage(), e);
        }
        if (node.hasNonNull("error")) {
            throw new RuntimeException(node.path("error").asText());
        }

        DriftReport report = new DriftReport();
        report.setReferencePlatform(node.path("reference").asText(null));
        report.setReferenceCn(node.path("reference_cn").asText(null));
        report.setMaxPsi(node.path("max_psi").asDouble());
        report.setStableRatio(node.path("stable_ratio").asDouble());
        report.setWorstPlatform(node.path("worst_platform").asText(null));
        report.setWorstFeature(node.path("worst_feature").asText(null));
        report.setDetailJson(node.path("detail").toString());
        report.setJobId(jobId);
        report.setCreateTime(new Date());
        driftReportMapper.insert(report);
        log.info("漂移检测完成：maxPsi={} stableRatio={} worst={}/{}",
                report.getMaxPsi(), report.getStableRatio(), report.getWorstPlatform(), report.getWorstFeature());

        ObjectNode summary = toJson(report);
        try {
            redisTemplate.opsForValue().set(LATEST_KEY, summary.toString());
        } catch (Exception e) {
            log.warn("漂移报告缓存失败（不影响结果）：{}", e.getMessage());
        }
        return summary;
    }

    @Override
    public JsonNode latest() {
        try {
            String cached = redisTemplate.opsForValue().get(LATEST_KEY);
            if (cached != null) {
                return om.readTree(cached);
            }
        } catch (Exception e) {
            log.warn("读取漂移报告缓存失败，回退数据库：{}", e.getMessage());
        }
        DriftReport report = driftReportMapper.selectOne(
                new LambdaQueryWrapper<DriftReport>().orderByDesc(DriftReport::getId).last("LIMIT 1"));
        return report == null ? null : toJson(report);
    }

    private ObjectNode toJson(DriftReport report) {
        ObjectNode node = om.valueToTree(report);
        try {
            node.put("detail", om.readTree(report.getDetailJson() == null ? "[]" : report.getDetailJson()));
        } catch (Exception e) {
            node.putArray("detail");
        }
        node.remove("detailJson");
        return node;
    }
}
