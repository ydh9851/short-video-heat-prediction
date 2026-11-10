# 部署

四个服务的编排文件在 `docker-compose.yml`，两个镜像定义在 `Dockerfile.backend` 与 `Dockerfile.engine`。

```bat
copy deploy\.env.example deploy\.env
docker compose -f deploy\docker-compose.yml --env-file deploy\.env up -d
```

启动后访问 http://127.0.0.1:8000/admin/index.html

完整部署说明（含本地开发方式、环境变量、常见问题与验收清单）见 [../docs/部署手册.md](../docs/部署手册.md)。