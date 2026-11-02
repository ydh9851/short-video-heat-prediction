#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 t_user 表中的密码密文从旧 RSA 密钥对迁移到新密钥对（保持明文密码不变）。

背景：
    登录链路用 RSA 对数据库里的密码做可逆解密。私钥外置到本地后，
    换密钥对会导致库中密文无法解密、所有人登录失败。
    本脚本用「旧私钥解密 → 新公钥重新加密」的方式平滑迁移，用户无感知。

用法：
    python tools/reencrypt_user_passwords.py --old-private-key-file <旧私钥文件>
    # 新公钥默认从 backend/src/main/resources/application-local.yml 读取

注意：
    - 旧私钥请放在仓库之外（如临时目录），迁移完成后立即删除；
    - 脚本只输出统计信息，不打印任何密码明文。
"""
import argparse
import base64
import os
import sys

try:
    import pymysql
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
except ImportError:
    sys.exit("缺少依赖，请先执行： pip install pymysql cryptography")

DEFAULT_LOCAL_YML = os.path.join("backend", "src", "main", "resources", "application-local.yml")


def load_private_key(b64: str):
    """加载 PKCS#1 私钥（Base64）。"""
    der = base64.b64decode(b64.strip())
    return serialization.load_der_private_key(der, password=None)


def load_public_key(b64: str):
    """加载 X.509 SubjectPublicKeyInfo 公钥（Base64）。"""
    der = base64.b64decode(b64.strip())
    return serialization.load_der_public_key(der)


def read_new_public_key(path: str) -> str:
    """从 application-local.yml 中读取 publicKey。"""
    if not os.path.exists(path):
        sys.exit("找不到 %s，请先执行 python tools/gen_rsa_keys.py 生成密钥对" % path)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "publicKey:" in line:
                return line.split("publicKey:", 1)[1].strip()
    sys.exit("%s 中未找到 publicKey" % path)


def clear_user_cache(host: str, port: int):
    """清理 Redis 中的用户缓存。

    必须执行这一步：UserService 对用户对象做了 @Cacheable 缓存，
    改了数据库里的密码密文但不清缓存，登录时读到的仍是旧密文，
    会表现为"密码明明正确却提示用户名或密码错误"。
    """
    try:
        import redis
    except ImportError:
        print("  [提示] 未安装 redis 客户端，跳过缓存清理；"
              "如登录异常请手动清理 Redis 中 User::* 键")
        return
    try:
        client = redis.Redis(host=host, port=port, protocol=2)
        keys = list(client.keys("User::*"))
        if keys:
            client.delete(*keys)
        print("已清理用户缓存 %d 个键" % len(keys))
    except Exception as exc:
        print("  [提示] 清理缓存失败（%s）；如登录异常请手动清理 Redis 中 User::* 键" % exc)


def main():
    parser = argparse.ArgumentParser(description="迁移 t_user 密码密文到新的 RSA 密钥对")
    parser.add_argument("--old-private-key-file", required=True, help="旧私钥文件（Base64 文本）")
    parser.add_argument("--local-yml", default=DEFAULT_LOCAL_YML, help="新公钥所在配置文件")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="123456")
    parser.add_argument("--database", default="short_video_heat_db")
    parser.add_argument("--redis-host", default="127.0.0.1")
    parser.add_argument("--redis-port", type=int, default=6379)
    args = parser.parse_args()

    with open(args.old_private_key_file, "r", encoding="utf-8") as f:
        old_key = load_private_key(f.read())
    new_pub = load_public_key(read_new_public_key(args.local_yml))

    conn = pymysql.connect(host=args.host, port=args.port, user=args.user,
                           password=args.password, database=args.database,
                           charset="utf8mb4")
    ok, fail = 0, 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, user_name, password FROM t_user")
            rows = cur.fetchall()
            for uid, uname, cipher_b64 in rows:
                try:
                    plain = old_key.decrypt(base64.b64decode(cipher_b64), padding.PKCS1v15())
                    new_cipher = new_pub.encrypt(plain, padding.PKCS1v15())
                    cur.execute("UPDATE t_user SET password = %s WHERE id = %s",
                                (base64.b64encode(new_cipher).decode("ascii"), uid))
                    ok += 1
                except Exception as exc:
                    print("  用户 %s(id=%s) 迁移失败：%s" % (uname, uid, exc))
                    fail += 1
        conn.commit()
    finally:
        conn.close()

    print("迁移完成：成功 %d 条，失败 %d 条" % (ok, fail))
    if ok:
        clear_user_cache(args.redis_host, args.redis_port)
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()