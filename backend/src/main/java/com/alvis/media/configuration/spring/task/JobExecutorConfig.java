package com.alvis.media.configuration.spring.task;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

/**
 * 任务中心专用线程池：数据导入等长耗时任务在此执行。
 *
 * <p>与实验线程池（evaluationTaskExecutor）隔离：导入任务可达十余分钟，
 * 若与实验共用池子会互相挤占。导入是 IO + Python 单进程密集型，
 * 并发度保持在 1~2 即可，过多并发反而拖慢磁盘与 Python 侧训练。
 */
@Configuration
public class JobExecutorConfig {

    public static final String EXECUTOR_NAME = "jobExecutor";

    @Bean(name = EXECUTOR_NAME)
    public ThreadPoolTaskExecutor jobExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(1);
        executor.setMaxPoolSize(2);
        executor.setQueueCapacity(50);
        executor.setThreadNamePrefix("job-");
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(120);
        executor.initialize();
        return executor;
    }
}
