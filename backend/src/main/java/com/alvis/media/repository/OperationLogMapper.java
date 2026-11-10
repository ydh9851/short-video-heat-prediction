package com.alvis.media.repository;

import com.alvis.media.domain.OperationLog;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

/**
 * 管理操作审计日志 Mapper。
 * 直接继承 MyBatis-Plus BaseMapper，无需手写 XML：insert/selectPage/selectList 自动生成。
 */
@Mapper
public interface OperationLogMapper extends BaseMapper<OperationLog> {
}
