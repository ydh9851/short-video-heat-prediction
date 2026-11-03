package com.alvis.media.service.impl;

import com.alvis.media.domain.User;
import com.alvis.media.service.AuthenticationService;
import com.alvis.media.service.UserService;
import lombok.AllArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

/**
 * 认证服务实现。
 *
 * <p><b>密码存储方案：BCrypt 单向哈希。</b>
 * 早期版本用 RSA 对密码做可逆加密后存库（前端并未使用该加密，仅存储环节依赖），
 * 存在两个问题：私钥一旦泄露即可还原全部密码；且加密算法对数据库泄露没有防护作用。
 * 现改为 BCrypt：
 * <ul>
 *   <li>存储不可逆，库泄露也无法反推明文；</li>
 *   <li>自带随机盐，相同口令哈希结果不同；</li>
 *   <li>校验用 {@code matches}，库中不出现任何明文。</li>
 * </ul>
 *
 * @author 奇趣
 */
@Service
@AllArgsConstructor
public class AuthenticationServiceImpl implements AuthenticationService {

    private static final Logger logger = LoggerFactory.getLogger(AuthenticationServiceImpl.class);

    private final UserService userService;

    private final PasswordEncoder passwordEncoder;

    /**
     * 校验用户名与密码。
     *
     * @param username 用户名
     * @param password 明文密码（前端经 HTTPS 传输）
     * @return 是否匹配
     */
    @Override
    public boolean authUser(String username, String password) {
        User user = userService.getUserByUserName(username);
        return authUser(user, username, password);
    }

    @Override
    public boolean authUser(User user, String username, String password) {
        if (user == null || password == null) {
            return false;
        }
        String stored = user.getPassword();
        if (stored == null || stored.trim().isEmpty()) {
            return false;
        }
        if (!isBcrypt(stored)) {
            // 兼容旧库：历史数据为 RSA 密文，需先执行迁移脚本转成 BCrypt
            logger.warn("用户 {} 的密码仍为旧格式（非 BCrypt），"
                    + "请执行 tools/ops/migrate_passwords_to_bcrypt.py 完成迁移", username);
            return false;
        }
        return passwordEncoder.matches(password, stored);
    }

    /**
     * 计算密码哈希（新增 / 修改用户时使用）。
     */
    @Override
    public String pwdEncode(String password) {
        return passwordEncoder.encode(password);
    }

    /**
     * BCrypt 是单向哈希，无法解密；此方法仅为兼容旧接口而保留。
     *
     * @deprecated 密码不可逆，请改用 {@link #pwdEncode(String)} 与 {@code PasswordEncoder.matches}
     */
    @Override
    @Deprecated
    public String pwdDecode(String endodePwd) {
        return null;
    }

    /** 判断库中的密码是否已是 BCrypt 格式（$2a$ / $2b$ / $2y$ 开头）。 */
    private boolean isBcrypt(String stored) {
        return stored.startsWith("$2a$") || stored.startsWith("$2b$") || stored.startsWith("$2y$");
    }
}