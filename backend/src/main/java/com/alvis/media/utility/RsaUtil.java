package com.alvis.media.utility;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.crypto.Cipher;
import java.security.KeyFactory;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;


/**
 *@author 奇趣
 */
public class RsaUtil {
    /**
     * String to hold name of the encryption algorithm.
     */
    private static final String ALGORITHM = "RSA";

    private static final String CHAR_SET = "utf-8";

    private static final Logger logger = LoggerFactory.getLogger(RsaUtil.class);

    public static String rsaEncode(String publicCertificate, String text) {
        try {
            byte[] publicBytes = baseStrToByte(publicCertificate);
            X509EncodedKeySpec keySpec = new X509EncodedKeySpec(publicBytes);
            KeyFactory keyFactory = KeyFactory.getInstance(ALGORITHM);
            PublicKey pubKey = keyFactory.generatePublic(keySpec);
            // get an RSA cipher object and print the provider
            final Cipher cipher = Cipher.getInstance(ALGORITHM);
            // encrypt the plain text using the public key
            cipher.init(Cipher.ENCRYPT_MODE, pubKey);
            byte[] cipherBytes = cipher.doFinal(text.getBytes(CHAR_SET));
            return baseByteToStr(cipherBytes);
        } catch (Exception e) {
            logger.error("publicCertificate:{}  \r\n  text:{}", publicCertificate, text, e);
        }
        return null;
    }


    public static String rsaDecode(String privateCertificate, String text) {
        try {
            // 只记录密钥指纹，不记录密钥本身：便于排查"配置与数据是否同一密钥对"
            logger.debug("rsaDecode 使用私钥指纹={}", fingerprint(privateCertificate));
            byte[] privateBytes = baseStrToByte(privateCertificate);
            PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(privateBytes);
            KeyFactory keyFactory = KeyFactory.getInstance(ALGORITHM);
            PrivateKey priKey = keyFactory.generatePrivate(keySpec);
            byte[] cipherText;
            // get an RSA cipher object and print the provider
            final Cipher cipher = Cipher.getInstance(ALGORITHM);
            // encrypt the plain text using the public key
            cipher.init(Cipher.DECRYPT_MODE, priKey);
            byte[] textbyte = baseStrToByte(text);
            cipherText = cipher.doFinal(textbyte);
            return new String(cipherText, CHAR_SET);
        } catch (Exception e) {
            logger.error("privateCertificate:{}  \r\n  text:{}", privateCertificate, text, e);
        }
        return null;
    }


    /**
     * @param str str
     * @return byte[]
     */
    /**
     * 计算密钥字符串的 SHA-256 指纹（前 8 位十六进制）。
     * 用于日志中确认"当前使用的密钥"是哪一把，而不泄露密钥内容。
     */
    private static String fingerprint(String key) {
        if (key == null || key.trim().isEmpty()) {
            return "empty";
        }
        try {
            java.security.MessageDigest md = java.security.MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(key.trim().getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 4; i++) {
                sb.append(String.format("%02x", digest[i]));
            }
            return sb.toString();
        } catch (Exception e) {
            return "unknown";
        }
    }

    private static byte[] baseStrToByte(String str) {
        return Base64.getDecoder().decode(str);
    }


    /**
     * @param bytes bytes
     * @return String
     */
    private static String baseByteToStr(byte[] bytes) {
        return Base64.getEncoder().encodeToString(bytes);
    }
}
