package com.alvis.media.configuration.spring.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * 密码编码器配置。
 *
 * <p>系统把用户密码以 <b>BCrypt 单向哈希</b> 存储（而非可逆加密）：
 * 数据库即便泄露，攻击者也无法反推出明文密码；BCrypt 自带随机盐，
 * 相同口令每次哈希结果不同，可有效抵御彩虹表与批量爆破。
 *
 * <p>代价是密码无法反解——忘记密码只能重置，不能找回。
 */
@Configuration
public class PasswordConfig {

    /**
     * 强度 10：约 2^10 次迭代，在本机登录场景下耗时约 50~100ms，
     * 对离线爆破有足够抵抗力，又不会让用户感到明显迟滞。
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(10);
    }
}