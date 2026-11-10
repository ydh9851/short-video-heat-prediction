package com.alvis.media.service.impl;

import com.alvis.media.domain.OperationLog;
import com.alvis.media.repository.OperationLogMapper;
import com.alvis.media.service.OperationLogService;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.Date;

@Service
public class OperationLogServiceImpl implements OperationLogService {

    private static final Logger log = LoggerFactory.getLogger(OperationLogServiceImpl.class);

    private final OperationLogMapper mapper;

    public OperationLogServiceImpl(OperationLogMapper mapper) {
        this.mapper = mapper;
    }

    @Override
    @Async
    public void saveAsync(OperationLog record) {
        try {
            if (record.getCreateTime() == null) {
                record.setCreateTime(new Date());
            }
            mapper.insert(record);
        } catch (Exception e) {
            // 审计日志写入失败绝不能影响主业务流程
            log.warn("审计日志写入失败: {}", e.getMessage());
        }
    }

    @Override
    public IPage<OperationLog> page(int pageIndex, int pageSize, String operation, String userName) {
        LambdaQueryWrapper<OperationLog> wrapper = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(operation)) {
            wrapper.eq(OperationLog::getOperation, operation);
        }
        if (StringUtils.hasText(userName)) {
            wrapper.like(OperationLog::getUserName, userName);
        }
        wrapper.orderByDesc(OperationLog::getId);
        return mapper.selectPage(new Page<>(pageIndex, pageSize), wrapper);
    }
}
