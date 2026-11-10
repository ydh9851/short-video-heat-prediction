package com.alvis.media.service;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * 上线预演：promote 前用候选版本与当前线上版本在真实采样上并行打分，
 * 量化输出偏差并落库；未通过预演门禁的版本不允许直接上线（可人工强制）。
 */
public interface RehearsalService {

    /**
     * 提交预演任务（异步执行），返回任务 ID。
     *
     * @param model   模型名
     * @param version 候选版本号
     */
    Long submit(String model, String version);

    /**
     * 执行预演（由任务中心调用）：跑 rehearsal.py → 落库 → 缓存最新结果。
     *
     * @param jobId  触发本次预演的任务 ID
     * @param params 任务参数（model / version）
     * @return 报告摘要
     */
    JsonNode execute(Long jobId, String params);

    /**
     * 该（模型, 候选版本）最新一份预演报告，无报告时返回 null。
     */
    JsonNode latest(String model, String version);

    /**
     * 上线门禁：存在「通过」且基于当前线上版本的预演报告才放行，
     * 否则抛出带 409 语义的异常，提示先预演或强制上线。
     */
    void requirePassed(String model, String version);
}
