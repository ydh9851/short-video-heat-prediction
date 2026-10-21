package com.alvis.media.configuration.spring.security;

import com.alvis.media.base.SystemCode;
import com.alvis.media.domain.User;
import com.alvis.media.domain.UserEventLog;
import com.alvis.media.event.UserEvent;
import com.alvis.media.service.UserService;
import lombok.AllArgsConstructor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.security.core.Authentication;
import org.springframework.security.web.authentication.logout.SimpleUrlLogoutSuccessHandler;
import org.springframework.stereotype.Component;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.Date;

/**
 * 用户登出
 *
 *@author 奇趣
 */
@Component
@AllArgsConstructor
public class RestLogoutSuccessHandler extends SimpleUrlLogoutSuccessHandler {

    private final ApplicationEventPublisher eventPublisher;
    private final UserService userService;

    @Override
    public void onLogoutSuccess(HttpServletRequest request, HttpServletResponse response, Authentication authentication) {
        // authentication 可能为 null（未登录 / session 已失效时调用登出），需做空指针保护
        if (null != authentication && authentication.getPrincipal() instanceof org.springframework.security.core.userdetails.User) {
            org.springframework.security.core.userdetails.User springUser =
                    (org.springframework.security.core.userdetails.User) authentication.getPrincipal();
            User user = userService.getUserByUserName(springUser.getUsername());
            if (null != user) {
                UserEventLog userEventLog = new UserEventLog(user.getId(), user.getUserName(), user.getRealName(), new Date());
                userEventLog.setContent(user.getUserName() + " 登出了短视频热度预测与归因分析系统");
                eventPublisher.publishEvent(new UserEvent(userEventLog));
            }
        }
        RestUtil.response(response, SystemCode.OK);
    }
}
