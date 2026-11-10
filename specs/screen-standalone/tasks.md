# 大屏独立全屏 — 任务清单

依据 `spec.md`。顺序执行，每步完成后勾选。

## 后端（无改动）

## 前端

- [x] T1 `router.js`：大屏路由 meta 加 `standalone: true`
- [x] T2 `layout/index.vue`：`route.meta.standalone` 为 true 时只渲染 `<router-view />`
- [x] T3 `views/screen/index.vue`：100vw × 100vh 全屏容器 + 去掉圆角/阴影
- [x] T4 四幕剧本：四个 scene 容器 + `currentScene` + opacity/transform 切换
- [x] T5 头部工具栏：幕编号、上/下幕、全屏按钮
- [x] T6 键盘控制：F/F11/←/→/1-4/空格/ESC
- [x] T7 自动播放：10s 切换 + 悬停/失焦暂停

## 验证

- [x] T8 `mvn test` 全绿（43 条，无后端改动）
- [x] T9 前端静态自查（路由 meta / Layout 分支 / 键盘监听清理 / ECharts 实例复用）
- [x] T10 提示用户执行 `npm run build`
