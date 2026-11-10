# 数据集版本 / 血缘页 — 任务清单

依据 `spec.md`。顺序执行，每步完成后勾选。

## 后端

- [x] T1 `DataService.java`：新增 `JsonNode lineage(String platform)`
- [x] T2 `DataServiceImpl.java`：新增 `versionsPath` 配置、注入 `ModelRegistryService`、私有 `readJson`
- [x] T3 `DataServiceImpl.lineage()`：raw / processed / versions / models / summary 五段输出
- [x] T4 `DataController.java`：新增 `GET /api/data/lineage`
- [x] T5 `DataServiceImplTest.java`：4 条单测（current 标记 / dataLinked / 原始文件缺失 / 非法平台）

## 前端

- [x] T6 `api/data.js`：新增 `lineage`
- [x] T7 `views/data/lineage.vue`：链路图 + 汇总条 + 版本时间线 + 模型版本对照表
- [x] T8 `router.js`：`/data/lineage` 路由（分组 数据与特征，icon tree）
- [x] T9 `views/data/index.vue`：页头新增「数据血缘」入口

## 验证

- [x] T10 `mvn -q compile` 通过
- [x] T11 `mvn test` 全绿（实际 39 条：原 35 + 新增 4）
- [x] T12 前端静态自查（模板闭合 / api 路径 / 图标与路由分组）+ 提示用户执行 `npm run build`
