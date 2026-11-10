package com.alvis.media.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Date;

/**
 * 报告中心：一次归因报告的完整快照。
 *
 * <p>报告与场景（Case）联动：从当前场景一键生成，记录场景名称快照；
 * 同时快照生成时的模型版本 / 数据版本 / 特征版本，保证报告可追溯到
 * 「哪个模型、用哪份数据、对什么输入」得出的结论。
 */
@Data
@EqualsAndHashCode
@NoArgsConstructor
@TableName("t_report")
public class Report implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    private String name;

    /** 报告类型：attribution=归因报告（表结构预留扩展） */
    private String reportType;

    /** 关联场景 ID（可空：手动输入参数生成） */
    private Long caseId;

    /** 场景名称快照：场景后续改名或删除不影响已生成报告的可读性 */
    private String caseName;

    private String model;

    /** 生成时的线上模型版本（ModelRegistry active） */
    private String modelVersion;

    /** 模型训练所用的数据版本 */
    private String dataVersion;

    /** 特征体系版本 */
    private Integer featureVersion;

    /** 报告输入参数 JSON：category/fans/hour/weekday/month */
    private String params;

    /** GENERATING / DONE / FAILED */
    private String status;

    private String fileName;

    private String filePath;

    private Double sizeKb;

    private Double prediction;

    private String grade;

    private String errorMsg;

    /** 分享令牌：免登录只读访问凭证（/api/report/shared/{token}） */
    private String shareToken;

    private Long jobId;

    private Integer userId;

    private String userName;

    private Date createTime;

    private Date finishTime;
}
