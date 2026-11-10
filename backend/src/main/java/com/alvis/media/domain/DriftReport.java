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
 * 特征分布漂移报告：按需运行漂移检测脚本（PSI/KS）后落库，
 * 治理页据此展示漂移指标与告警，回答「数据分布还稳不稳、模型假设是否仍成立」。
 */
@Data
@EqualsAndHashCode
@NoArgsConstructor
@TableName("t_drift_report")
public class DriftReport implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /** 参照平台（基准分布） */
    private String referencePlatform;

    private String referenceCn;

    /** 最大 PSI：<0.1 稳定；0.1~0.25 中等漂移；>=0.25 显著漂移 */
    private Double maxPsi;

    /** 稳定特征占比 0-1 */
    private Double stableRatio;

    private String worstPlatform;

    private String worstFeature;

    /** 逐平台×特征 PSI/KS 明细（JSON 数组） */
    private String detailJson;

    /** 产生本报告的任务ID */
    private Long jobId;

    private Date createTime;
}
