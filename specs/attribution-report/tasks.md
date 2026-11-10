# 归因页「解释报告」改造 — 任务清单

依据 `spec.md`。

## 前端

- [x] T1 新建 `panels/ExplanationReport.vue`：props（explain / quality / cf / refutation / form）
- [x] T2 结论段：热度 + 等级 + 一句话归因 + 基线偏离 + 参数摘要
- [x] T3 证据段：正/负贡献 Top2、正负合计与集中度、可信度三指标
- [x] T4 建议段：后端 advice 列表 + 反事实最大提升项（缺失时给兜底文案）
- [x] T5 局限段：三条口径说明（模型内解释 / 点估计 / Top-K）
- [x] T6 父页面挂载组件并传值，保持原有区块不变
- [x] T7 报告样式：四段卡片、分节标题、缺失态降级

## 验证

- [x] T8 前端静态自查（模板闭合 / props 默认值 / 缺字段不报错）
- [x] T9 `mvn test` 全绿（43 条，无后端改动）
- [x] T10 提示用户执行 `npm run build`
