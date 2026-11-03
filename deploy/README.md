# 部署说明

整套系统由四个服务组成，一条命令即可拉起：

```
MySQL 8.4   数据库与种子数据
Redis 7     会话缓存与模型注册表缓存
engine      常驻算法服务（FastAPI + LightGBM，端口 8100）
backend     Spring Boot 应用（同时伺服前端静态资源，端口 8000）
```

## 一、快速开始

```bat
copy deploy\.env.example deploy\.env
docker compose -f deploy\docker-compose.yml --env-file deploy\.env up -d
```

首次执行会构建镜像（前端 + 后端 + 算法依赖），需要网络，耗时较长；
之后再次执行只需十几秒。构建完成后访问：

- 系统首页：<http://127.0.0.1:8000/admin/index.html>
- 接口文档：<http://127.0.0.1:8000/swagger-ui/index.html>
- 健康检查：<http://127.0.0.1:8000/actuator/health>

查看状态与日志：

```bat
docker compose -f deploy\docker-compose.yml ps
docker compose -f deploy\docker-compose.yml logs -f backend
```

停止与清理：

```bat
docker compose -f deploy\docker-compose.yml down          :: 停止，保留数据卷
docker compose -f deploy\docker-compose.yml down -v       :: 停止并删除数据卷（会清空数据库）
```

## 二、启动顺序如何保证

`depends_on` 配合 `condition: service_healthy`，因此是「MySQL / Redis 就绪 → 引擎健康 → 后端启动」。
这样不会出现「后端先连库失败」或「引擎还没起来就收到推理请求」。

后端对引擎的依赖其实是可选的：引擎不可用时会自动熔断并降级回 CLI 通道，
只是响应从 34ms 变成数秒（首次要加载模型）。

## 三、目录与配置约定

容器内目录结构与本地一致：

```
/app/backend/app.jar    后端应用（工作目录）
/app/algorithm/         算法脚本
/app/data/              数据集
```

因此配置里的 `../algorithm/...` 这类相对路径在本地与容器中含义相同，
不需要为容器另写一套配置。引擎地址是唯一例外——容器内不能用 `127.0.0.1`，
通过 `ENGINE_SERVICE_URL=http://engine:8100` 注入。

## 四、数据初始化

首次启动时 MySQL 会自动执行 `sql/` 下的两个脚本：

| 脚本 | 作用 |
|---|---|
| `short_video_heat_db.sql` | 建库、建表、写入种子数据（含 admin 账号） |
| `migration_heat_predict_log.sql` | 预测日志表的结构迁移 |

数据卷 `mysql-data` 会保留，**重启容器不会丢数据**；只有 `down -v` 才会清除。

默认管理员账号见 `sql/short_video_heat_db.sql` 中的 `t_user` 表，
密码为 BCrypt 密文；如需重置：

```bat
docker compose -f deploy\docker-compose.yml exec backend python /app/algorithm/../tools/ops/reset_user_password.py --user admin --password 新密码
```

## 五、常见问题

| 现象 | 原因与处理 |
|---|---|
| 后端日志报「未配置脚本」 | `SPRING_PROFILES_ACTIVE` 未设为 `prod`，导致没加载 `application-prod.yml` 里的脚本路径 |
| 预测报「引擎不可用」 | 引擎未就绪；系统会自动降级到 CLI 通道，功能正常但响应变慢 |
| 中文图表显示方框 | 镜像缺少中文字体；两个 Dockerfile 都已安装 `fonts-wqy-zenhei` |
| 端口被占用 | 改 `deploy/.env` 里的 `BACKEND_PORT` |
| 首次构建很慢 | 需要下载基础镜像与 npm / maven 依赖；后续构建有缓存 |

## 六、与本地开发方式的关系

本文件描述的是「给别人一台干净机器」的用法。本地开发仍用仓库根目录的三个脚本：

| 脚本 | 作用 |
|---|---|
| `setup_venv.cmd` | 创建 Python 虚拟环境并安装依赖 |
| `run_engine_service.cmd` | 启动常驻算法引擎（8100） |
| `restart_backend.cmd` | 编译并启动后端（8000） |