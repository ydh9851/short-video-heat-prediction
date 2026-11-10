# 阶段 3 收尾 — 设计系统 / EDA 交互 / 数字动态化 / 命令面板与导览

本批完成路线图阶段 3 剩余四项（第 1、5、6、7），后端零改动。

---

## 一、设计 token + ECharts 主题 + 通用组件

现状：`styles/theme.scss` 已有颜色 / 圆角 / 阴影令牌，`utils/chart.js` 已有动画与轴线常量，
`layout/components/CaseBar.vue` 已存在并在 Navbar 使用。

补齐：

### 1.1 ECharts 主题
- 新增 `utils/echartsTheme.js`：
  - 注册名为 `app` 的主题，统一调色板（靛蓝紫主色 + 语义色）、文字色、轴线/分割线、
    tooltip 白底圆角、legend 与 grid 间距；
  - `ensureAppTheme(echarts)` 用 WeakSet 做一次性注册。
- `utils/chart.js` 的 `createChart` 改为自动注册并 `init(el, 'app')`，
  所有走 `createChart` 的图表（预测 what-if、评估页等）自动统一风格。

### 1.2 通用组件
- `components/InsightCard.vue`：结论卡。props `title / desc / tone / tag`，支持默认插槽与 `extra` 插槽。
- `components/ConfidenceBadge.vue`：覆盖率徽标。props `value / target / label / suffix`，
  `value >= target` 为达标色，否则警示色；缺失数据显示「待评估」。
- `components/JobProgress.vue`：任务进度条。props `percent / status / label / elapsed`，
  RUNNING 渐变条纹、DONE 绿色、FAILED 红色。
- `CaseBar` 已具备，不重复实现。

### 1.3 落地使用（保证组件不是死代码）
- `ConformalPanel` 的实测覆盖率改用 `ConfidenceBadge`（值取 `conformal.coverage`，缺失时 89.5）。
- 实验中心运行中状态改用 `JobProgress`（在结果区上方显示进度与已耗时）。
- EDA 交互图顶部摘要使用 `InsightCard`。

---

## 二、EDA 改交互图（保留静态快照）

现状：EDA 页只展示 13 张 Python 生成的 PNG，分组筛选是纯前端过滤。

改造：`views/analysis/edaAnalysis.vue` 顶部加 `el-tabs`：

1. **交互洞察（默认）**：新组件 `views/analysis/components/EdaInteractive.vue`
   - 数据源：`GET /api/data/platforms` 取默认平台 → `GET /api/data/overview` 取类别/分位/等级 →
     `GET /api/data/samples?size=200` 取样本散点；
   - 三张联动图：
     - 类别样本量柱状图（点击类别 → 过滤散点与摘要）；
     - 热度等级环形图（点击等级 → 按 684 / 15661 阈值过滤散点）；
     - 粉丝数—热度散点图（按当前类别 / 等级交叉过滤，log 轴）；
   - 顶部显示当前筛选条件 chips + 「重置」，下方 `InsightCard` 给出样本量 / 平均热度 / 最高类别；
   - 任一张图点击都可清空或叠加筛选，形成「筛选 → 联动 → 结论」闭环。
2. **静态图组**：保留现有 13 张 PNG、分组 pill 与预览，逻辑不变。

数据缺失（平台未导入 / 样本为空）时展示 `AppEmpty` 与原因，不报错。

---

## 三、登录 / 关于页数字动态化 + 数据页治理块清理

### 3.1 共享统计
- 新增 `utils/projectStats.js`：默认值（样本 36,381、模型 6、EDA 13、R² 0.818、覆盖 89.5% 等）
  + `readCachedStats()/writeCachedStats()`（localStorage，键 `projectStats`）。

### 3.2 关于页
- 页面加载后并行请求：
  - `dataApi.platforms()` → 默认平台；`dataApi.overview(platform)` → 样本量、类别数、时间跨度；
  - `predictApi.metrics()` → 模型数与最优 R²(log)；
  - `evaluationApi.modes()` → 可复现实验数量；
  - `evaluationApi.latest('conformal')` → 实测覆盖率（拿不到则用默认值）。
- Hero 六个数字改为 `heroStats` 数组驱动，并写入缓存；接口失败全部回退默认值，不阻塞页面。
- 「数据集与特征体系」的规模描述同步使用实时样本量。

### 3.3 登录页
- 左侧三个数字改为动画计数（复用 `CountTo`），数值优先读缓存，其次默认值；
  预登录状态不请求受保护接口，避免 401 跳转。

### 3.4 数据页清理
- 删除「模型治理」卡片（与 `/model/index` 模型治理页重复，侧栏已有入口）。
- 删除「数据质量门禁」大表格卡片；保留顶部「质量门禁速览」strip，并把「运行质检」按钮并入 strip。
- 清理仅被删除块使用的 data / 方法（`shadow`、`models`、`loadingModels` 等），
  确保质量门禁功能（速览 + 运行质检）仍可用。

---

## 四、命令面板 + 演示 Tour

### 4.1 命令面板
- 新增 `components/CommandPalette/index.vue`，挂载于 Layout（standalone 不渲染）。
- `Ctrl / Cmd + K` 打开/关闭；输入框自动聚焦；`↑/↓` 选择、`Enter` 执行、`Esc` 关闭。
- 命令分两组：
  - 页面跳转：主页、数据管理、预测、归因、实验中心、模型治理、报告中心、数据大屏、项目介绍；
  - 快捷操作：开始演示导览、打开数据大屏、复制当前地址。
- Navbar 右侧增加 `⌘K` 提示按钮，点击等价于快捷键。

### 4.2 演示 Tour
- 新增 `components/DemoTour/index.vue`：自研轻量导览（不依赖 Element Plus 版本），
  props `visible`，事件 `close`。
- 六步：项目概览 → 数据管理 → 热度预测 → 归因解释 → 实验中心 → 模型治理。
  每步自动 `router.push` 到对应路由，等待渲染后按选择器测量元素（找不到则指向 `.page-head`），
  绘制高亮框 + 说明卡；支持「上一步 / 下一步 / 结束」，`Esc` 退出。
- Navbar 增加「导览」入口；命令面板亦可启动。
- 导览结束写入 localStorage `demoTourDone`，避免每次进入自动打扰（导览本身只手动启动）。

---

## 验收

- `mvn test` 保持 43 条全绿（后端无改动）。
- 所有新组件在后端不可用 / 数据缺失时有降级态，不出现 `undefined`。
- EDA 交互图三图联动可用，静态图组功能不回退。
- 登录页不因统计请求触发 401 跳转；关于页接口失败不影响正文。
- 数据页质量门禁仍可「运行质检」，模型治理从侧栏进入。
- 命令面板与导览在非 standalone 页面可用，大屏全屏模式不受影响。

## 不做

- 不新增 / 修改后端接口。
- 不改动已有 STATIC EDA 图片与算法脚本。
- 不引入新的第三方依赖。
