-- V6：模型治理闭环 —— 漂移监控报告 + 上线预演报告
-- 漂移监控：按需运行 model_evaluation.py --mode drift，结果落库供治理页展示指标与告警
CREATE TABLE IF NOT EXISTS `t_drift_report` (
  `id`                 BIGINT       NOT NULL AUTO_INCREMENT COMMENT '报告ID',
  `reference_platform` VARCHAR(32)  DEFAULT NULL COMMENT '参照平台',
  `reference_cn`       VARCHAR(32)  DEFAULT NULL COMMENT '参照平台中文名',
  `max_psi`            DOUBLE       DEFAULT NULL COMMENT '最大 PSI（>=0.25 显著漂移）',
  `stable_ratio`       DOUBLE       DEFAULT NULL COMMENT '稳定特征占比 0-1',
  `worst_platform`     VARCHAR(32)  DEFAULT NULL COMMENT '漂移最严重平台',
  `worst_feature`      VARCHAR(64)  DEFAULT NULL COMMENT '漂移最严重特征',
  `detail_json`        TEXT         DEFAULT NULL COMMENT '逐平台×特征 PSI/KS 明细（JSON 数组）',
  `job_id`             BIGINT       DEFAULT NULL COMMENT '产生本报告的任务ID',
  `create_time`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_drift_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='特征分布漂移报告';

-- 上线预演：promote 前用候选版本与当前线上版本在真实采样上并行打分，量化输出偏差
CREATE TABLE IF NOT EXISTS `t_rehearsal_report` (
  `id`                 BIGINT       NOT NULL AUTO_INCREMENT COMMENT '报告ID',
  `model`              VARCHAR(20)  NOT NULL COMMENT '模型名',
  `candidate_version`  VARCHAR(64)  NOT NULL COMMENT '候选版本',
  `active_version`     VARCHAR(64)  DEFAULT NULL COMMENT '预演时的线上版本',
  `sample_size`        INT          DEFAULT 0 COMMENT '采样条数',
  `mean_abs_diff_pct`  DOUBLE       DEFAULT NULL COMMENT '平均绝对偏差%',
  `p50_abs_diff_pct`   DOUBLE       DEFAULT NULL COMMENT 'P50 绝对偏差%',
  `p90_abs_diff_pct`   DOUBLE       DEFAULT NULL COMMENT 'P90 绝对偏差%',
  `max_abs_diff_pct`   DOUBLE       DEFAULT NULL COMMENT '最大绝对偏差%',
  `pearson_corr`       DOUBLE       DEFAULT NULL COMMENT 'log 尺度 Pearson 相关',
  `top10_overlap`      DOUBLE       DEFAULT NULL COMMENT '头部 10% 样本重合度 0-1',
  `passed`             TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否通过上线门禁',
  `detail_json`        TEXT         DEFAULT NULL COMMENT '阈值与偏差最大样本（JSON）',
  `job_id`             BIGINT       DEFAULT NULL COMMENT '产生本报告的任务ID',
  `create_time`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_rehearsal_model_version` (`model`, `candidate_version`),
  KEY `idx_rehearsal_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型上线预演报告';
