-- 任务中心：长耗时任务（数据导入 / 批量预测 / 实验）统一登记与追踪
-- 状态机：QUEUED -> RUNNING -> DONE | FAILED
CREATE TABLE IF NOT EXISTS `t_job` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `job_type`    VARCHAR(64)  NOT NULL COMMENT '任务类型，如 data.import',
  `status`      VARCHAR(16)  NOT NULL DEFAULT 'QUEUED' COMMENT 'QUEUED/RUNNING/DONE/FAILED',
  `params`      VARCHAR(2000) DEFAULT NULL COMMENT '任务参数（JSON）',
  `result`      TEXT          DEFAULT NULL COMMENT '任务结果摘要（JSON，截断）',
  `error_msg`   VARCHAR(2000) DEFAULT NULL COMMENT '失败原因',
  `trace_id`    VARCHAR(64)   DEFAULT NULL COMMENT 'TraceId，可串联后端与 Python 日志',
  `user_id`     INT           DEFAULT NULL COMMENT '提交人ID',
  `user_name`   VARCHAR(64)   DEFAULT NULL COMMENT '提交人用户名',
  `cost_ms`     BIGINT        DEFAULT NULL COMMENT '耗时毫秒',
  `create_time` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `start_time`  DATETIME      DEFAULT NULL COMMENT '开始执行时间',
  `finish_time` DATETIME      DEFAULT NULL COMMENT '结束时间',
  PRIMARY KEY (`id`),
  KEY `idx_job_status` (`status`),
  KEY `idx_job_type` (`job_type`),
  KEY `idx_job_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务中心';
