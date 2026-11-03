# tools —— 开发与运维脚本

按用途分三组，每组自包含说明文档。

| 目录 | 用途 | 脚本 |
|---|---|---|
| `dev/` | 本机开发环境辅助 | `git-proxy-on.cmd`、`git-proxy-off.cmd`、`git-proxy-status.cmd`（详见 `dev/README.md`） |
| `ops/` | 账号与密码运维 | `reset_user_password.py`（重置登录口令）、`migrate_passwords_to_bcrypt.py`（历史口令迁移为 BCrypt） |
| `docs/` | 文档生成 | `api_docs.py`（依据运行时 OpenAPI 契约生成 `docs/API.md`） |

## 常用命令

```bat
:: 重置 admin 口令
.venv\Scripts\python.exe tools\ops\reset_user_password.py --user admin --password 123456

:: 重新生成接口文档（需后端已启动）
.venv\Scripts\python.exe tools\docs\api_docs.py

:: 诊断 Git 代理并一键切换
tools\dev\git-proxy-status.cmd
tools\dev\git-proxy-on.cmd
tools\dev\git-proxy-off.cmd
```

## 约定

- 脚本一律输出单行 JSON 或纯文本，便于命令行与 Java 端解析；
- 涉及写库的脚本在写库后会自动清理 Redis 中的 `User::*` 缓存——
  改了口令但缓存未失效时，登录会读到旧值；
- 脚本不在运行时依赖 Spring 上下文，可单独执行。