package com.alvis.media.event;

import com.alvis.media.domain.OperationLog;
import org.springframework.context.ApplicationEvent;

/** 审计日志事件：切面采集完成后发布，由监听器异步落库。 */
public class OperationLogEvent extends ApplicationEvent {

    private final OperationLog operationLog;

    public OperationLogEvent(OperationLog operationLog) {
        super(operationLog);
        this.operationLog = operationLog;
    }

    public OperationLog getOperationLog() {
        return operationLog;
    }
}
