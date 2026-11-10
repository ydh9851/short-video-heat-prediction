package com.alvis.media.configuration.spring.exception;

import com.alvis.media.base.RestResponse;
import com.alvis.media.base.SystemCode;
import com.alvis.media.exception.BusinessException;
import com.alvis.media.utility.ErrorUtil;
import com.alvis.media.utility.TraceContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
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
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.util.stream.Collectors;

/**
 * 全局异常处理：区分「可预期的业务错误」与「未预期的系统故障」。
 *
 * <p>响应体协议保持不变（code + message，code===1 才成功），前端无需改动；
 * 同时为基础设施级错误返回语义化 HTTP 状态码（400/403/405/429/500），
 * 让网关、监控与浏览器网络面板能直接识别错误类型。
 *
 * <p>刻意保持 HTTP 200 的场景（前端依赖 body.code 做静默处理）：
 * <ul>
 *   <li>登录失败（body.code=402）：登录页自行提示「用户名或密码错误」；</li>
 *   <li>资源不存在（body.code=404）：实验任务轮询等场景静默处理，避免重复弹窗；</li>
 *   <li>业务校验失败（body.code 非 429）：各页面自行展示文案。</li>
 * </ul>
 */
@ControllerAdvice
public class ExceptionHandle {
    private final static Logger logger = LoggerFactory.getLogger(ExceptionHandle.class);

    /**
     * 兜底分支：未预期的系统故障。HTTP 500。
     * 原始 message 不回传（可能含 SQL、路径、类名），只给 traceId 供排查。
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<RestResponse> handleUnexpected(Exception e) {
        String traceId = TraceContext.current();
        logger.error("未预期异常 traceId={} {}", traceId, e.getMessage(), e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new RestResponse<>(SystemCode.InnerError.getCode(),
                        SystemCode.InnerError.getMessage() + "（traceId: " + traceId + "）"));
    }

    /**
     * 业务异常：HTTP 状态仅对「限流 429」语义化（让前端 axios 走 429 分支提示），
     * 其余保持 HTTP 200 + body.code，兼容页面级静默处理。
     */
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<RestResponse> handler(BusinessException e) {
        int code = e.getCode() == BusinessException.UNKNOWN_EXCEPTION
                ? SystemCode.InnerError.getCode() : e.getCode();
        logger.warn("业务异常 code={} message={}", code, e.getMessage());
        RestResponse body = new RestResponse<>(code, e.getMessage());
        if (code == 429) {
            return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS).body(body);
        }
        return ResponseEntity.ok(body);
    }

    /** 参数不合法：HTTP 400（调用方问题，语义上比 500 更准确）。body.code 保持 501 不变。 */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<RestResponse> handler(IllegalArgumentException e) {
        logger.warn("参数不合法: {}", e.getMessage());
        return ResponseEntity.badRequest()
                .body(new RestResponse<>(SystemCode.ParameterValidError.getCode(), e.getMessage()));
    }

    /** 运行状态异常：如「未配置 Python 脚本路径」，属部署/配置问题。 */
    @ExceptionHandler(IllegalStateException.class)
    public ResponseEntity<RestResponse> handler(IllegalStateException e) {
        logger.warn("运行状态异常: {}", e.getMessage());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(new RestResponse<>(SystemCode.InnerError.getCode(), e.getMessage()));
    }

    /** 资源不存在：保持 HTTP 200 + body.code=404（前端轮询场景静默处理）。 */
    @ExceptionHandler({UsernameNotFoundException.class, java.util.NoSuchElementException.class})
    public ResponseEntity<RestResponse> handleNotFound(RuntimeException e) {
        logger.warn("资源不存在: {}", e.getMessage());
        return ResponseEntity.ok(RestResponse.fail(404,
                e.getMessage() == null ? "请求的资源不存在" : e.getMessage()));
    }

    /** 认证失败：保持 HTTP 200 + body.code=402（登录页自行提示文案）。 */
    @ExceptionHandler(BadCredentialsException.class)
    public ResponseEntity<RestResponse> handleBadCredentials(BadCredentialsException e) {
        return ResponseEntity.ok(new RestResponse<>(SystemCode.AuthError.getCode(),
                SystemCode.AuthError.getMessage()));
    }

    /** 权限不足：HTTP 403（body.code 保持 502 不变，前端两个分支都会提示无权限）。 */
    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<RestResponse> handleAccessDenied(AccessDeniedException e) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .body(new RestResponse<>(SystemCode.AccessDenied.getCode(),
                        SystemCode.AccessDenied.getMessage()));
    }

    /** 请求体不可解析：HTTP 400。 */
    @ExceptionHandler({HttpMessageNotReadableException.class, MethodArgumentTypeMismatchException.class})
    public ResponseEntity<RestResponse> handleBadRequest(Exception e) {
        logger.warn("请求参数格式错误: {}", e.getMessage());
        return ResponseEntity.badRequest()
                .body(new RestResponse<>(SystemCode.ParameterValidError.getCode(),
                        "请求参数格式错误，请检查字段类型与取值范围"));
    }

    /** 请求方法不支持：HTTP 405。 */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<RestResponse> handleMethodNotSupported(HttpRequestMethodNotSupportedException e) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED)
                .body(RestResponse.fail(405, "不支持的请求方法：" + e.getMethod()));
    }

    /** Bean Validation 失败（@RequestBody）：HTTP 400。 */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<RestResponse> handler(MethodArgumentNotValidException e) {
        return ResponseEntity.badRequest()
                .body(new RestResponse<>(SystemCode.ParameterValidError.getCode(), formatErrors(e)));
    }

    /** Bean Validation 失败（表单 / Query）：HTTP 400。 */
    @ExceptionHandler(BindException.class)
    public ResponseEntity<RestResponse> handler(BindException e) {
        return ResponseEntity.badRequest()
                .body(new RestResponse<>(SystemCode.ParameterValidError.getCode(), formatErrors(e)));
    }

    private String formatErrors(BindException e) {
        return e.getBindingResult().getAllErrors().stream().map(file -> {
            FieldError fieldError = (FieldError) file;
            return ErrorUtil.parameterErrorFormat(fieldError.getField(), fieldError.getDefaultMessage());
        }).collect(Collectors.joining());
    }
}
