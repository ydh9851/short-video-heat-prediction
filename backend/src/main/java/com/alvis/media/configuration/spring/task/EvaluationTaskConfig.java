package com.alvis.media.configuration.spring.task;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

/**
 * 长耗时实验（交叉验证 / 超参数搜索 / 学习曲线等）专用线程池。
 *
 * <p>这些实验单次可能跑数分钟，若在 HTTP 请求线程里同步执行，前端只能干等到超时。
 * 单独隔离一个线程池后，接口立即返回 taskId，前端轮询任务状态，
 * 同时避免实验把 Web 工作线程占满导致整个站点卡死。
 */
@Configuration
public class EvaluationTaskConfig {

    public static final String EXECUTOR_NAME = "evaluationTaskExecutor";

    @Bean(name = EXECUTOR_NAME)
    public ThreadPoolTaskExecutor evaluationTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        // Python 侧单次实验已占满一个 CPU 核心，并发过高只会互相拖慢，故并发度控制在 2~4
        executor.setCorePoolSize(2);
        executor.setMaxPoolSize(4);
        executor.setQueueCapacity(20);
        executor.setThreadNamePrefix("eval-task-");
        // 关停时等待在跑的实验收尾，避免 Python 子进程被硬切断留下半个缓存文件
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(60);
        executor.initialize();
        return executor;
    }
}
