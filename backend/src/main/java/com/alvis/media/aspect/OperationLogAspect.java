package com.alvis.media.aspect;

import com.alvis.media.annotation.OperationLog;
import com.alvis.media.context.WebContext;
import com.alvis.media.domain.User;
import com.alvis.media.event.OperationLogEvent;
import com.alvis.media.utility.TraceContext;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.Date;

/**
 * 管理操作审计切面：拦截标注了 {@link OperationLog} 的 Controller 方法，
 * 采集操作人 / 参数 / 耗时 / 结果，通过事件异步写入 t_operation_log。
 *
 * <p>约束：
 * <ul>
 *   <li>参数 JSON 截断到 2000 字符，避免大请求撑爆日志表；</li>
 *   <li>无论成功失败都记录（失败时记录错误摘要）；</li>
 *   <li>采集过程任何异常都吞掉，绝不影响主业务返回。</li>
 * </ul>
 */
@Aspect
@Component
public class OperationLogAspect {

    private static final Logger log = LoggerFactory.getLogger(OperationLogAspect.class);
    private static final int PARAMS_MAX_LEN = 2000;

    private final ApplicationEventPublisher publisher;
    private final WebContext webContext;
    private final ObjectMapper om = new ObjectMapper();

    public OperationLogAspect(ApplicationEventPublisher publisher, WebContext webContext) {
        this.publisher = publisher;
        this.webContext = webContext;
    }

    @Around("@annotation(opLog)")
    public Object around(ProceedingJoinPoint pjp, OperationLog opLog) throws Throwable {
        long start = System.currentTimeMillis();
        com.alvis.media.domain.OperationLog record = new com.alvis.media.domain.OperationLog();
        record.setOperation(opLog.value());
        MethodSignature sig = (MethodSignature) pjp.getSignature();
        record.setMethod(sig.getDeclaringType().getSimpleName() + "#" + sig.getName());
        record.setTraceId(TraceContext.current());
        fillUser(record);
        fillIp(record);
        record.setParams(safeArgs(pjp.getArgs()));

        String result = "SUCCESS";
        String errorMsg = null;
        Object ret;
        try {
            ret = pjp.proceed();
            return ret;
        } catch (Throwable t) {
            result = "FAILURE";
            errorMsg = t.getMessage();
            if (errorMsg != null && errorMsg.length() > 500) {
                errorMsg = errorMsg.substring(0, 500);
            }
            throw t;
        } finally {
            try {
                record.setResult(result);
                record.setErrorMsg(errorMsg);
                record.setCostMs(System.currentTimeMillis() - start);
                record.setCreateTime(new Date());
                publisher.publishEvent(new OperationLogEvent(record));
            } catch (Exception e) {
                log.warn("发布审计日志事件失败: {}", e.getMessage());
            }
        }
    }

    private void fillUser(com.alvis.media.domain.OperationLog record) {
        try {
            User user = webContext.getCurrentUser();
            if (user != null) {
                record.setUserId(user.getId());
                record.setUserName(user.getUserName());
                return;
            }
        } catch (Exception ignore) {
            // 未登录 / 非 Web 请求时从 SecurityContext 兜底取用户名
        }
        try {
            Object principal = SecurityContextHolder.getContext().getAuthentication().getPrincipal();
            if (principal instanceof org.springframework.security.core.userdetails.User u) {
                record.setUserName(u.getUsername());
            }
        } catch (Exception ignore) {
        }
    }

    private void fillIp(com.alvis.media.domain.OperationLog record) {
        try {
            ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs == null) {
                return;
            }
            HttpServletRequest req = attrs.getRequest();
            String ip = req.getHeader("X-Forwarded-For");
            if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
                ip = req.getHeader("X-Real-IP");
            }
            if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
                ip = req.getRemoteAddr();
            }
            record.setIp(ip);
        } catch (Exception ignore) {
        }
    }

    private String safeArgs(Object[] args) {
        if (args == null || args.length == 0) {
            return null;
        }
        try {
            String json = om.writeValueAsString(args);
            if (json.length() > PARAMS_MAX_LEN) {
                json = json.substring(0, PARAMS_MAX_LEN) + "...(truncated)";
            }
            return json;
        } catch (Exception e) {
            return "[unserializable]";
        }
    }
}
