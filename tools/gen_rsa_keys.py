#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 RSA 密钥对并写入本地配置（application-local.yml）。

为什么需要这个脚本：
    登录链路用 RSA 对数据库中的密码密文做可逆解密（见 RsaUtil）。
    私钥一旦随仓库分发，等同于所有用户密码可被还原，因此私钥不入库。
    本脚本在本地生成一对新密钥，写入被 .gitignore 忽略的 application-local.yml。

用法：
    python tools/gen_rsa_keys.py                # 生成并写入 backend/src/main/resources/application-local.yml
    python tools/gen_rsa_keys.py --print-only   # 只打印密钥对，不写文件

依赖：
    pip install cryptography
"""
import argparse
import base64
import os
import sys

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
except ImportError:
    sys.exit("缺少依赖，请先执行： pip install cryptography")


def generate_keys(bits: int = 2048):
    """生成 RSA 密钥对，返回 (public_b64, private_b64)。

    格式与 Java 侧严格对应：
      - 公钥：X.509 SubjectPublicKeyInfo DER 的 Base64（对应 X509EncodedKeySpec）。
      - 私钥：PKCS#8（PrivateKeyInfo）DER 的 Base64（对应 PKCS8EncodedKeySpec）。
        注意：JDK 17 的 RSAKeyFactory 对 PKCS8EncodedKeySpec 严格按 PKCS#8 解析，
        不再回退支持 PKCS#1，因此必须产出 PKCS#8。
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    private_der = key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_der = key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return (
        base64.b64encode(public_der).decode("ascii"),
        base64.b64encode(private_der).decode("ascii"),
    )


def write_local_yaml(public_b64: str, private_b64: str, path: str):
    """写入本地配置；已存在则先备份为 .bak。"""
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    if os.path.exists(path):
        backup = path + ".bak"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(backup, "w", encoding="utf-8") as f:
            f.write(content)
        print("已备份原配置 -> %s" % backup)

    body = (
        "# 本地私有配置（已被 .gitignore 忽略，请勿提交到仓库）\n"
        "# 由 tools/gen_rsa_keys.py 生成\n"
        "system:\n"
        "  pwdKey:\n"
        "    publicKey: %s\n"
        "    privateKey: %s\n" % (public_b64, private_b64)
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    print("已写入 %s" % path)


def main():
    parser = argparse.ArgumentParser(description="生成登录链路用的 RSA 密钥对")
    parser.add_argument("--bits", type=int, default=2048, help="密钥长度，默认 2048")
    parser.add_argument("--print-only", action="store_true", help="只打印，不写文件")
    parser.add_argument(
        "--out",
        default=os.path.join("backend", "src", "main", "resources", "application-local.yml"),
        help="输出路径，默认 backend/src/main/resources/application-local.yml",
    )
    args = parser.parse_args()

    public_b64, private_b64 = generate_keys(args.bits)
    if args.print_only:
        print("RSA_PUBLIC_KEY=%s" % public_b64)
        print("RSA_PRIVATE_KEY=%s" % private_b64)
        return
    write_local_yaml(public_b64, private_b64, args.out)


if __name__ == "__main__":
    main()