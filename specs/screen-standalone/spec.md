# 大屏独立全屏 — 技术规格

> 阶段 3 第 4 项（路线图：`大屏独立全屏 + 四幕剧本 + 键盘控制`；验收：可独立投屏、ESC 退出、四幕自动/手动切换）。
> 现状：`/screen/index` 是 Layout 下的普通路由，页面高度 `calc(100vh - 120px)`，仍带侧栏/顶栏/面包屑，不是真正的"大屏"。

## 1. 设计决策

### 1.1 路由（改 `router.js`）

```js
// 原来是：component: Layout -> children: [{path:'index', component: ScreenPage}]
// 改为：component: () => import('@/views/screen/index')  // 顶层路由，无 Layout 包裹
{
  path: '/screen',
  component: () => import('@/views/screen/index'),
  name: 'ScreenPage',
  meta: { title: '数据大屏', icon: 'chart', group: '项目概览', noCache: true, standalone: true }
}
```

**保留菜单**（meta 中仍带 `icon`/`group`），但因为没有 Layout 子路由，侧边栏需要特殊处理 — 侧边栏直接根据 `constantRoutes` 中的配置渲染，所以只需要让 `/screen` 仍出现在侧栏菜单中。侧栏组件通常只渲染带 `component: Layout` 的路由的 children。让我检查侧栏实现。

> 简化处理：**保留 Layout 包裹但让大屏路由的 Layout 不渲染侧栏/顶栏**。做法：Layout 读取 `route.meta.standalone`，为 true 时只渲染 `<router-view />`。这样：
> - 侧栏菜单仍能出现（因为路由顶层仍走 Layout）
> - 大屏页拿到真正的 100vw × 100vh
> - 不影响 ScenarioCompareTray 的 `isScreen` 判断
> - 改动最小

### 1.2 大屏页面改造成全屏

| 项 | 改前 | 改后 |
|---|---|---|
| 页面容器 | `.screen-page { min-height: calc(100vh - 120px); padding: 16px 20px 24px; border-radius: 12px; }` | `.screen-page { width: 100vw; height: 100vh; padding: 24px 40px; border-radius: 0; }`（无外边距、无圆角） |
| 背景 | 需要"卡片感" | 需要"沉浸式"：保留渐变但做全屏；去掉 inset shadow |
| KPI 区 | 4 列 | 5 列（为四幕剧本加一个幕指标位） |
| 工具栏 | 只有「刷新」 | 新增「全屏」按钮、幕编号指示、自动播放开关 |

### 1.3 四幕剧本

| 幕 | 主题 | 内容 | 数据来源 |
|---|---|---|---|
| 1 | 数据可信 | KPI 行 + 平台样本量柱图（宽） | data.platforms + overview |
| 2 | 热度分级与内容偏好 | 等级饼图 + 类别 Top10 条形图 | overview.gradeDistribution + categories |
| 3 | 热度分布 | 分位数柱图（宽，占满） | overview.heat |
| 4 | 系统在跑 | 实时预测流（满高） | predict.logs |

每幕有独立 `height`：前 3 幕顶部保留 KPI 行，幕 4 KPI 行折叠为一行标题。幕切换是**动画切换**（opacity + transform，240ms），不是 DOM 删除重建 — 让已加载的 ECharts 保持状态。

实现：四个幕都挂在同一个 `.screen-page` 下，用 `currentScene` 下标控制每个幕容器的 `display` / `opacity`。

### 1.4 键盘与全屏控制

| 键 | 动作 |
|---|---|
| `F` / `F11` | 切换浏览器全屏（Fullscreen API） |
| `←` / `→` | 上一幕 / 下一幕（循环） |
| `1` `2` `3` `4` | 直接跳到对应幕 |
| `空格` | 自动播放暂停/继续 |
| `ESC` | 退出全屏；非全屏时保持在当前幕 |

全屏按钮提供明确的视觉入口（一个"⛶ 全屏投屏"按钮）。

### 1.5 自动播放

- 自动播放开启后，每 **10 秒** 切换到下一幕（循环）
- 当前幕正在手动操作（例如悬停在图表上）时不自动切换
- 页面失焦时暂停自动播放，重新聚焦恢复（避免演示被打断）
- 自动播放状态显示在头部工具栏（绿色小点 + "自动播放 开/关"）

### 1.6 非目标

- 不新增后端接口（四幕数据全部来自现有 `data.platforms / data.overview / predict.logs`）
- 不新增组件库
- 不做每幕独立 ECharts 实例重建（保持原实例只改变可见性）
- 不部署时禁用（本地/演示都能用）

## 2. 改动清单

1. **`layout/index.vue`**：检测 `route.meta.standalone`，true 时跳过 Navbar/Sidebar/TagsView/BackToTop/ScenarioCompareTray，只渲染 `<router-view />`
2. **`router.js`**：大屏路由 meta 加 `standalone: true`
3. **`views/screen/index.vue`**：
   - 去掉 `min-height: calc(100vh - 120px)` 约束，改为真正 100vw × 100vh
   - 新增 4 个 scene 容器（display controlled by `currentScene`）
   - 新增 `currentScene`、`autoPlay`、键盘监听、fullscreen 切换方法
   - 新增头部工具栏：「上一幕 / 自动播放 / 下一幕 / 全屏 / 退出全屏」+ 幕编号指示
   - 移除大屏相关的 inset shadow / border-radius
   - 保留原有 4 个 ECharts 实例（platformChart / gradeChart / categoryChart / quantileChart）+ stream，只是改可见性

## 3. 验证

1. 后端 `mvn test` 继续全绿（本次不动后端）
2. 前端静态自查：路由 meta、Layout 分支逻辑、键盘监听正确清理
3. 本机无 Node.js：提示用户执行 `npm run build`
