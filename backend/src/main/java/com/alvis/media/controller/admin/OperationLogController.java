package com.alvis.media.controller.admin;

import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.domain.OperationLog;
import com.alvis.media.service.OperationLogService;
import com.baomidou.mybatisplus.core.metadata.IPage;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理操作审计日志查询接口（仅 ADMIN 可访问，由 SecurityConfigurer 控制）。
 */
@RestController
@RequestMapping("/api/admin/operation-log")
@AllArgsConstructor
public class OperationLogController extends BaseApiController {

    private final OperationLogService operationLogService;

    @GetMapping
    public RestResponse<IPage<OperationLog>> page(
            @RequestParam(defaultValue = "1") int pageIndex,
            @RequestParam(defaultValue = "20") int pageSize,
            @RequestParam(required = false) String operation,
            @RequestParam(required = false) String userName) {
        return RestResponse.ok(operationLogService.page(pageIndex, pageSize, operation, userName));
    }
}
