#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重置系统用户的登录密码（写入 BCrypt 哈希）。

背景：密码以 BCrypt 单向哈希存储，无法反解，忘记密码只能重置。

用法：
    python tools/reset_user_password.py --user admin --password 123456
"""
import argparse
import sys

try:
    import bcrypt
    import pymysql
except ImportError:
    sys.exit("缺少依赖，请先执行： pip install bcrypt pymysql")


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
    parser = argparse.ArgumentParser(description="重置用户登录密码（BCrypt）")
    parser.add_argument("--user", required=True, help="用户名")
    parser.add_argument("--password", required=True, help="新密码（明文）")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--db-user", default="root")
    parser.add_argument("--db-password", default="123456")
    parser.add_argument("--database", default="short_video_heat_db")
    parser.add_argument("--redis-host", default="127.0.0.1")
    parser.add_argument("--redis-port", type=int, default=6379)
    args = parser.parse_args()

    hashed = bcrypt.hashpw(args.password.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("ascii")

    conn = pymysql.connect(host=args.host, port=args.port, user=args.db_user,
                           password=args.db_password, database=args.database, charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE t_user SET password = %s WHERE user_name = %s", (hashed, args.user))
            affected = cur.rowcount
        conn.commit()
    finally:
        conn.close()

    if affected == 0:
        sys.exit("未找到用户：%s" % args.user)
    print("已重置用户 %s 的密码（影响 %d 条记录）" % (args.user, affected))
    clear_user_cache(args.redis_host, args.redis_port)


if __name__ == "__main__":
    main()