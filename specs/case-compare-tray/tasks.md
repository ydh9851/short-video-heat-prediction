# 场景对比托盘 — 任务清单

依据 `spec.md`。顺序执行，每步完成后勾选。

## 后端

- [x] T1 `CaseCompareRequestVM.java`：`ids` 列表
- [x] T2 `CaseService` + `CaseServiceImpl`：新增 `compare(ids)`，注入 `PredictService`
- [x] T3 对比逻辑：2~3 个、去重保序、归属校验、逐条 interval、单条失败降级
- [x] T4 `CaseController`：`POST /api/case/compare` + 操作日志
- [x] T5 `CaseServiceImplTest.java`：4 条单测

## 前端

- [x] T6 `api/case.js`：新增 `compare`
- [x] T7 `store/modules/caseCompare.js`：托盘状态 + localStorage + 上限 3
- [x] T8 `components/ScenarioCompareTray/index.vue`：悬浮托盘 + 对比弹窗（转置表格、差值、查看归因）
- [x] T9 `layout/index.vue`：挂载托盘组件
- [x] T10 `views/case/index.vue`：加入/移出对比操作

## 验证

- [x] T11 `mvn -q compile` 通过
- [x] T12 `mvn test` 全绿（43 条：原 39 + 新增 4）
- [x] T13 前端静态自查 + 提示用户执行 `npm run build`
