package com.alvis.media.service;

import com.alvis.media.domain.Report;
import com.alvis.media.viewmodel.report.ReportGenerateRequestVM;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

/**
 * 报告中心：报告的生成（异步）、查询、删除与分享。
 *
 * <p>生成走任务中心（jobType=report.generate），报告行先落库（GENERATING），
 * 任务完成后回写文件信息；版本快照（模型/数据/特征版本）在提交时固化，
 * 保证报告可追溯到「哪个模型、用哪份数据、对什么输入」。
 */
public interface ReportService {

    /**
     * 提交报告生成：校验参数（或场景）、固化版本快照、落库（GENERATING）、提交任务。
     *
     * @return {reportId, jobId}
     */
    ObjectNode generate(ReportGenerateRequestVM vm);

    /** 任务中心回调：执行 Python 报告脚本，回写结果（DONE/FAILED）。 */
    JsonNode execute(Long jobId, String paramsJson);

    /** 分页查询（归属隔离：普通用户仅自己的，管理员全部） */
    IPage<Report> page(int pageIndex, int pageSize, String name, String status);

    /** 单条详情（归属隔离，不存在/无权限返回 null） */
    Report getOwn(Long id);

    /** 删除（归属隔离；同时尽力删除报告文件） */
    void deleteOwn(Long id);

    /** 开启分享：已有 token 直接复用，否则生成新 token；返回 token */
    String share(Long id);

    /** 取消分享：清空 token */
    void unshare(Long id);

    /** 按分享令牌查询（仅 DONE 状态可见，否则返回 null） */
    Report getShared(String token);

    /** 读取报告 HTML 内容（目录穿越校验；文件缺失抛 404） */
    byte[] readContent(Report report);
}
