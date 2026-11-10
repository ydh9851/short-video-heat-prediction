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
 * 任务中心：长耗时任务统一登记（数据导入、批量预测、实验等）。
 *
 * <p>状态机：QUEUED → RUNNING → DONE / FAILED。
 * 与 EvaluationTaskService 的 Redis 任务不同：本表持久化到 MySQL，
 * 重启不丢、可按人/类型/状态追溯，是平台「可运维」能力的载体。
 */
@Data
@EqualsAndHashCode
@NoArgsConstructor
@TableName("t_job")
public class Job implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 任务类型：data.import / predict.batch / evaluation.run */
    private String jobType;

    /** QUEUED / RUNNING / DONE / FAILED */
    private String status;

    /** 任务参数（JSON） */
    private String params;

    /** 结果摘要（JSON，截断存储） */
    private String result;

    private String errorMsg;

    private String traceId;

    private Integer userId;

    private String userName;

    private Long costMs;

    private Date createTime;

    private Date startTime;

    private Date finishTime;
}
