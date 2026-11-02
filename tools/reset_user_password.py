#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重置系统用户的登录密码（用 application-local.yml 中的 RSA 公钥重新加密）。

用途：
    密钥对更换、或用户表中的密文与当前私钥不匹配时，
    用本脚本把指定账号的密码重置为已知值，保证演示与答辩时能正常登录。

用法：
    python tools/reset_user_password.py --user admin --password 123456
"""
import argparse
import base64
import os
import sys

try:
    import pymysql
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:
    sys.exit("缺少依赖，请先执行： pip install pymysql cryptography")

DEFAULT_LOCAL_YML = os.path.join("backend", "src", "main", "resources", "application-local.yml")


def read_public_key(path: str) -> str:
    if not os.path.exists(path):
        sys.exit("找不到 %s，请先执行 python tools/gen_rsa_keys.py" % path)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if "publicKey:" in line:
                return line.split("publicKey:", 1)[1].strip()
    sys.exit("%s 中未找到 publicKey" % path)


def main():
    parser = argparse.ArgumentParser(description="重置用户登录密码")
    parser.add_argument("--user", required=True, help="用户名")
    parser.add_argument("--password", required=True, help="新密码（明文）")
    parser.add_argument("--local-yml", default=DEFAULT_LOCAL_YML)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--db-user", default="root")
    parser.add_argument("--db-password", default="123456")
    parser.add_argument("--database", default="short_video_heat_db")
    args = parser.parse_args()

    from cryptography.hazmat.primitives import serialization
    der = base64.b64decode(read_public_key(args.local_yml))
    pub = serialization.load_der_public_key(der)
    cipher_b64 = base64.b64encode(pub.encrypt(args.password.encode("utf-8"), padding.PKCS1v15())).decode("ascii")

    conn = pymysql.connect(host=args.host, port=args.port, user=args.db_user,
                           password=args.db_password, database=args.database, charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE t_user SET password = %s WHERE user_name = %s", (cipher_b64, args.user))
            affected = cur.rowcount
        conn.commit()
    finally:
        conn.close()

    if affected == 0:
        sys.exit("未找到用户：%s" % args.user)
    print("已重置用户 %s 的密码（影响 %d 条记录）" % (args.user, affected))


if __name__ == "__main__":
    main()