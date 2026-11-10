package com.alvis.media.service.impl;

import com.alvis.media.context.WebContext;
import com.alvis.media.domain.Job;
import com.alvis.media.domain.User;
import com.alvis.media.exception.BusinessException;
import com.alvis.media.repository.JobMapper;
import com.alvis.media.service.DataService;
import com.alvis.media.service.DriftService;
import com.alvis.media.service.JobService;
import com.alvis.media.service.RehearsalService;
import com.alvis.media.service.ReportService;
import com.alvis.media.utility.DerivedCacheEvictor;
import com.alvis.media.utility.TraceContext;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Lazy;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Service;

import java.util.Date;
import java.util.Map;
import java.util.concurrent.RejectedExecutionException;

/**
 * 任务中心实现：任务落 MySQL（t_job），由独立线程池异步执行。
 *
 * <p>与 Redis 版实验任务（EvaluationTaskService）的差异：
 * 任务中心面向「平台运维动作」（导入、批量预测），要求重启不丢、可审计，
 * 因此用数据库而非 Redis 存状态。
 */
@Service
public class JobServiceImpl implements JobService {

    private static final Logger log = LoggerFactory.getLogger(JobServiceImpl.class);

    /** 结果摘要最大长度，避免大 JSON 撑爆行 */
    private static final int RESULT_MAX = 4000;

    private final JobMapper jobMapper;
    private final ThreadPoolTaskExecutor jobExecutor;
    private final WebContext webContext;
    private final DataService dataService;
    private final DriftService driftService;
    private final RehearsalService rehearsalService;
    private final ReportService reportService;
    private final DerivedCacheEvictor cacheEvictor;
    private final ObjectMapper om = new ObjectMapper();

    public JobServiceImpl(JobMapper jobMapper,
                          @Qualifier("jobExecutor") ThreadPoolTaskExecutor jobExecutor,
                          WebContext webContext,
                          @Lazy DataService dataService,
                          @Lazy DriftService driftService,
                          @Lazy RehearsalService rehearsalService,
                          @Lazy ReportService reportService,
                          DerivedCacheEvictor cacheEvictor) {
        this.jobMapper = jobMapper;
        this.jobExecutor = jobExecutor;
        this.webContext = webContext;
        this.dataService = dataService;
        this.driftService = driftService;
        this.rehearsalService = rehearsalService;
        this.reportService = reportService;
        this.cacheEvictor = cacheEvictor;
    }

    @Override
    public Long submit(String jobType, Map<String, Object> params) {
        Job job = new Job();
        job.setJobType(jobType);
        job.setStatus("QUEUED");
        job.setParams(writeJson(params));
        job.setTraceId(TraceContext.current());
        User user = webContext.getCurrentUser();
        if (user != null) {
            job.setUserId(user.getId());
            job.setUserName(user.getUserName());
        }
        job.setCreateTime(new Date());
        jobMapper.insert(job);

        String traceId = job.getTraceId();
        try {
            jobExecutor.execute(() -> runJob(job.getId(), traceId));
        } catch (RejectedExecutionException e) {
            markFailed(job.getId(), "任务队列已满，请稍后重试");
            throw new BusinessException(429, "任务队列已满，请稍后重试");
        }
        return job.getId();
    }

    @Override
    public Job get(Long id) {
        if (id == null) {
            return null;
        }
        return jobMapper.selectById(id);
    }

    @Override
    public IPage<Job> page(int pageIndex, int pageSize, String jobType, String status) {
        LambdaQueryWrapper<Job> qw = new LambdaQueryWrapper<>();
        if (jobType != null && !jobType.trim().isEmpty()) {
            qw.eq(Job::getJobType, jobType.trim());
        }
        if (status != null && !status.trim().isEmpty()) {
            qw.eq(Job::getStatus, status.trim());
        }
        qw.orderByDesc(Job::getId);
        return jobMapper.selectPage(new Page<>(pageIndex, pageSize), qw);
    }

    @Override
    public Long retry(Long id) {
        Job origin = get(id);
        if (origin == null) {
            throw new BusinessException(404, "任务不存在");
        }
        if ("RUNNING".equals(origin.getStatus()) || "QUEUED".equals(origin.getStatus())) {
            throw new BusinessException(400, "任务正在执行中，无需重试");
        }
        Map<String, Object> params;
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> p = om.readValue(origin.getParams(), Map.class);
            params = p;
        } catch (Exception e) {
            throw new BusinessException(400, "原任务参数无法解析，不能重试");
        }
        return submit(origin.getJobType(), params);
    }

    // ------------------------------------------------------------------ 执行

    private void runJob(Long jobId, String traceId) {
        if (traceId != null) {
            TraceContext.bind(traceId);
        }
        long start = System.currentTimeMillis();
        Job job = jobMapper.selectById(jobId);
        if (job == null) {
            return;
        }
        Job running = new Job();
        running.setId(jobId);
        running.setStatus("RUNNING");
        running.setStartTime(new Date());
        jobMapper.updateById(running);
        try {
            JsonNode result = dispatch(job.getId(), job.getJobType(), job.getParams());
            Job done = new Job();
            done.setId(jobId);
            done.setStatus("DONE");
            done.setResult(truncate(result == null ? null : result.toString()));
            done.setCostMs(System.currentTimeMillis() - start);
            done.setFinishTime(new Date());
            jobMapper.updateById(done);
            log.info("任务完成 id={} type={} 耗时={}ms", jobId, job.getJobType(), System.currentTimeMillis() - start);
        } catch (Exception e) {
            log.error("任务失败 id={} type={}", jobId, job.getJobType(), e);
            markFailed(jobId, e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage());
        } finally {
            TraceContext.clear();
        }
    }

    /** 按任务类型分发到具体业务服务 */
    private JsonNode dispatch(Long jobId, String jobType, String paramsJson) throws Exception {
        if ("data.import".equals(jobType)) {
            JsonNode params = om.readTree(paramsJson);
            String platform = params.path("platform").asText();
            JsonNode result = dataService.importPlatform(platform);
            // 导入成功后主动失效派生缓存：数据变了，预测/归因/分级结果必须重算
            if (result != null && result.path("code").asInt() == 1) {
                cacheEvictor.evictAll();
            }
            return result;
        }
        if ("model.drift".equals(jobType)) {
            return driftService.execute(jobId);
        }
        if ("model.rehearsal".equals(jobType)) {
            return rehearsalService.execute(jobId, paramsJson);
        }
        if ("report.generate".equals(jobType)) {
            return reportService.execute(jobId, paramsJson);
        }
        throw new IllegalArgumentException("未知任务类型：" + jobType);
    }

    private void markFailed(Long jobId, String error) {
        Job failed = new Job();
        failed.setId(jobId);
        failed.setStatus("FAILED");
        failed.setErrorMsg(truncate(error));
        failed.setFinishTime(new Date());
        jobMapper.updateById(failed);
    }

    private String writeJson(Map<String, Object> params) {
        try {
            return om.writeValueAsString(params);
        } catch (Exception e) {
            return "{}";
        }
    }

    private String truncate(String s) {
        if (s == null) {
            return null;
        }
        return s.length() > RESULT_MAX ? s.substring(0, RESULT_MAX) : s;
    }
}
