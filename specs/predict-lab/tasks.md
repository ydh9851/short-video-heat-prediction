# 预测页「实验台」改造 — 任务清单

依据 `spec.md`。

## 前端

- [x] T1 粉丝数：数字输入 + 滑杆（0~100 万，步长 5,000）
- [x] T2 发布小时：滑杆（0~23，含刻度）
- [x] T3 `decision` 计算属性：热度 / 区间 / 不确定性 / 建议 / 风险
- [x] T4 结果区决策卡：结论 + 区间 + 建议 + 风险 + 动作
- [x] T5 `saveAsScene`：prompt 命名 → 创建场景 → 写入当前场景 + 加入对比托盘
- [x] T6 `goAttribution` / `addToCompare`
- [x] T7 决策卡样式（按等级着色）

## 验证

- [x] T8 `mvn test` 全绿（43 条，无后端改动）
- [x] T9 前端静态自查（模板闭合 / computed / prompt / store）
- [x] T10 提示用户执行 `npm run build`
