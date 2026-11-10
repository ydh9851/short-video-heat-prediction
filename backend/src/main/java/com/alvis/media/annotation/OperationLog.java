package com.alvis.media.annotation;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 标记需要记录审计日志的管理接口。
 * 由 OperationLogAspect 统一采集操作人、参数、耗时、结果并异步落库。
 *
 * <p>用法：在 Controller 方法上加 {@code @OperationLog("model.promote")}。
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface OperationLog {

    /** 操作名称，建议使用「模块.动作」格式，如 model.promote / data.import */
    String value();
}
