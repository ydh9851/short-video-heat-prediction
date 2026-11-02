package com.alvis.media.service.impl;

import com.alvis.media.configuration.property.PasswordKeyConfig;
import com.alvis.media.configuration.property.SystemConfig;
import com.alvis.media.domain.User;
import com.alvis.media.service.AuthenticationService;
import com.alvis.media.service.UserService;
import com.alvis.media.utility.RsaUtil;
import lombok.AllArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 *@author 奇趣
 */
@Service
@AllArgsConstructor
public class AuthenticationServiceImpl implements AuthenticationService {

    private static final Logger logger = LoggerFactory.getLogger(AuthenticationServiceImpl.class);

    private final UserService userService;

    private final SystemConfig systemConfig;


    /**
     * @param username username
     * @param password password
     * @return boolean
     */
    @Override
    public boolean authUser(String username, String password) {
        User user = userService.getUserByUserName(username);
        return authUser(user, username, password);
    }


    @Override
    public boolean authUser(User user, String username, String password) {
        if (user == null) {
            return false;
        }
        String encodePwd = user.getPassword();
        if (null == encodePwd || encodePwd.length() == 0) {
            return false;
        }
        // 私钥已外置到 application-local.yml / 环境变量；未配置时给出明确提示而不是抛 NPE
        if (!hasPwdKey()) {
            throw new IllegalStateException(
                    "未配置 RSA 私钥，无法校验密码：请先执行 python tools/gen_rsa_keys.py 生成密钥对");
        }
        String pwd = pwdDecode(encodePwd);
        if (pwd == null) {
            // 密钥与库中密文不匹配（如换过密钥对但未同步用户表），不能继续比对
            logger.warn("密码解密失败：私钥与用户表中的密文不匹配，请检查 RSA 密钥配置");
            return false;
        }
        return pwd.equals(password);
    }

    /** 是否已注入可用的 RSA 私钥。 */
    private boolean hasPwdKey() {
        PasswordKeyConfig key = systemConfig.getPwdKey();
        return key != null
                && key.getPrivateKey() != null && !key.getPrivateKey().trim().isEmpty()
                && key.getPublicKey() != null && !key.getPublicKey().trim().isEmpty();
    }

    @Override
    public String pwdEncode(String password) {
        return RsaUtil.rsaEncode(systemConfig.getPwdKey().getPublicKey(), password);
    }

    @Override
    public String pwdDecode(String encodePwd) {
        return RsaUtil.rsaDecode(systemConfig.getPwdKey().getPrivateKey(), encodePwd);
    }


}
