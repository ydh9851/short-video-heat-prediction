package com.alvis.media.service;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * 漂移监控：按需运行跨平台特征分布漂移检测（PSI/KS），
 * 结果落库并缓存最新一份，供治理页展示漂移指标与告警。
 */
public interface DriftService {

    /**
     * 提交漂移检测任务（异步执行），返回任务 ID。
     */
    Long submit();

    /**
     * 执行漂移检测（由任务中心调用）：跑 Python 脚本 → 落库 → 缓存最新结果。
     *
     * @param jobId 触发本次检测的任务 ID（登记到报告中便于追溯）
     * @return 报告摘要
     */
    JsonNode execute(Long jobId);

    /**
     * 最新一份漂移报告（含明细），无报告时返回 null。
     */
    JsonNode latest();
}
