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
 * 上线预演报告：promote 前用候选版本与当前线上版本在真实数据采样上并行打分，
 * 量化两者输出偏差；通过门禁（平均偏差/相关性/头部重合度）才允许直接上线。
 */
@Data
@EqualsAndHashCode
@NoArgsConstructor
@TableName("t_rehearsal_report")
public class RehearsalReport implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    private String model;

    private String candidateVersion;

    /** 预演时的线上版本；上线前若线上版本已变化，本报告失效需重新预演 */
    private String activeVersion;

    private Integer sampleSize;

    /** 平均绝对偏差%（以线上预测为基准） */
    private Double meanAbsDiffPct;

    private Double p50AbsDiffPct;

    private Double p90AbsDiffPct;

    private Double maxAbsDiffPct;

    /** log 尺度 Pearson 相关系数 */
    private Double pearsonCorr;

    /** 头部 10% 样本重合度 0-1 */
    private Double top10Overlap;

    private Boolean passed;

    /** 判定阈值与偏差最大样本（JSON） */
    private String detailJson;

    private Long jobId;

    private Date createTime;
}
