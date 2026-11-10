# 场景对比托盘 — 技术规格

> 阶段 2 第 5 项（路线图：`场景对比托盘（2~3 个）`，验收：3 个场景同屏对比、指标差异可读）。
> 已在阶段 2 第 1 项完成「分析场景 Case」的增删改查与跨页上下文，本项在其上补一层
> **全局可用的对比托盘**：把 2~3 个场景固定到托盘，一键并排比较预测、区间与核心输入。

## 1. 现状结论

| 能力 | 现状 |
|---|---|
| 场景实体 | `domain/Case.java` 存模型/类别/粉丝数/发布小时/星期/月份，按用户隔离（`CaseServiceImpl.canAccess`） |
| 场景接口 | `/api/case`：创建、分页、详情、更新、删除；前端 `api/case.js` 已封装 |
| 跨页上下文 | Vuex `caseStudy` 模块 + `localStorage`，页面通过 `currentCase` getter 复用参数 |
| 单场景预测 | `PredictService.interval(req)` 一次返回 `prediction / lo / hi / grade / alpha / target_coverage`（保形区间） |
| 前端布局 | `layout/index.vue` 是全局壳层（登录后所有后台页），适合挂载常驻托盘组件 |
| 场景列表 | `views/case/index.vue` 已有「设为当前 / 编辑 / 删除」操作列 |

**缺口**：场景之间无法并排比较；用户只能逐个切换「当前场景」再回预测页看结果。

## 2. 设计决策

### 2.1 后端（新增 2 文件，改 3 文件 + 1 测试）

1. **`viewmodel/scenario/CaseCompareRequestVM.java`（新）**：`List<Long> ids;`（`case` 是 Java 关键字，包名用 `scenario`）
2. **`CaseService`**：新增 `JsonNode compare(List<Long> ids);`
3. **`CaseServiceImpl`**
   - 构造器增加 `PredictService predictService`（无循环依赖：PredictServiceImpl 不依赖 CaseService）
   - 校验：`ids` 去重保序后数量必须为 **2~3**，否则 `BusinessException(400, "请选择 2-3 个场景进行对比")`
   - 逐个 `selectById` + `canAccess`，任一不存在/无权限 → `BusinessException(404, "场景不存在")`
   - 对每个场景拼 `PredictRequestVM`，调用 `predictService.interval(req)`；**单条失败不拖垮整批**，
     捕获异常写入该列 `error`，其余列照常返回
   - 输出：`{generatedAt, baseId(=第一个场景), items:[{id,name,description,model,videoCategory,authorFans,publishHour,publishWeekday,publishMonth,prediction,lo,hi,grade,alpha,coverage,error}]}`
4. **`CaseController`**：`@PostMapping("/compare")` + `@OperationLog("场景.对比")`
5. **`CaseServiceImplTest.java`（新，4 条）**：
   - 少于 2 个 / 多于 3 个 id 抛 400
   - 正常对比：返回条目数、预测/区间/等级映射正确、`baseId` 为首个
   - 某个场景的区间计算抛异常时，该列带 `error`，另一列仍成功

### 2.2 接口契约

`POST /api/case/compare`

```json
// 请求
{ "ids": [1, 2, 3] }

// 响应 response
{
  "generatedAt": "2026-11-09 12:00:00",
  "baseId": 1,
  "items": [
    {
      "id": 1, "name": "美食大号 · 周五晚间", "model": "lgbm",
      "videoCategory": "美食", "authorFans": 50000,
      "publishHour": 20, "publishWeekday": 5, "publishMonth": 6,
      "prediction": 12345.6, "lo": 8000.0, "hi": 20000.0,
      "grade": "B", "alpha": 0.1, "coverage": 0.9, "error": null
    }
  ]
}
```

### 2.3 前端（新增 2 文件，改 3 文件）

1. **`api/case.js`**：`compare: ids => post('/api/case/compare', { ids }, 300000)`
2. **`store/modules/caseCompare.js`（新）**：托盘状态 `items:[{id,name,videoCategory,model}]`
   - 最多 **3** 个，按 id 去重；超出时拒绝并返回 false（由页面提示）
   - 持久化 `localStorage`（键 `caseCompareTray`），刷新不丢
   - actions：`add / remove / toggle / clear`
3. **`components/ScenarioCompareTray/index.vue`（新）**
   - 常驻右下角，`items` 为空时不渲染
   - 收起态：图标 + 「对比托盘 n/3」+ 场景名胶囊（可单个移除）+「开始对比」「清空」
   - 对比弹窗（宽 1080px）：
     - 打开时 `caseApi.compare(ids)`，加载态 / 失败提示 / 单列 `error` 展示
     - 转置表格：左侧指标标签列（预测热度、90% 区间、热度等级、模型、类别、粉丝数、发布时间、相对基准变化），右侧每个场景一列
     - 「相对基准」= 与首列预测值的百分比差异（↑ 绿 / ↓ 红）
     - 每列头部「查看归因」：写入 `caseStudy/currentCase` 后跳 `/attribution`
   - 关闭后保留托盘
4. **`layout/index.vue`**：在 `<app-main />` 后挂载 `<scenario-compare-tray />`
5. **`views/case/index.vue`**
   - 操作列新增「加入对比 / 移出对比」（切换），列宽 200 → 260
   - 依赖 `mapState('caseCompare', ['items'])` 判断是否已在托盘

## 3. 非目标

- 不做服务端持久化托盘（localStorage 足够，换设备不同步）
- 不做 3 个以上场景（路线图明确 2~3 个）
- 对比弹窗不内嵌 SHAP 瀑布/反事实明细，通过「查看归因」跳到归因页看完整解释
- 不新增数据库表、不改 Flyway

## 4. 验证

1. `mvn -q compile` 通过
2. `mvn test` 全绿（当前 39 条 + 新增 4 条 = 43 条）
3. 前端静态自查：组件挂载、store 命名空间、mapState 用法、弹窗模板闭合
4. 本机无 Node.js：提示用户执行 `npm run build`
