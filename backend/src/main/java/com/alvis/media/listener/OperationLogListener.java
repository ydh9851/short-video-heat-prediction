package com.alvis.media.listener;

import com.alvis.media.event.OperationLogEvent;
import com.alvis.media.service.OperationLogService;
import lombok.AllArgsConstructor;
import org.springframework.context.ApplicationListener;
import org.springframework.stereotype.Component;

@Component
@AllArgsConstructor
public class OperationLogListener implements ApplicationListener<OperationLogEvent> {

    private final OperationLogService operationLogService;

    @Override
    public void onApplicationEvent(OperationLogEvent event) {
        operationLogService.saveAsync(event.getOperationLog());
    }
}
