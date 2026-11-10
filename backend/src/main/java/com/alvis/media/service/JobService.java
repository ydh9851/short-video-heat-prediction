package com.alvis.media.service;

import com.alvis.media.domain.Job;
import com.baomidou.mybatisplus.core.metadata.IPage;

import java.util.Map;

/**
 * 任务中心：长耗时任务的提交、执行与查询。
 */
public interface JobService {

    /**
     * 提交任务：登记为 QUEUED 后立即返回任务 ID，由独立线程池异步执行。
     *
     * @param jobType 任务类型（当前支持 data.import）
     * @param params  任务参数
     * @return 任务 ID
     */
    Long submit(String jobType, Map<String, Object> params);

    /** 查询单个任务（不存在返回 null） */
    Job get(Long id);

    /** 分页查询（按创建时间倒序），可按类型 / 状态筛选 */
    IPage<Job> page(int pageIndex, int pageSize, String jobType, String status);

    /**
     * 重试：以相同类型与参数创建一个新任务（保留原任务作为历史）。
     *
     * @return 新任务 ID
     */
    Long retry(Long id);
}
