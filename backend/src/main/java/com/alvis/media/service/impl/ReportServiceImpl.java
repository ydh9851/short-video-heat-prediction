package com.alvis.media.service.impl;

import com.alvis.media.context.WebContext;
import com.alvis.media.domain.Case;
import com.alvis.media.domain.Report;
import com.alvis.media.domain.User;
import com.alvis.media.domain.enums.RoleEnum;
import com.alvis.media.exception.BusinessException;
import com.alvis.media.repository.ReportMapper;
import com.alvis.media.service.CaseService;
import com.alvis.media.service.JobService;
import com.alvis.media.service.ModelRegistryService;
import com.alvis.media.service.ReportService;
import com.alvis.media.utility.PythonCliRunner;
import com.alvis.media.utility.PythonGateway;
import com.alvis.media.viewmodel.report.ReportGenerateRequestVM;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 报告中心实现：报告落库管理 + 任务中心异步生成 + 版本快照 + token 分享。
 *
 * <p>生成链路：generate() 校验并固化版本快照 → 落库（GENERATING）→ 提交任务；
 * execute() 由任务线程回调，调用 build_report.py 生成自包含 HTML 后回写 DONE。
 */
@Service
public class ReportServiceImpl implements ReportService {

    private static final Logger log = LoggerFactory.getLogger(ReportServiceImpl.class);

    /** 报告生成涉及全量 SHAP + 反事实扫描，耗时较长，给足超时 */
    private static final int REPORT_TIMEOUT = 900;

    private final ReportMapper reportMapper;
    private final CaseService caseService;
    private final JobService jobService;
    private final ModelRegistryService registry;
    private final PythonGateway gateway;
    private final WebContext webContext;
    private final ObjectMapper om = new ObjectMapper();

    @Value("${system.python.reportScript:../algorithm/attribution/build_report.py}")
    private String reportScript;

    @Value("${system.reports.dir:../data/reports}")
    private String reportsDir;

    public ReportServiceImpl(ReportMapper reportMapper,
                             CaseService caseService,
                             JobService jobService,
                             ModelRegistryService registry,
                             PythonGateway gateway,
                             WebContext webContext) {
        this.reportMapper = reportMapper;
        this.caseService = caseService;
        this.jobService = jobService;
        this.registry = registry;
        this.gateway = gateway;
        this.webContext = webContext;
    }

    // ------------------------------------------------------------------ 生成

    @Override
    public ObjectNode generate(ReportGenerateRequestVM vm) {
        Case c = null;
        if (vm.getCaseId() != null) {
            c = caseService.getOwn(vm.getCaseId());
            if (c == null) {
                throw new BusinessException(404, "场景不存在或无权限");
            }
        }
        // 场景优先：传了 caseId 则以场景参数为准，实现「从场景一键生成，不重复输入」
        String model = pick(c == null ? vm.getModel() : c.getModel(), "lgbm");
        String category = pick(c == null ? vm.getVideoCategory() : c.getVideoCategory(), null);
        Double fans = c == null ? vm.getAuthorFans() : c.getAuthorFans();
        Integer hour = c == null ? vm.getPublishHour() : c.getPublishHour();
        Integer weekday = c == null ? vm.getPublishWeekday() : c.getPublishWeekday();
        Integer month = c == null ? vm.getPublishMonth() : c.getPublishMonth();

        if (category == null || category.trim().isEmpty()) {
            throw new BusinessException(400, "视频类别不能为空");
        }
        if (fans == null || fans < 0) {
            fans = 0.0;
        }
        if (hour == null || hour < 0 || hour > 23) {
            throw new BusinessException(400, "发布小时需在 0-23 之间");
        }
        if (weekday == null || weekday < 0 || weekday > 6) {
            throw new BusinessException(400, "发布星期需在 0-6 之间");
        }
        if (month == null || month < 1 || month > 12) {
            throw new BusinessException(400, "发布月份需在 1-12 之间");
        }

        Report r = new Report();
        r.setName(pick(vm.getName(),
                "归因报告 · " + (c != null ? c.getName() : category)));
        r.setReportType("attribution");
        if (c != null) {
            r.setCaseId(c.getId());
            r.setCaseName(c.getName());
        }
        r.setModel(model);
        // 版本快照：报告结论可追溯到「哪个模型版本、哪份数据」
        JsonNode meta = registry.activeVersionMeta(model);
        if (meta != null) {
            r.setModelVersion(meta.path("version").asText(null));
            r.setDataVersion(meta.path("dataVersion").asText(null));
            if (meta.hasNonNull("featureVersion")) {
                r.setFeatureVersion(meta.path("featureVersion").asInt());
            }
        }
        r.setParams(writeParams(category, fans, hour, weekday, month));
        r.setStatus("GENERATING");
        User user = webContext.getCurrentUser();
        if (user != null) {
            r.setUserId(user.getId());
            r.setUserName(user.getUserName());
        }
        r.setCreateTime(new Date());
        reportMapper.insert(r);

        Map<String, Object> jobParams = new HashMap<>();
        jobParams.put("reportId", r.getId());
        Long jobId = jobService.submit("report.generate", jobParams);

        Report upd = new Report();
        upd.setId(r.getId());
        upd.setJobId(jobId);
        reportMapper.updateById(upd);

        ObjectNode node = om.createObjectNode();
        node.put("reportId", r.getId());
        node.put("jobId", jobId);
        return node;
    }

    @Override
    public JsonNode execute(Long jobId, String paramsJson) {
        Long reportId;
        try {
            reportId = om.readTree(paramsJson).path("reportId").asLong();
        } catch (Exception e) {
            throw new IllegalArgumentException("报告任务参数无法解析");
        }
        Report r = reportMapper.selectById(reportId);
        if (r == null) {
            throw new BusinessException(404, "报告记录不存在");
        }
        try {
            JsonNode params = om.readTree(r.getParams());
            List<String> args = new ArrayList<>();
            args.addAll(List.of("--model", r.getModel()));
            args.addAll(List.of("--category",
                    URLEncoder.encode(params.path("category").asText(), StandardCharsets.UTF_8)));
            args.addAll(List.of("--fans", String.valueOf(params.path("fans").asDouble())));
            args.addAll(List.of("--hour", String.valueOf(params.path("hour").asInt())));
            args.addAll(List.of("--weekday", String.valueOf(params.path("weekday").asInt())));
            args.addAll(List.of("--month", String.valueOf(params.path("month").asInt())));
            // 文件名按报告 ID 命名：避免同秒并发生成撞名，也让文件与记录一一对应
            args.addAll(List.of("--name", "report_" + r.getId() + ".html"));

            String out = gateway.runCli(reportScript, args, REPORT_TIMEOUT);
            JsonNode node = om.readTree(PythonCliRunner.lastJsonLine(out));
            if (node.hasNonNull("error")) {
                throw new RuntimeException(node.path("error").asText());
            }

            Report done = new Report();
            done.setId(r.getId());
            done.setStatus("DONE");
            done.setFilePath(node.path("file").asText(null));
            String filePath = done.getFilePath();
            if (filePath != null) {
                done.setFileName(filePath.substring(filePath.lastIndexOf('/') + 1));
            }
            if (node.hasNonNull("sizeKB")) {
                done.setSizeKb(node.path("sizeKB").asDouble());
            }
            if (node.hasNonNull("prediction")) {
                done.setPrediction(node.path("prediction").asDouble());
            }
            done.setGrade(node.path("grade").asText(null));
            done.setFinishTime(new Date());
            reportMapper.updateById(done);
            log.info("报告生成完成 id={} file={}", r.getId(), done.getFilePath());
            return node;
        } catch (RuntimeException e) {
            markFailed(r.getId(), e.getMessage());
            throw e;
        } catch (Exception e) {
            markFailed(r.getId(), e.getMessage());
            throw new RuntimeException("报告生成失败: " + e.getMessage(), e);
        }
    }

    // ------------------------------------------------------------------ 查询 / 删除

    @Override
    public IPage<Report> page(int pageIndex, int pageSize, String name, String status) {
        LambdaQueryWrapper<Report> qw = new LambdaQueryWrapper<>();
        User user = webContext.getCurrentUser();
        if (!isAdmin(user)) {
            qw.eq(Report::getUserId, user == null ? -1 : user.getId());
        }
        if (name != null && !name.trim().isEmpty()) {
            qw.like(Report::getName, name.trim());
        }
        if (status != null && !status.trim().isEmpty()) {
            qw.eq(Report::getStatus, status.trim());
        }
        qw.orderByDesc(Report::getId);
        return reportMapper.selectPage(new Page<>(pageIndex, pageSize), qw);
    }

    @Override
    public Report getOwn(Long id) {
        if (id == null) {
            return null;
        }
        Report r = reportMapper.selectById(id);
        if (r == null || !canAccess(r)) {
            return null;
        }
        return r;
    }

    @Override
    public void deleteOwn(Long id) {
        Report r = id == null ? null : reportMapper.selectById(id);
        if (r == null || !canAccess(r)) {
            throw new BusinessException(404, "报告不存在");
        }
        reportMapper.deleteById(id);
        // 尽力删除报告文件：文件可能已被人工清理，失败不影响记录删除
        if (r.getFileName() != null) {
            try {
                Path p = resolveInReportsDir(r.getFileName());
                Files.deleteIfExists(p);
            } catch (Exception e) {
                log.warn("删除报告文件失败 id={} file={}: {}", id, r.getFileName(), e.getMessage());
            }
        }
    }

    // ------------------------------------------------------------------ 分享

    @Override
    public String share(Long id) {
        Report r = id == null ? null : reportMapper.selectById(id);
        if (r == null || !canAccess(r)) {
            throw new BusinessException(404, "报告不存在");
        }
        if (!"DONE".equals(r.getStatus())) {
            throw new BusinessException(400, "报告尚未生成完成，无法分享");
        }
        if (r.getShareToken() != null && !r.getShareToken().isEmpty()) {
            return r.getShareToken();
        }
        String token = UUID.randomUUID().toString().replace("-", "");
        Report upd = new Report();
        upd.setId(id);
        upd.setShareToken(token);
        reportMapper.updateById(upd);
        return token;
    }

    @Override
    public void unshare(Long id) {
        Report r = id == null ? null : reportMapper.selectById(id);
        if (r == null || !canAccess(r)) {
            throw new BusinessException(404, "报告不存在");
        }
        Report upd = new Report();
        upd.setId(id);
        // MyBatis-Plus 默认忽略 null 字段，用 LambdaUpdateWrapper 显式置空
        reportMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper<Report>()
                .eq(Report::getId, id)
                .set(Report::getShareToken, null));
    }

    @Override
    public Report getShared(String token) {
        if (token == null || token.trim().isEmpty()) {
            return null;
        }
        Report r = reportMapper.selectOne(new LambdaQueryWrapper<Report>()
                .eq(Report::getShareToken, token.trim()));
        if (r == null || !"DONE".equals(r.getStatus())) {
            return null;
        }
        return r;
    }

    // ------------------------------------------------------------------ 内容读取

    @Override
    public byte[] readContent(Report report) {
        if (report.getFileName() == null || report.getFileName().isEmpty()) {
            throw new BusinessException(404, "报告文件尚未生成");
        }
        Path p = resolveInReportsDir(report.getFileName());
        if (!Files.isRegularFile(p)) {
            throw new BusinessException(404, "报告文件不存在（可能已被清理）");
        }
        try {
            return Files.readAllBytes(p);
        } catch (Exception e) {
            throw new RuntimeException("读取报告文件失败: " + e.getMessage(), e);
        }
    }

    // ------------------------------------------------------------------ 内部

    private void markFailed(Long reportId, String error) {
        Report failed = new Report();
        failed.setId(reportId);
        failed.setStatus("FAILED");
        failed.setErrorMsg(error == null ? "未知错误"
                : (error.length() > 900 ? error.substring(0, 900) : error));
        failed.setFinishTime(new Date());
        reportMapper.updateById(failed);
    }

    /** 防目录穿越：解析后的路径必须仍位于 reports 目录内 */
    private Path resolveInReportsDir(String fileName) {
        Path base = Paths.get(reportsDir).toAbsolutePath().normalize();
        Path p = base.resolve(fileName).normalize();
        if (!p.startsWith(base)) {
            throw new BusinessException(400, "非法文件路径");
        }
        return p;
    }

    private boolean canAccess(Report r) {
        User user = webContext.getCurrentUser();
        if (isAdmin(user)) {
            return true;
        }
        return user != null && r.getUserId() != null && r.getUserId().equals(user.getId());
    }

    private boolean isAdmin(User user) {
        return user != null && user.getRole() != null
                && user.getRole() == RoleEnum.ADMIN.getCode();
    }

    private String pick(String v, String def) {
        return (v == null || v.trim().isEmpty()) ? def : v.trim();
    }

    private String writeParams(String category, Double fans, Integer hour, Integer weekday, Integer month) {
        try {
            Map<String, Object> m = new HashMap<>();
            m.put("category", category);
            m.put("fans", fans);
            m.put("hour", hour);
            m.put("weekday", weekday);
            m.put("month", month);
            return om.writeValueAsString(m);
        } catch (Exception e) {
            return "{}";
        }
    }
}
