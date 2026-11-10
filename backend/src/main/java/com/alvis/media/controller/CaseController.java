package com.alvis.media.controller;

import com.alvis.media.annotation.OperationLog;
import com.alvis.media.base.BaseApiController;
import com.alvis.media.base.RestResponse;
import com.alvis.media.domain.Case;
import com.alvis.media.service.CaseService;
import com.alvis.media.viewmodel.scenario.CaseCompareRequestVM;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 分析场景接口（登录用户）：场景的增删改查。
 * 普通用户仅能访问自己的场景，管理员可见全部（归属校验在 Service 层）。
 */
@RestController
@RequestMapping("/api/case")
@AllArgsConstructor
public class CaseController extends BaseApiController {

    private final CaseService caseService;

    /** 创建场景（从预测页/数据样本页「存为场景」调用） */
    @PostMapping
    public RestResponse<Long> create(@RequestBody Case c) {
        return RestResponse.ok(caseService.create(c));
    }

    /** 场景分页列表 */
    @GetMapping("/page")
    public RestResponse<IPage<Case>> page(
            @RequestParam(defaultValue = "1") int pageIndex,
            @RequestParam(defaultValue = "20") int pageSize,
            @RequestParam(required = false) String name) {
        return RestResponse.ok(caseService.page(pageIndex, pageSize, name));
    }

    /** 单个场景详情 */
    @GetMapping("/{id}")
    public RestResponse<Case> get(@PathVariable Long id) {
        return RestResponse.ok(caseService.getOwn(id));
    }

    /** 更新场景 */
    @PutMapping("/{id}")
    public RestResponse<Boolean> update(@PathVariable Long id, @RequestBody Case c) {
        c.setId(id);
        caseService.updateOwn(c);
        return RestResponse.ok(true);
    }

    /** 删除场景 */
    @DeleteMapping("/{id}")
    public RestResponse<Boolean> delete(@PathVariable Long id) {
        caseService.deleteOwn(id);
        return RestResponse.ok(true);
    }

    /** 场景对比：2~3 个场景并排返回预测、保形区间与核心输入 */
    @PostMapping("/compare")
    @OperationLog("场景.对比")
    public RestResponse<JsonNode> compare(@RequestBody CaseCompareRequestVM req) {
        return RestResponse.ok(caseService.compare(req.getIds()));
    }
}
