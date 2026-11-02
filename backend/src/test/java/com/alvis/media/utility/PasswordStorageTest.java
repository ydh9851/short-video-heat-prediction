package com.alvis.media.utility;

import com.alvis.media.MediaApplication;
import com.alvis.media.domain.User;
import com.alvis.media.service.UserService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.crypto.password.PasswordEncoder;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 密码存储自检：确认库中的口令以 BCrypt 单向哈希保存，且能被正确校验。
 *
 * <p>这是一条"部署体检"用例：若有人把口令改回明文或可逆密文，这里会立刻失败。
 */
@SpringBootTest(classes = MediaApplication.class)
class PasswordStorageTest {

    @Autowired
    private UserService userService;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Test
    void passwordIsStoredAsBcryptHash() {
        User user = userService.getUserByUserName("admin");
        assertNotNull(user, "数据库中应存在 admin 账号");
        String stored = user.getPassword();
        assertNotNull(stored);
        assertTrue(stored.startsWith("$2a$") || stored.startsWith("$2b$") || stored.startsWith("$2y$"),
                "密码必须以 BCrypt 哈希存储，实际为：" + stored.substring(0, Math.min(12, stored.length())) + "…");
    }

    @Test
    void correctPasswordMatches() {
        User user = userService.getUserByUserName("admin");
        assertNotNull(user);
        assertTrue(passwordEncoder.matches("123456", user.getPassword()),
                "正确口令应校验通过（若失败请检查是否执行过密码重置脚本）");
    }

    @Test
    void wrongPasswordDoesNotMatch() {
        User user = userService.getUserByUserName("admin");
        assertNotNull(user);
        assertTrue(!passwordEncoder.matches("wrong-password", user.getPassword()));
    }

    @Test
    void samePasswordHashesDifferently() {
        /** BCrypt 自带随机盐：相同口令两次哈希结果必须不同。 */
        String first = passwordEncoder.encode("same-password");
        String second = passwordEncoder.encode("same-password");
        assertNotNull(first);
        assertTrue(!first.equals(second), "相同口令的两次哈希不应相同（随机盐失效）");
        assertTrue(passwordEncoder.matches("same-password", first), "哈希应能被正确校验");
    }
}