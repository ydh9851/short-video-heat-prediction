package com.alvis.media.configuration.spring.exception;

import com.alvis.media.base.RestResponse;
import com.alvis.media.base.SystemCode;
import com.alvis.media.exception.BusinessException;
import com.alvis.media.utility.ErrorUtil;
import com.alvis.media.utility.TraceContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.util.stream.Collectors;

/**
 * 全局异常处理：区分「可预期的业务错误」与「未预期的系统故障」。
 *
 * <p>前者回传可读原因（如「不支持的平台：xxx」），
 * 后者只回通用文案并附 traceId，避免把实现细节（SQL 语句、文件路径、内部类名）暴露给前端。
 *
 * <p>traceId 同时写入响应头 {@code X-Trace-Id}（由 TraceIdFilter 负责），
 * 因此用户报错时可直接凭 traceId 在后端日志中定位到具体那一行。
 */
@ControllerAdvice
public class ExceptionHandle {
    private final static Logger logger = LoggerFactory.getLogger(ExceptionHandle.class);

    /**
     * 兜底分支：未预期的系统异常。
     * 原始 message 不再回传（可能含 SQL、路径、类名），只给 traceId 供排查。
     */
    @ExceptionHandler(Exception.class)
    @ResponseBody
    public RestResponse handleUnexpected(Exception e) {
        String traceId = TraceContext.current();
        logger.error("未预期异常 traceId={} {}", traceId, e.getMessage(), e);
        return new RestResponse<>(SystemCode.InnerError.getCode(),
                SystemCode.InnerError.getMessage() + "（traceId: " + traceId + "）");
    }

    /** 业务异常：显式抛出的可预期错误，保留其自带错误码与文案。 */
    @ExceptionHandler(BusinessException.class)
    @ResponseBody
    public RestResponse handler(BusinessException e) {
        int code = e.getCode() == BusinessException.UNKNOWN_EXCEPTION
                ? SystemCode.InnerError.getCode() : e.getCode();
        logger.warn("业务异常 code={} message={}", code, e.getMessage());
        return new RestResponse<>(code, e.getMessage());
    }

    /** 参数不合法：属于调用方问题，语义上比 500 更准确。 */
    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseBody
    public RestResponse handler(IllegalArgumentException e) {
        logger.warn("参数不合法: {}", e.getMessage());
        return new RestResponse<>(SystemCode.ParameterValidError.getCode(), e.getMessage());
    }

    /** 运行状态异常：如「未配置 Python 脚本路径」，属部署/配置问题，文案对运维有价值。 */
    @ExceptionHandler(IllegalStateException.class)
    @ResponseBody
    public RestResponse handler(IllegalStateException e) {
        logger.warn("运行状态异常: {}", e.getMessage());
        return new RestResponse<>(SystemCode.InnerError.getCode(), e.getMessage());
    }

    /** 资源不存在：返回 404，与「实验任务不存在」的既有语义一致。 */
    @ExceptionHandler({UsernameNotFoundException.class, java.util.NoSuchElementException.class})
    @ResponseBody
    public RestResponse handleNotFound(RuntimeException e) {
        logger.warn("资源不存在: {}", e.getMessage());
        return RestResponse.fail(404,
                e.getMessage() == null ? "请求的资源不存在" : e.getMessage());
    }

    /** 认证失败：用户名或密码错误。 */
    @ExceptionHandler(BadCredentialsException.class)
    @ResponseBody
    public RestResponse handleBadCredentials(BadCredentialsException e) {
        return new RestResponse<>(SystemCode.AuthError.getCode(), SystemCode.AuthError.getMessage());
    }

    /** 权限不足。 */
    @ExceptionHandler(AccessDeniedException.class)
    @ResponseBody
    public RestResponse handleAccessDenied(AccessDeniedException e) {
        return new RestResponse<>(SystemCode.AccessDenied.getCode(),
                SystemCode.AccessDenied.getMessage());
    }

    /** 请求体不可解析：JSON 格式错误、字段类型不匹配等。 */
    @ExceptionHandler({HttpMessageNotReadableException.class, MethodArgumentTypeMismatchException.class})
    @ResponseBody
    public RestResponse handleBadRequest(Exception e) {
        logger.warn("请求参数格式错误: {}", e.getMessage());
        return new RestResponse<>(SystemCode.ParameterValidError.getCode(),
                "请求参数格式错误，请检查字段类型与取值范围");
    }

    /** 请求方法不支持。 */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    @ResponseBody
    public RestResponse handleMethodNotSupported(HttpRequestMethodNotSupportedException e) {
        return RestResponse.fail(405, "不支持的请求方法：" + e.getMethod());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseBody
    public RestResponse handler(MethodArgumentNotValidException e) {
        String errorMsg = e.getBindingResult().getAllErrors().stream().map(file -> {
            FieldError fieldError = (FieldError) file;
            return ErrorUtil.parameterErrorFormat(fieldError.getField(), fieldError.getDefaultMessage());
        }).collect(Collectors.joining());
        return new RestResponse<>(SystemCode.ParameterValidError.getCode(), errorMsg);
    }

    @ExceptionHandler(BindException.class)
    @ResponseBody
    public RestResponse handler(BindException e) {
        String errorMsg = e.getBindingResult().getAllErrors().stream().map(file -> {
            FieldError fieldError = (FieldError) file;
            return ErrorUtil.parameterErrorFormat(fieldError.getField(), fieldError.getDefaultMessage());
        }).collect(Collectors.joining());
        return new RestResponse<>(SystemCode.ParameterValidError.getCode(), errorMsg);
    }


}
