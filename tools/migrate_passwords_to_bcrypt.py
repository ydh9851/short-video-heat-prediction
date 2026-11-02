#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 t_user 表中的密码从「RSA 密文」迁移为「BCrypt 单向哈希」。

背景：
    旧版本用 RSA 可逆加密存密码，私钥一旦泄露即可还原全部口令。
    现改为 BCrypt 单向哈希，但历史数据仍是 RSA 密文，需要一次性转换：
        RSA 私钥解密 -> 明文口令 -> BCrypt 哈希 -> 写回数据库

前置条件：
    1. 本机仍持有与库中密文配对的 RSA 私钥（application-local.yml 或环境变量）；
    2. 已安装 bcrypt、pymysql、cryptography。

用法：
    python tools/migrate_passwords_to_bcrypt.py --private-key-file <旧私钥文件>

注意：
    - 脚本只打印统计信息，不输出任何口令明文；
    - 迁移完成后会清理 Redis 中的 User::* 缓存，否则登录仍会读到旧密文。
"""
import argparse
import base64
import os
import sys

try:
    import bcrypt
    import pymysql
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    sys.exit("缺少依赖，请先执行： pip install bcrypt pymysql cryptography")

DEFAULT_LOCAL_YML = os.path.join("backend", "src", "main", "resources", "application-local.yml")


def read_private_key(private_b64: str):
    """加载 PKCS#8 私钥（Base64）。"""
    der = base64.b64decode(private_b64.strip())
    return serialization.load_der_private_key(der, password=None)


def read_private_key_from(path: str) -> str:
    """从 application-local.yml 中读取 privateKey。"""
    if not os.path.exists(path):
        sys.exit("找不到 %s" % path)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "privateKey:" in line:
                return line.split("privateKey:", 1)[1].strip()
    sys.exit("%s 中未找到 privateKey" % path)


def is_bcrypt(value: str) -> bool:
    return value.startswith(("$2a$", "$2b$", "$2y$"))


def clear_user_cache(host: str, port: int):
    """清理用户缓存：改了库里的密码但不清缓存，登录读到的仍是旧值。"""
    try:
        import redis
    except ImportError:
        print("  [提示] 未安装 redis 客户端，跳过缓存清理")
        return
    try:
        client = redis.Redis(host=host, port=port, protocol=2)
        keys = list(client.keys("User::*"))
        if keys:
            client.delete(*keys)
        print("已清理用户缓存 %d 个键" % len(keys))
    except Exception as exc:
        print("  [提示] 清理缓存失败（%s），如登录异常请手动清理 Redis 中 User::* 键" % exc)


def main():
    parser = argparse.ArgumentParser(description="把用户密码从 RSA 密文迁移为 BCrypt 哈希")
    parser.add_argument("--private-key-file", default=None, help="RSA 私钥文件（Base64 文本）")
    parser.add_argument("--local-yml", default=DEFAULT_LOCAL_YML, help="从该文件读取 RSA 私钥")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="123456")
    parser.add_argument("--database", default="short_video_heat_db")
    parser.add_argument("--redis-host", default="127.0.0.1")
    parser.add_argument("--redis-port", type=int, default=6379)
    args = parser.parse_args()

    if args.private_key_file:
        with open(args.private_key_file, "r", encoding="utf-8") as f:
            key_b64 = f.read()
    else:
        key_b64 = read_private_key_from(args.local_yml)
    key = read_private_key(key_b64)

    conn = pymysql.connect(host=args.host, port=args.port, user=args.user,
                           password=args.password, database=args.database, charset="utf8mb4")
    ok, skipped, fail = 0, 0, 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, user_name, password FROM t_user")
            for uid, uname, stored in cur.fetchall():
                if is_bcrypt(stored):
                    skipped += 1
                    continue
                try:
                    plain = key.decrypt(base64.b64decode(stored), padding.PKCS1v15())
                    hashed = bcrypt.hashpw(plain, bcrypt.gensalt(rounds=10)).decode("ascii")
                    cur.execute("UPDATE t_user SET password = %s WHERE id = %s", (hashed, uid))
                    ok += 1
                except Exception as exc:
                    print("  用户 %s(id=%s) 迁移失败：%s" % (uname, uid, exc))
                    fail += 1
        conn.commit()
    finally:
        conn.close()

    print("迁移完成：成功 %d 条，已是 BCrypt 跳过 %d 条，失败 %d 条" % (ok, skipped, fail))
    if ok:
        clear_user_cache(args.redis_host, args.redis_port)
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()