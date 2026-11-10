# 报告中心（Report Center）— 技术规格

> 阶段 2 第 2 项。目标：把现有的「归因页同步生成 HTML 报告」升级为平台级报告中心——
> 报告落库可管理、与场景（Case）联动、带模型/数据版本信息、异步生成、可分享只读链接。

## 1. 现状结论（已探查确认）

| 现状 | 证据 |
|---|---|
| Python 报告脚本已存在 | `algorithm/attribution/build_report.py`：生成自包含 HTML 到 `data/reports/explain_%Y%m%d_%H%M%S.html`，stdout 输出 `{file,url,sizeKB,prediction,grade,...}`；CLI 参数 `--category/--fans/--hour/--weekday/--month/--model` |
| 静态暴露已有 | `WebMvcConfiguration`：`/reports/**` → `system.reports.dir`（`../data/reports`），noStore；但需登录（`anyRequest().authenticated()`） |
| 现有生成链路是同步、不留痕 | `AttributionServiceImpl.report(req)` 同步 `gateway.runCli(reportScript,args)`（默认 600s）；前端归因页「生成报告(HTML)」成功后 `window.open(url)`；**无列表/版本/分享/场景联动** |
| 任务中心可复用 | `JobServiceImpl.submit/runJob/dispatch`，已有 `data.import`/`model.drift`/`model.rehearsal` 三种类型；`@Lazy` 注入业务服务避免循环依赖（DriftService 模式） |
| 版本信息可取 | `ModelRegistryService.activeVersion(model)` 返回线上版本；注册表版本条目含 `dataVersion`、`featureVersion`（`findVersion` 目前为 private） |
| 归属隔离模式可复用 | `CaseServiceImpl.canAccess`：管理员全见，普通用户仅自己的 |
| 审计注解可复用 | `@OperationLog("模块.动作")` |
| 前端页面模式可复用 | `views/case/index.vue`：app-container > page-head > list-card > list-toolbar > el-table > list-footer(Pagination)；store `currentCase` getter；icon 可用 `pdf`（未被占用语义） |

**差距**：报告无实体表、无列表/详情/删除、无版本快照、无异步生成、无分享；生成是同步长请求。

## 2. 设计决策

### 2.1 数据表（V7__report.sql，幂等）

`t_report`：`id, name, report_type(default 'attribution'), case_id, case_name(快照), model, model_version, data_version, feature_version, params(JSON: category/fans/hour/weekday/month), status(GENERATING/DONE/FAILED 默认 GENERATING), file_name, file_path, size_kb, prediction, grade, error_msg, share_token(唯一), job_id, user_id, user_name, create_time, finish_time`。索引：`idx_report_user`、`idx_report_case`、`uk_report_share_token`。

### 2.2 后端（新建 7 文件 + 改 3 文件）

**新建**
1. `domain/Report.java` — MyBatis-Plus 实体（`@TableName("t_report")`，Lombok @Data，与 Case 同风格）
2. `repository/ReportMapper.java` — `extends BaseMapper<Report>`
3. `viewmodel/report/ReportGenerateRequestVM.java` — `{name?, caseId?, model?, videoCategory?, authorFans?, publishHour?, publishWeekday?, publishMonth?}`；caseId 与手动参数二选一，手动参数缺省时用场景值补齐
4. `service/ReportService.java` / `service/impl/ReportServiceImpl.java`：
   - `ObjectNode generate(vm)`：校验（caseId→`caseService.getOwn`，不存在抛 404；小时 0-23/星期 0-6/月 1-12/粉丝≥0 抛 400）；版本快照 = `registry.activeVersion(model)` + 新增 `activeVersionMeta(model)` 取 `dataVersion/featureVersion`；落行（GENERATING）；`jobService.submit("report.generate", {reportId})`；回写 `job_id`；返回 `{reportId, jobId}`
   - `JsonNode execute(jobId, paramsJson)`：任务回调。读行 → 用行内 params 拼 CLI 参数（中文类别 `URLEncoder.encode`，与 AttributionServiceImpl 一致）→ `gateway.runCli(reportScript, args, 900)` → 解析 `lastJsonLine` → 更新 DONE + fileName/filePath/sizeKb/prediction/grade/finishTime；异常则 FAILED + errorMsg 并 rethrow（让任务也标记失败）
   - `page(pageIndex,pageSize,name,status)`：归属隔离（复用 canAccess 模式）
   - `getOwn(id)` / `deleteOwn(id)`（删行 + 报告文件尽力删除，路径校验防穿越）
   - `share(id)`：已有 token 直接复用，否则 `UUID.randomUUID().toString().replace("-","")` 落库返回
   - `unshare(id)`：清空 token
   - `getShared(token)`：按 token 查，仅 DONE 返回，否则 null
   - `readContent(Report)`：从 `system.reports.dir` 读 `file_name`（normalize 后必须仍在目录内），文件缺失抛 404
5. `controller/ReportController.java` — `/api/report`，`extends BaseApiController`：
   - `POST /generate` `@OperationLog("report.generate")` → `{reportId, jobId}`
   - `GET /page`（name/status 可选）
   - `GET /{id}`（getOwn）
   - `DELETE /{id}` `@OperationLog("report.delete")`
   - `POST /{id}/share` `@OperationLog("report.share")` → `{token, url:"/api/report/shared/<token>"}`
   - `DELETE /{id}/share` `@OperationLog("report.unshare")`
   - `GET /{id}/content?download=1` → `ResponseEntity<byte[]>`，`text/html;charset=UTF-8`，inline/attachment（归属校验，仅 DONE）
   - `GET /shared/{token}?download=1` → 同上但匿名（token 即凭证；`/shared` 字面量路由优先于 `/{id}`，无冲突）

**修改**
6. `ModelRegistryService.java`：新增 `public JsonNode activeVersionMeta(String model)`（返回 active 版本条目，含 artifactExists + featureVersion 一致性校验，不满足返回 null）；`activeVersion` 改为基于它实现（行为不变）
7. `JobServiceImpl.java`：新增 `@Lazy ReportService` 依赖；`dispatch` 增加 `"report.generate"` 分支 → `reportService.execute(jobId, paramsJson)`
8. `application.yml`：`security-ignore-urls` 增加 `/api/report/shared/**`（分享链接免登录；其余 /api/report/** 仍需登录）
9. `algorithm/attribution/build_report.py`：增加可选 `--name`（输出文件名，防同秒并发撞名；缺省保持原时间戳命名，行为不变）；Java 侧传 `report_<id>.html`

### 2.3 前端（新建 2 文件 + 改 3 文件）

1. **`api/report.js`（新）**：`generate/page/get/remove/share/unshare`
2. **`views/report/index.vue`（新）— 报告中心页**：
   - page-head：标题「报告中心」+ 说明（与场景/版本联动）+ 主按钮「生成报告」
   - list-toolbar：名称搜索 + 状态筛选（生成中/已完成/失败）+ 总数
   - 表格列：名称（附类型 tag「归因」）、关联场景、模型/版本（model + modelVersion 短显）、数据版本、预测热度/等级、大小（KB)、状态（GENERATING=warning 转圈 / DONE=success / FAILED=danger+errorMsg tooltip）、创建人、创建时间、操作（预览/下载/分享/删除）
   - **生成对话框**：名称（选场景后自动 `归因报告 · <场景名>`，可改）；场景下拉（`caseApi.page({pageSize:100})` 加载 + 「不使用场景（手动输入）」）；选中场景显示参数摘要；未选场景显示手动参数表单（模型/类别/粉丝/小时/星期/月份，同场景编辑表单）；有 `currentCase` 时默认选中
   - **预览对话框**：`<iframe :src="`/api/report/${id}/content`">`（宽 100%、高 70vh）
   - **下载**：`window.open(`/api/report/${id}/content?download=1`)`
   - **分享对话框**：链接 = `location.origin + '/api/report/shared/' + token`；`navigator.clipboard.writeText` 复制（失败回退 el-input 手动全选）；内含「取消分享」按钮
   - **轮询**：列表含 GENERATING 行时启动 4s `setInterval`，逐行 `reportApi.get(id)` 更新（数组下标整体替换触发响应式）；全部终态后停表；`beforeUnmount` 清理
   - 删除：`$confirm` → `reportApi.remove` → 刷新
3. **`router.js`**：`/case` 之后新增 `/report` 路由块，`meta{title:'报告中心', icon:'pdf', group:'模型与归因', noCache:true}`
4. **`views/attribution/index.vue`**：`doReport` 改为走报告中心——payload 带 `caseId: currentCase?.id` + 当前表单参数 + 自动名称；提交后提示「已提交生成」并递归轮询（4s），DONE 后 `window.open(/api/report/<id>/content)` 并提示可在报告中心管理；FAILED 提示 errorMsg；按钮旁加「报告中心」跳转链接
5. **`api/attribution.js`**：删除不再使用的 `report` 方法（后端 `/api/attribution/report` 保留不动，零回归风险）

### 2.4 测试（新建 1 文件）

`backend/src/test/java/com/alvis/media/service/impl/ReportServiceImplTest.java`（Mockito 直构造，与 RehearsalServiceImplTest 同风格）：
1. `generate_withCase_createsRowWithVersionSnapshot`：mock 场景存在 + activeVersion/activeVersionMeta 返回版本与 dataVersion → 捕获 insert 的行断言（GENERATING、caseName、modelVersion、dataVersion）+ verify `jobService.submit("report.generate", …)`
2. `generate_caseNotFound_throws404`
3. `share_existingRow_generatesTokenPersisted`；`share_twice_reusesToken`
4. `getShared_notDone_returnsNull`
5. `deleteOwn_notOwner_throws404`

### 2.5 异常与安全约束

- 业务校验失败：`BusinessException(400/404)`（**禁止 401/402**）；队列满 429 由 jobService.submit 抛出
- `/api/report/shared/**` 免登录但 token 128bit 随机、仅 DONE、只读、不暴露列表；内容端点不缓存（ reports 静态映射本就 noStore；controller 返回不加缓存头由 Spring 默认处理）
- 文件读取做目录穿越校验（normalize 后必须位于 reports 目录内）
- 中文类别 CLI 参数 URLEncoder 编码（规避 Windows argv 编码问题，与现有实现一致）

## 3. 验收

1. `mvn compile` 通过
2. `mvn test`：现有 27 条全绿 + 新增 ReportServiceImplTest ≥5 条全绿
3. `build_report.py --name` 冒烟：`.venv/Scripts/python.exe algorithm/attribution/build_report.py --name smoke_test.html` 输出 JSON 且 file 字段为新名（跑通后删除产物）
4. 前端无 Node 环境，改动靠编辑回读校验；提示用户自行 `npm run build`
5. 主线走查（用户侧）：归因页「生成报告」→ 自动打开 → 报告中心可见（带版本/场景）→ 预览/下载/分享链接匿名可开

## 4. 明确不做

- 不改 `/api/attribution/report` 后端端点与 `/reports/**` 静态映射（兼容旧链路）
- 不做报告类型扩展（仅 attribution 一种；表结构预留 report_type）
- 不做分享链接过期/密码（仅 token，毕设口径足够）
- 不动 EDA/大屏等其他路线图项
