# 数据集版本 / 血缘页 — 技术规格

> 阶段 2 第 4 项（路线图：`数据集版本/血缘页（可先做轻量图）`）。
> 目标：把散落在 `dataset_registry.json`、`dataset_versions.json`、`model_registry.json`
> 的元数据串成一条可读链路：**原始文件 → 规范化数据集 → 数据集版本 → 模型版本**，
> 并回答「线上模型用的是哪一版数据」。

## 1. 现状结论（已探查确认）

| 现状 | 证据 |
|---|---|
| 平台元信息已齐 | `data/processed/dataset_registry.json`：`datasets.<platform>` 含 `rawFile/processedFile/rows/categoryCount/timeStart/timeEnd/importTime` |
| 数据集版本已登记 | `data/processed/dataset_versions.json`：`datasets.<platform>[]` 含 `version/fingerprint/file/rows/registered_at`（可选 `heat_median/heat_p90/category_count`） |
| 版本写入方 | `algorithm/datasets/versioning.py`：SHA-256 前 12 位做指纹，同指纹不重复登记；`current_version()` = 列表最后一条 |
| 模型侧有数据版本 | `data/models/model_registry.json`：每个版本条目含 `featureVersion/dataVersion/r2/mae/rmse/trainedAt/artifact`，模型级 `active` |
| 注册表读取能力已具备 | `ModelRegistryService.read()` 返回整棵 JSON；`activeVersionMeta(model)` 返回可加载的 active 条目（不可加载返回 null） |
| 后端数据服务 | [DataServiceImpl.java](file:///c:/Users/Ximenez2021/Desktop/demo/short-video-heat-prediction/backend/src/main/java/com/alvis/media/service/impl/DataServiceImpl.java) 已有 `readRegistry()`、`resolveFile()`、`rawDir`、`detectPlatform()` 等私有能力 |
| 前端数据页 | `views/data/index.vue`：page-head + 质量门禁 + 原始文件 + 治理入口 + KPI + 图表 + 样本表；已有平台下拉与页面路由模式 |

**差距**：上述三份元数据各自展示，没有一条「数据版本 → 模型版本」的对照视图；数据页也无可下钻入口。

## 2. 设计决策

### 2.1 后端（改 3 文件 + 新增 1 测试）

**不改表**：全部数据来自现有 JSON 文件，无需 Flyway 迁移。

1. **`service/DataService.java`**：新增 `JsonNode lineage(String platform);`
2. **`service/impl/DataServiceImpl.java`**
   - 新增字段 `@Value("${system.data.versions:../data/processed/dataset_versions.json}") private String versionsPath;`
   - 构造器增加 `ModelRegistryService registryService` 依赖（与现有 `PythonGateway` 并存；该类仅依赖 PythonGateway，无循环依赖）
   - 新增私有 `readJson(String path)`（复用 `om`，异常/缺失返回 null）
   - 实现 `lineage(platform)`：
     - 平台校验：空则取注册表默认平台；不在 `SUPPORTED` 抛 `IllegalArgumentException`（400）
     - `raw`：取注册表 `rawFile` 的文件名，按 `rawDir` 拼绝对路径；输出 `path/name/exists/sizeMB/modifiedAt`
     - `processed`：用现有 `resolveFile(platform)`；输出 `path/name/exists/sizeMB/modifiedAt/rows/categoryCount/timeStart/timeEnd`
     - `versions`：读 `versionsPath`，取 `datasets.<platform>[]`；逐条输出
       `{version,fingerprint,file,rows,registeredAt,heatMedian,heatP90,categoryCount,current,matchesProcessed,exists}`；
       `current` = 列表最后一条；`matchesProcessed` = 条目 `file` 与规范化数据集文件名一致；
       `exists` = `processedDir/<file>` 存在
     - `models`：`registryService.read()` 遍历 `models`；对每个模型取 `active` 对应版本条目，输出
       `{model,activeVersion,featureVersion,dataVersion,dataLinked,loadable,r2,mae,rmse,trainedAt}`；
       `loadable` = `registryService.activeVersionMeta(model) != null`；
       `dataLinked` = `dataVersion` 非空且等于 `currentVersion`
     - `summary`：`{versionCount,modelCount,linkedModelCount,rawExists,processedExists,chainComplete}`，
       `chainComplete = rawExists && processedExists && versionCount>0 && linkedModelCount>0`
     - `currentVersion`：版本列表最后一条的 `version`，无则空串
     - `updatedAt`：注册表 `updatedAt`
3. **`controller/DataController.java`**：新增
   `@GetMapping("/lineage")` → `RestResponse.ok(dataService.lineage(resolve(platform)))`
4. **`test/.../DataServiceImplTest.java`（新）**：4 条单测（JUnit5 + Mockito + `ReflectionTestUtils`）
   - 最新版本被标记 `current`、`matchesProcessed` 判断正确
   - `dataVersion` 与 `currentVersion` 一致时模型 `dataLinked=true`，否则 false
   - 原始文件不存在时 `rawExists=false`、`chainComplete=false`
   - 不支持的平台抛 `IllegalArgumentException`

### 2.2 接口契约

`GET /api/data/lineage?platform=douyin`（platform 可省略）

```json
{
  "platform": "douyin",
  "displayName": "抖音",
  "updatedAt": "2026-10-20 10:52:36",
  "raw": {"path":"data/raw/douyin_video_data.xlsx","name":"douyin_video_data.xlsx","exists":true,"sizeMB":12.3,"modifiedAt":"2026-10-20 10:15:02"},
  "processed": {"path":"data/processed/douyin_clean.csv","name":"douyin_clean.csv","exists":true,"sizeMB":6.08,"modifiedAt":"2026-10-20 10:15:02","rows":45476,"categoryCount":14,"timeStart":"2025-09-01","timeEnd":"2025-12-26"},
  "currentVersion": "v20261104-010645-414489",
  "versions": [{"version":"v20261104-010645-414489","fingerprint":"414489956bf2","file":"train_clean.csv","rows":36381,"registeredAt":"2026-11-04 01:06:45","heatMedian":null,"heatP90":null,"categoryCount":null,"current":true,"matchesProcessed":false,"exists":true}],
  "models": [{"model":"lgbm","activeVersion":"v4-20261109_041936_208829","featureVersion":4,"dataVersion":"v20261104-010645-414489","dataLinked":true,"loadable":true,"r2":0.8182,"mae":0.6523,"rmse":0.9778,"trainedAt":"2026-11-09 04:19:36"}],
  "summary": {"versionCount":1,"modelCount":7,"linkedModelCount":7,"rawExists":true,"processedExists":true,"chainComplete":true}
}
```

### 2.3 前端（新建 1 文件 + 改 3 文件）

1. **`api/data.js`**：新增 `lineage: platform => get('/api/data/lineage', { platform }, 30000)`
2. **`views/data/lineage.vue`（新）**：沿用现有页面范式
   - `page-head`：标题「数据血缘」+ 说明；平台下拉（`data.platforms`）+ 重新加载 + 返回数据管理按钮
   - **链路图（轻量 CSS 流程图，不引新依赖）**：四张节点卡横向串联
     `原始文件` → `规范化数据集` → `数据集版本` → `模型版本`；每卡显示关键字段与 `exists / linked` 状态点，
     缺失或未关联显示告警色；顶部一行汇总（版本数 / 模型数 / 已关联模型 / 链路完整）
   - **版本时间线**：`el-timeline` 展示 `versions`（版本号、指纹、行数、登记时间、`current` 标签、可选热度中位数/P90/类别数）；无数据用 `AppEmpty`
   - **模型版本对照表**：`el-table` 列 = 模型 / 线上版本 / 特征版本 / 数据版本 / 数据版本匹配（tag）/ 可加载（tag）/ R² / MAE / 训练时间
   - 平台切换时重新请求；加载态与空态齐全
3. **`router.js`**：`/data` 下新增子路由
   `{ path:'lineage', component: () => import('@/views/data/lineage'), name:'DataLineage', meta:{title:'数据血缘',icon:'tree',group:'数据与特征',noCache:true} }`
4. **`views/data/index.vue`**：`page-head-actions` 新增普通按钮「数据血缘」→ `$router.push('/data/lineage')`

## 3. 非目标

- 不做版本 diff / 删除 / 回滚（后续可选）
- 不引入 ECharts graph 或新依赖，链路图用 CSS 节点卡
- 不修改 `versioning.py`、不改模型注册表读写逻辑
- 不迁移 JSON 到数据库

## 4. 验证

1. `mvn -q compile` 通过
2. `mvn test` 全绿（原 34 条 + 新增 4 条 = 38 条）
3. 前端静态自查：模板/脚本/样式闭合、`api` 导入路径、图标 `tree` 存在、路由分组正确
4. 本机无 Node.js：提示用户执行 `npm run build` 验证
