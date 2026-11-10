package com.alvis.media.controller.admin;

import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.domain.Job;
import com.alvis.media.service.JobService;
import com.baomidou.mybatisplus.core.metadata.IPage;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 任务中心查询接口（仅 ADMIN）：任务列表、单任务状态轮询与失败重试。
 */
@RestController
@RequestMapping("/api/admin/job")
@AllArgsConstructor
public class JobController extends BaseApiController {

    private final JobService jobService;

    /** 任务分页列表（按类型 / 状态筛选） */
    @GetMapping("/page")
    public RestResponse<IPage<Job>> page(
            @RequestParam(defaultValue = "1") int pageIndex,
            @RequestParam(defaultValue = "20") int pageSize,
            @RequestParam(required = false) String jobType,
            @RequestParam(required = false) String status) {
        return RestResponse.ok(jobService.page(pageIndex, pageSize, jobType, status));
    }

    /** 单任务状态（前端轮询用） */
    @GetMapping("/{id}")
    public RestResponse<Job> get(@PathVariable Long id) {
        return RestResponse.ok(jobService.get(id));
    }

    /** 失败/已完成任务重试：以相同参数创建新任务 */
    @PostMapping("/{id}/retry")
    public RestResponse<Long> retry(@PathVariable Long id) {
        return RestResponse.ok(jobService.retry(id));
    }
}
