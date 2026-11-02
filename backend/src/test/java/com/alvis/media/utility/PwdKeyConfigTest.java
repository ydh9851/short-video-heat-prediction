package com.alvis.media.utility;

import com.alvis.media.MediaApplication;
import com.alvis.media.configuration.property.SystemConfig;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * 密钥配置自检：确认 Spring 实际加载到的 RSA 密钥对是可用且相互匹配的。
 *
 * <p>密钥已外置到 application-local.yml（不入库）或环境变量，
 * 因此这条测试同时充当"部署是否正确配置密钥"的体检项。
 */
@SpringBootTest(classes = MediaApplication.class)
class PwdKeyConfigTest {

    @Autowired
    private SystemConfig systemConfig;

    @Test
    void keysAreLoadedAndConsistent() {
        assertNotNull(systemConfig.getPwdKey(), "未注入 system.pwdKey 配置");
        String publicKey = systemConfig.getPwdKey().getPublicKey();
        String privateKey = systemConfig.getPwdKey().getPrivateKey();
        assertNotNull(publicKey, "未配置 RSA 公钥（请执行 python tools/gen_rsa_keys.py）");
        assertNotNull(privateKey, "未配置 RSA 私钥（请执行 python tools/gen_rsa_keys.py）");
        assertFalse(publicKey.trim().isEmpty(), "RSA 公钥为空");
        assertFalse(privateKey.trim().isEmpty(), "RSA 私钥为空");

        // 用配置中的公钥加密、再用配置中的私钥解密，验证二者确实是一对
        String plain = "config-self-check";
        String encoded = RsaUtil.rsaEncode(publicKey, plain);
        assertNotNull(encoded, "RSA 加密失败，请检查公钥格式（应为 X.509 SPKI 的 Base64）");
        String decoded = RsaUtil.rsaDecode(privateKey, encoded);
        assertEquals(plain, decoded, "RSA 解密结果与原文不一致，请检查公私钥是否配对");
    }
}