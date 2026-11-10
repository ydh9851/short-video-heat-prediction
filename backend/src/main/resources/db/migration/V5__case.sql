-- V5：分析场景（Case）表
-- 承载「一次分析的全部先验输入」，让数据样本 → 预测 → 归因 → 反事实 → 报告全流程不重复输入
CREATE TABLE IF NOT EXISTS `t_case` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '场景ID',
  `name`          VARCHAR(100) NOT NULL COMMENT '场景名称',
  `description`   VARCHAR(500) DEFAULT NULL COMMENT '场景描述',
  `model`         VARCHAR(20)  NOT NULL DEFAULT 'lgbm' COMMENT '选用模型',
  `video_category` VARCHAR(50) NOT NULL COMMENT '视频类别',
  `author_fans`   DOUBLE       NOT NULL DEFAULT 0 COMMENT '作者粉丝数',
  `publish_hour`  INT          NOT NULL COMMENT '发布小时 0-23',
  `publish_weekday` INT        NOT NULL COMMENT '发布星期 0-6',
  `publish_month` INT          NOT NULL COMMENT '发布月份 1-12',
  `source`        VARCHAR(20)  DEFAULT 'manual' COMMENT '来源：manual/data-sample',
  `user_id`       INT          DEFAULT NULL COMMENT '创建人ID',
  `user_name`     VARCHAR(64)  DEFAULT NULL COMMENT '创建人用户名',
  `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`   DATETIME     DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_case_user` (`user_id`),
  KEY `idx_case_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分析场景';
