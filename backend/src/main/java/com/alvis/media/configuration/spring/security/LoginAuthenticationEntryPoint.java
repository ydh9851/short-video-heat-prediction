package com.alvis.media.configuration.spring.security;

import com.alvis.media.base.SystemCode;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.authentication.LoginUrlAuthenticationEntryPoint;
import org.springframework.stereotype.Component;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * 未登录
 *@author 奇趣
 */
@Component
public final class LoginAuthenticationEntryPoint extends LoginUrlAuthenticationEntryPoint {

    public LoginAuthenticationEntryPoint() {
        super("/api/user/login");
    }

    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response,
                         AuthenticationException authException) throws IOException, ServletException {
        // 必须同时设置 HTTP 401，前端 axios 拦截器与网关/监控才能正确识别未登录
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        RestUtil.response(response, SystemCode.UNAUTHORIZED);
    }

}
