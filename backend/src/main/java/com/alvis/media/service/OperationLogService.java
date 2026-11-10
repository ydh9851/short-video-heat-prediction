package com.alvis.media.service;

import com.alvis.media.domain.OperationLog;
import com.baomidou.mybatisplus.core.metadata.IPage;

public interface OperationLogService {

    /** 异步保存审计日志（由监听器调用，不阻塞主请求）。 */
    void saveAsync(OperationLog log);

    /** 分页查询审计日志。 */
    IPage<OperationLog> page(int pageIndex, int pageSize, String operation, String userName);
}
