package com.alvis.media.service;

import com.alvis.media.domain.Case;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;

/**
 * 分析场景服务：场景的创建、查询、更新与删除。
 * 数据按创建人隔离——普通用户只能看/改自己的场景，管理员可见全部。
 */
public interface CaseService {

    /** 创建场景，返回场景 ID */
    Long create(Case c);

    /** 按 ID 查询（带归属校验：非本人且非管理员返回 null） */
    Case getOwn(Long id);

    /** 分页查询：普通用户查自己的，管理员查全部（可按名称模糊筛选） */
    IPage<Case> page(int pageIndex, int pageSize, String name);

    /** 更新场景（仅允许改名称/描述/参数，归属不可变） */
    void updateOwn(Case c);

    /** 删除场景（归属校验） */
    void deleteOwn(Long id);

    /**
     * 场景对比：对 2~3 个场景逐一计算保形预测区间，并排返回预测、区间与核心输入。
     * 单条计算失败只标记该列 error，不影响其他列。
     */
    JsonNode compare(List<Long> ids);
}
