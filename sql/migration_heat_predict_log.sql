-- 增量迁移：短视频热度预测记录表
-- 用法：mysql --default-character-set=utf8mb4 -uroot -p 库名 < migration_heat_predict_log.sql
-- 幂等，可重复执行

CREATE TABLE IF NOT EXISTS `t_heat_predict_log` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `model` varchar(20) DEFAULT NULL COMMENT '模型',
  `video_category` varchar(50) DEFAULT NULL COMMENT '视频类别',
  `author_fans` bigint(20) DEFAULT NULL COMMENT '作者粉丝数',
  `publish_hour` int(11) DEFAULT NULL COMMENT '发布小时',
  `publish_weekday` int(11) DEFAULT NULL COMMENT '发布星期',
  `publish_month` int(11) DEFAULT NULL COMMENT '发布月份',
  `prediction` double DEFAULT NULL COMMENT '预测热度',
  `prediction_log` double DEFAULT NULL COMMENT '预测热度(log1p)',
  `grade` varchar(20) DEFAULT NULL COMMENT '热度等级',
  `source` varchar(20) DEFAULT NULL COMMENT '来源 single/batch',
  `creator_id` int(11) DEFAULT NULL COMMENT '操作人ID',
  `create_time` datetime DEFAULT NULL COMMENT '记录时间',
  PRIMARY KEY (`id`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='短视频热度预测记录';
