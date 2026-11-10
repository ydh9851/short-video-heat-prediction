# 阶段 3 收尾 — 任务清单

依据 `spec.md`。

## 一、设计系统

- [x] T1 `utils/echartsTheme.js` + `utils/chart.js` 接入统一主题
- [x] T2 `components/InsightCard.vue`
- [x] T3 `components/ConfidenceBadge.vue` + 替换 ConformalPanel 覆盖率
- [x] T4 `components/JobProgress.vue` + 接入实验中心运行态

## 二、EDA 交互图

- [x] T5 `views/analysis/components/EdaInteractive.vue`（三图 + 交叉筛选 + 摘要）
- [x] T6 `edaAnalysis.vue` 改 Tab（交互洞察 / 静态图组）

## 三、数字动态化与数据页清理

- [x] T7 `utils/projectStats.js`
- [x] T8 关于页 hero 数字接实时接口 + 缓存
- [x] T9 登录页数字动画（读缓存 / 默认值）
- [x] T10 数据页删除模型治理卡 + 质量门禁大表，速览条保留「运行质检」

## 四、命令面板与 Tour

- [x] T11 `components/CommandPalette`（Ctrl/Cmd+K、键盘导航）
- [x] T12 `components/DemoTour`（六步、路由跳转、高亮框）
- [x] T13 Layout / Navbar 接入两个入口

## 验证

- [x] T14 前端静态自查（模板闭合 / props 默认值 / 数据缺失降级）
- [x] T15 `mvn test` 全绿（43 条）
- [x] T16 提示用户执行 `npm run build`
