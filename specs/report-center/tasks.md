# 报告中心 — 任务清单

依据 `spec.md`。顺序执行，每步完成后勾选。

## 后端

- [x] T1 `V7__report.sql`：t_report 建表（幂等 CREATE TABLE IF NOT EXISTS，含 uk_report_share_token 唯一索引）
- [x] T2 `domain/Report.java` + `repository/ReportMapper.java`
- [x] T3 `viewmodel/report/ReportGenerateRequestVM.java`
- [x] T4 `ModelRegistryService`：新增 `activeVersionMeta(String model)`，activeVersion 复用（行为不变）
- [x] T5 `service/ReportService.java` + `impl/ReportServiceImpl.java`：generate/execute/page/getOwn/deleteOwn/share/unshare/getShared/readContent
- [x] T6 `controller/ReportController.java`：/api/report 8 个端点（generate/page/{id}/delete/share/unshare/{id}/content/shared/{token}）
- [x] T7 `JobServiceImpl`：dispatch 增加 "report.generate" 分支（@Lazy ReportService）
- [x] T8 `application.yml`：security-ignore-urls 增加 `/api/report/shared/**`
- [x] T9 `build_report.py`：可选 `--name` 参数（缺省行为不变）
- [x] T10 `ReportServiceImplTest.java`：≥5 条单测（generate 版本快照/场景不存在 404/share token 复用/getShared 非 DONE/deleteOwn 非属主）——实际 7 条全绿

## 前端

- [x] T11 `api/report.js`
- [x] T12 `views/report/index.vue`：报告中心页（列表/生成对话框带场景联动/iframe 预览/下载/分享/删除/GENERATING 轮询）
- [x] T13 `router.js`：/report 路由（group 模型与归因，icon pdf）
- [x] T14 `views/attribution/index.vue`：doReport 改走报告中心（带 currentCase）+ 报告中心入口；`api/attribution.js` 删除 report 方法

## 验证

- [x] T15 `mvn compile` + `mvn test`（34 条全绿：27 存量 + 7 新增）+ `build_report.py --name` 冒烟通过（产物已清理）
