package com.alvis.media.viewmodel.report;

import lombok.Data;

/**
 * 报告生成请求：caseId 与手动参数二选一。
 * 传 caseId 时以场景参数为准（手动字段忽略），实现「从场景一键生成」；
 * 不传 caseId 时使用手动输入的先验参数。
 */
@Data
public class ReportGenerateRequestVM {

    /** 报告名称（缺省自动命名：归因报告 · <场景名或类别>） */
    private String name;

    /** 关联场景 ID（可空） */
    private Long caseId;

    private String model;

    private String videoCategory;

    private Double authorFans;

    private Integer publishHour;

    private Integer publishWeekday;

    private Integer publishMonth;
}
