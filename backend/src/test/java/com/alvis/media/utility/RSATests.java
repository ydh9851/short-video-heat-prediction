package com.alvis.media.utility;

import org.junit.jupiter.api.Test;

import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.util.Base64;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 登录密码 RSA 加解密往返测试。
 *
 * <p>本测试自生成密钥对，不依赖 Spring 配置：RSA 私钥已外置到 application-local.yml
 * 或环境变量，测试不应因本地是否生成过密钥而失败。
 */
class RSATests {

    /** 生成一对临时 RSA 密钥，格式与配置文件中的一致（PKCS8 私钥 / X509 公钥，Base64 编码）。 */
    private static String[] generateKeyPair() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        KeyPair pair = generator.generateKeyPair();
        String publicKey = Base64.getEncoder().encodeToString(pair.getPublic().getEncoded());
        String privateKey = Base64.getEncoder().encodeToString(pair.getPrivate().getEncoded());
        return new String[]{publicKey, privateKey};
    }

    @Test
    void rsaEncodeDecodeRoundTrip() throws Exception {
        String[] keys = generateKeyPair();
        String pwd = "123456";
        String encoded = RsaUtil.rsaEncode(keys[0], pwd);
        assertNotNull(encoded);
        assertTrue(encoded.length() > 0);
        String decoded = RsaUtil.rsaDecode(keys[1], encoded);
        assertEquals(pwd, decoded);
    }

    @Test
    void cipherTextDiffersFromPlainText() throws Exception {
        String[] keys = generateKeyPair();
        String encoded = RsaUtil.rsaEncode(keys[0], "my-secret-password");
        assertTrue(!encoded.contains("my-secret-password"));
    }
}