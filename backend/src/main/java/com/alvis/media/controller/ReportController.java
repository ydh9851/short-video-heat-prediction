package com.alvis.media.controller;

import com.alvis.media.annotation.OperationLog;
import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.domain.Report;
import com.alvis.media.exception.BusinessException;
import com.alvis.media.service.ReportService;
import com.alvis.media.viewmodel.report.ReportGenerateRequestVM;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.util.Map;

/**
 * 报告中心接口：报告的生成（异步）、列表、详情、删除、分享与内容读取。
 *
 * <p>分享链接 /api/report/shared/{token} 免登录（token 即凭证，只读）；
 * 其余端点均需登录，且普通用户仅能访问自己的报告。
 */
@RestController("ReportController")
@Tag(name = "报告中心")
@RequestMapping(value = "/api/report")
@AllArgsConstructor
public class ReportController extends BaseApiController {

    private final ReportService reportService;

    private static final ObjectMapper OM = new ObjectMapper();

    /** 提交报告生成（异步，走任务中心）；返回 {reportId, jobId} 供前端轮询 */
    @PostMapping("/generate")
    @OperationLog("report.generate")
    public RestResponse<ObjectNode> generate(@RequestBody ReportGenerateRequestVM vm) {
        return RestResponse.ok(reportService.generate(vm));
    }

    /** 报告分页列表（普通用户仅自己的，管理员全部） */
    @GetMapping("/page")
    public RestResponse<IPage<Report>> page(
            @RequestParam(defaultValue = "1") int pageIndex,
            @RequestParam(defaultValue = "20") int pageSize,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String status) {
        return RestResponse.ok(reportService.page(pageIndex, pageSize, name, status));
    }

    /** 单条详情（归属隔离） */
    @GetMapping("/{id}")
    public RestResponse<Report> get(@PathVariable("id") Long id) {
        Report r = reportService.getOwn(id);
        if (r == null) {
            throw new BusinessException(404, "报告不存在");
        }
        return RestResponse.ok(r);
    }

    /** 删除（归属隔离，同时删除报告文件） */
    @DeleteMapping("/{id}")
    @OperationLog("report.delete")
    public RestResponse<Boolean> delete(@PathVariable("id") Long id) {
        reportService.deleteOwn(id);
        return RestResponse.ok(true);
    }

    /** 开启分享：返回免登录只读链接 */
    @PostMapping("/{id}/share")
    @OperationLog("report.share")
    public RestResponse<ObjectNode> share(@PathVariable("id") Long id) {
        String token = reportService.share(id);
        ObjectNode node = OM.createObjectNode();
        node.put("token", token);
        node.put("url", "/api/report/shared/" + token);
        return RestResponse.ok(node);
    }

    /** 取消分享 */
    @DeleteMapping("/{id}/share")
    @OperationLog("report.unshare")
    public RestResponse<Boolean> unshare(@PathVariable("id") Long id) {
        reportService.unshare(id);
        return RestResponse.ok(true);
    }

    /** 报告内容（登录用户，归属隔离）；download=1 时作为附件下载 */
    @GetMapping("/{id}/content")
    public ResponseEntity<byte[]> content(@PathVariable("id") Long id,
                                          @RequestParam(value = "download", defaultValue = "0") int download) {
        Report r = reportService.getOwn(id);
        if (r == null) {
            throw new BusinessException(404, "报告不存在");
        }
        return contentResponse(r, download);
    }

    /** 分享内容（免登录，token 即凭证，仅 DONE 可见） */
    @GetMapping("/shared/{token}")
    public ResponseEntity<byte[]> shared(@PathVariable("token") String token,
                                         @RequestParam(value = "download", defaultValue = "0") int download) {
        Report r = reportService.getShared(token);
        if (r == null) {
            throw new BusinessException(404, "分享链接无效或报告不可用");
        }
        return contentResponse(r, download);
    }

    private ResponseEntity<byte[]> contentResponse(Report r, int download) {
        byte[] body = reportService.readContent(r);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(new MediaType("text", "html", StandardCharsets.UTF_8));
        headers.setContentLength(body.length);
        if (download == 1) {
            String name = (r.getFileName() == null ? "report.html" : r.getFileName());
            headers.setContentDispositionFormData("attachment", name);
        }
        // 报告内容固定不变（生成后不再覆盖），但与其缓存不如每次直读，逻辑更简单
        return ResponseEntity.ok().headers(headers).body(body);
    }
}
