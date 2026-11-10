# 预测页「实验台」改造 — 技术规格

> 阶段 3 第 2 项（路线图：`预测页改实验台（滑杆 + 对比托盘 + 决策卡）`；验收：调参手感、结果可解释、可沉淀为场景）。
> 现状：预测页已有「表单 + KPI + 分位数区间 + 保形区间 + what-if」四块，信息完整但仍是
> 「填表 → 看数」的工具形态，缺少**决策结论**与**场景沉淀/对比**闭环。

## 1. 设计决策（仅改前端，不动后端）

### 1.1 参数滑杆

在现有表单上增强，不删字段：

| 字段 | 改法 |
|---|---|
| 作者粉丝数 | 保留 `el-input-number`，下方加 `el-slider`（0 ~ 1,000,000，步长 5,000），tooltip 显示「x 万」 |
| 发布小时 | 用 `el-slider` 替换数字输入（0 ~ 23，带 0/6/12/18/23 刻度），右侧显示当前值 |
| 星期 / 月份 / 类别 / 模型 | 不变 |

### 1.2 决策卡（结果区首屏）

在报告头部与 KPI 行之间插入 `.decision-card`，由 `decision` 计算属性驱动：

```json
{
  "heat": 12345.6,
  "grade": "中热度",
  "rangeText": "8,000 ~ 20,000",
  "uncertainty": "低|中|高|未知",
  "advice": "将发布时段调整到「21 点」，预计热度 15,000（+21.5%）",
  "risk": "区间适中，可作为排期参考"
}
```

- 区间优先取 `conformal`（90% 保形），否则取分位数区间 `interval.p10 / p90`
- 不确定性 = `(hi - lo) / heat`：>2 高、>1 中、否则低
- 建议优先取 `whatif.best`：`维度 + 最优取值 + 预测值 + 增益`
- 风险文案按不确定性分档，明确「样本少 / 可参考 / 较稳定」
- 决策卡右侧动作：**查看归因** / **存为场景** / **加入对比**（仅已有当前场景时可用）

### 1.3 场景沉淀与对比托盘联动

- 「存为场景」：`$prompt` 输入场景名（默认 `类别 · 周X 20点`）→ `caseApi.create(payload)`
  → 成功后 `caseStudy/setCurrent` + `caseCompare/add`，提示「已存入场景库并加入对比托盘」
- 「加入对比」：已有 `currentCase` 时直接 `caseCompare/add(currentCase)`
- 「查看归因」：把当前表单包装为临时场景写入 `caseStudy`，跳 `/attribution`

### 1.4 非目标

- 不重写 what-if / 保形区间 / 批量预测 / 模型对比 / 预测记录
- 不新增后端接口、不改 Python
- 不做自动预测（仍需点击按钮）

## 2. 改动清单

1. `views/predict/index.vue`
   - 表单：粉丝数滑杆、发布小时滑杆 + 刻度
   - 结果区：决策卡（结论 / 区间 / 建议 / 风险 / 动作）
   - 新增 `decision` 计算属性与 `dimensionName / fmtFansShort / gradeKey` 辅助
   - 新增 `saveAsScene / goAttribution / addToCompare`
   - 新增决策卡样式
2. `api/case.js` 无需改动（`create` 已存在）

## 3. 验证

1. 后端 `mvn test` 不变（43 条全绿）
2. 前端静态自查：模板闭合、computed 引用、prompt promise、store 命名空间
3. 本机无 Node.js：提示用户执行 `npm run build`
