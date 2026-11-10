-- 增量迁移：管理操作审计日志表
-- 用法：mysql --default-character-set=utf8mb4 -uroot -p 库名 < migration_operation_log.sql
-- 幂等，可重复执行

CREATE TABLE IF NOT EXISTS `t_operation_log` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL COMMENT '操作人ID',
  `user_name` varchar(50) DEFAULT NULL COMMENT '操作人账号',
  `operation` varchar(100) DEFAULT NULL COMMENT '操作名称（如 model.promote / data.import）',
  `method` varchar(200) DEFAULT NULL COMMENT 'Controller 类名#方法名',
  `params` text COMMENT '请求参数（JSON，截断 2000 字符）',
  `result` varchar(20) DEFAULT NULL COMMENT '执行结果 SUCCESS/FAILURE',
  `error_msg` varchar(500) DEFAULT NULL COMMENT '失败原因',
  `cost_ms` bigint(20) DEFAULT NULL COMMENT '耗时(毫秒)',
  `trace_id` varchar(64) DEFAULT NULL COMMENT '链路追踪ID',
  `ip` varchar(64) DEFAULT NULL COMMENT '客户端IP',
  `create_time` datetime DEFAULT NULL COMMENT '操作时间',
  PRIMARY KEY (`id`),
  KEY `idx_create_time` (`create_time`),
  KEY `idx_user_name` (`user_name`),
  KEY `idx_operation` (`operation`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='管理操作审计日志';
