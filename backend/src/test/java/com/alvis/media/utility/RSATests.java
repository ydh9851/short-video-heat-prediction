package com.alvis.media.utility;

import com.alvis.media.MediaApplication;
import com.alvis.media.configuration.property.SystemConfig;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.assertEquals;

/** 登录密码 RSA 加解密往返测试（Spring Boot 3.5 只带 JUnit5，原 JUnit4 写法无法编译）。 */
@SpringBootTest(classes = MediaApplication.class)
class RSATests {

    @Autowired
    private SystemConfig systemConfig;

    @Test
    void rsaEncodeDecodeRoundTrip() {
        String pwd = "123456";
        String encoded = RsaUtil.rsaEncode(systemConfig.getPwdKey().getPublicKey(), pwd);
        String decoded = RsaUtil.rsaDecode(systemConfig.getPwdKey().getPrivateKey(), encoded);
        assertEquals(pwd, decoded);
    }
}
