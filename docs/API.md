# 接口文档

> 本文件由 `python tools/docs/api_docs.py` 依据后端 OpenAPI 契约（`/v3/api-docs`）自动生成，共 **64** 个接口，分 **10** 组。

> 在线交互式文档（可直接试调）：`http://127.0.0.1:8000/swagger-ui/index.html`

> 系统：短视频热度预测与归因分析系统 API　版本：1.0.0

毕业设计 Web 系统的后端接口文档。覆盖热度预测、热度分级、可解释归因、17 类可复现实验、数据治理与模型治理六组能力。所有响应统一为 { code, message, response } 三字段结构，响应头携带 X-Trace-Id 便于在后端日志中定位。

所有响应统一为 `{ code, message, response }` 三字段结构；响应头 `X-Trace-Id` 可用于在后端日志中定位该次请求。

## 分组总览

| 分组 | 接口数 |
|---|---|
| 归因分析 | 4 |
| 数据治理 | 7 |
| 文件上传 | 16 |
| 模型治理 | 5 |
| 模型评估与实验 | 7 |
| 消息管理 | 2 |
| 热度分级 | 1 |
| 热度预测 | 7 |
| 用户管理 | 10 |
| 错误处理 | 5 |

## 归因分析

| 方法 | 路径 | 说明 | 参数 |
|---|---|---|---|
| `GET` | `/api/attribution/global` | — | — |
| `GET` | `/api/attribution/pdp` | — | feature(query) |
| `POST` | `/api/attribution/explain` | — | body(JSON) |
| `POST` | `/api/attribution/report` | — | body(JSON) |

## 数据治理

| 方法 | 路径 | 说明 | 参数 |
|---|---|---|---|
| `GET` | `/api/data/overview` | — | platform(query) |
| `GET` | `/api/data/platforms` | — | — |
| `GET` | `/api/data/quality` | — | platform(query) |
| `GET` | `/api/data/raw-files` | — | — |
| `GET` | `/api/data/samples` | — | platform(query)、page(query)、size(query)、category(query)、keyword(query) |
| `POST` | `/api/data/import` | — | platform(query,必填) |
| `POST` | `/api/data/upload` | — | platform(query,必填) |

## 文件上传

| 方法 | 路径 | 说明 | 参数 |
|---|---|---|---|
| `DELETE` | `/api/admin/upload/auth` | — | — |
| `DELETE` | `/api/admin/upload/configAndUpload` | — | — |
| `DELETE` | `/api/admin/upload/image` | — | — |
| `GET` | `/api/admin/upload/auth` | — | — |
| `GET` | `/api/admin/upload/configAndUpload` | — | — |
| `GET` | `/api/admin/upload/image` | — | — |
| `PATCH` | `/api/admin/upload/auth` | — | — |
| `PATCH` | `/api/admin/upload/configAndUpload` | — | — |
| `PATCH` | `/api/admin/upload/image` | — | — |
| `POST` | `/api/admin/upload/auth` | — | — |
| `POST` | `/api/admin/upload/configAndUpload` | — | — |
| `POST` | `/api/admin/upload/image` | — | — |
| `POST` | `/api/admin/upload/uploadVidoe` | — | SavePath(query,必填) |
| `PUT` | `/api/admin/upload/auth` | — | — |
| `PUT` | `/api/admin/upload/configAndUpload` | — | — |
| `PUT` | `/api/admin/upload/image` | — | — |

## 模型治理

| 方法 | 路径 | 说明 | 参数 |
|---|---|---|---|
| `GET` | `/api/models` | — | — |
| `GET` | `/api/models/shadow` | — | recent(query) |
| `POST` | `/api/models/sync` | — | — |
| `POST` | `/api/models/{model}/promote` | — | model(path,必填)、version(query,必填) |
| `POST` | `/api/models/{model}/rollback` | — | model(path,必填) |

## 模型评估与实验

| 方法 | 路径 | 说明 | 参数 |
|---|---|---|---|
| `GET` | `/api/evaluation/latest` | — | mode(query,必填) |
| `GET` | `/api/evaluation/modes` | — | — |
| `GET` | `/api/evaluation/runs` | — | limit(query) |
| `GET` | `/api/evaluation/task/{taskId}` | — | taskId(path,必填) |
| `GET` | `/api/evaluation/tasks` | — | — |
| `POST` | `/api/evaluation/run` | — | body(JSON) |
| `POST` | `/api/evaluation/submit` | — | body(JSON) |

## 消息管理

| 方法 | 路径 | 说明 | 参数 |
|---|---|---|---|
| `POST` | `/api/admin/message/page` | — | body(JSON) |
| `POST` | `/api/admin/message/send` | — | body(JSON) |

## 热度分级

| 方法 | 路径 | 说明 | 参数 |
|---|---|---|---|
| `GET` | `/api/grade` | — | k(query) |

## 热度预测

| 方法 | 路径 | 说明 | 参数 |
|---|---|---|---|
| `GET` | `/api/predict/engine` | — | — |
| `GET` | `/api/predict/logs` | — | page(query)、size(query) |
| `GET` | `/api/predict/metrics` | — | — |
| `GET` | `/api/predict/whatif` | — | dimension(query)、videoCategory(query)、authorFans(query)、publishHour(query)、publishWeekday(query)、publishMonth(query)、model(query) |
| `POST` | `/api/predict` | — | body(JSON) |
| `POST` | `/api/predict/batch` | — | body(JSON) |
| `POST` | `/api/predict/interval` | — | body(JSON) |

## 用户管理

| 方法 | 路径 | 说明 | 参数 |
|---|---|---|---|
| `POST` | `/api/admin/user/changeStatus/{id}` | — | id(path,必填) |
| `POST` | `/api/admin/user/current` | — | — |
| `POST` | `/api/admin/user/delete/{id}` | — | id(path,必填) |
| `POST` | `/api/admin/user/edit` | — | body(JSON) |
| `POST` | `/api/admin/user/event/page/list` | — | body(JSON) |
| `POST` | `/api/admin/user/getUserDetailByUserId/{id}` | — | id(path,必填) |
| `POST` | `/api/admin/user/page/list` | — | body(JSON) |
| `POST` | `/api/admin/user/select/{id}` | — | id(path,必填) |
| `POST` | `/api/admin/user/selectByUserName` | — | body(JSON) |
| `POST` | `/api/admin/user/update` | — | body(JSON) |

## 错误处理

| 方法 | 路径 | 说明 | 参数 |
|---|---|---|---|
| `DELETE` | `/error` | — | — |
| `GET` | `/error` | — | — |
| `PATCH` | `/error` | — | — |
| `POST` | `/error` | — | — |
| `PUT` | `/error` | — | — |
