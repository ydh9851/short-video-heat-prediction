# 归因页「解释报告」改造 — 设计方案

## 背景

归因页已有完整的能力：全局 SHAP 重要性、单条贡献拆解、PDP、交互效应、反事实、
解释质量三指标。但页面是「图表优先」的排布，读者需要自己从瀑布图、条形图和表格里
归纳结论，答辩时也不容易一句话讲清「所以到底为什么火」。

本次改造把单条归因结果重组为一份**四段式解释报告**：

> 结论 → 证据 → 建议 → 局限

图表不删除，降级为「证据」部分的支撑材料；后端零改动，全部基于已有响应字段。

## 数据来源（现有接口，不改）

`POST /api/attribution/explain` → `response`：

```json
{
  "prediction": 12345.6,
  "prediction_log": 9.42,
  "base_value": 8.10,
  "contributions": [{ "feature": "author_fans_log", "feature_cn": "作者粉丝数", "value": 10.8, "shap": 0.82 }],
  "top_positive": [{ "...": "..." }],
  "top_negative": [{ "...": "..." }],
  "advice": ["作者粉丝基数偏低……", "发布时段处于凌晨……"],
  "figure": "shap_waterfall.png"
}
```

- `quality`：`GET /api/evaluation/latest?mode=explanation-quality`，字段 `compacity.k80`、`consistency.kendall_shap_vs_gain`、`stability.jaccard_mean`
- `cf`：反事实结果 `{ base_heat, base_grade, suggestions:[{dimension,from,to,heat,delta_pct,grade}], non_mutable }`
- `refutation`：稳健性结果 `{ stability:{ hour_gain:{ cv, min, max } } }`

## 方案

新增 `frontend/src/views/attribution/panels/ExplanationReport.vue`，在单条归因结果
（`<template v-if="explain">`）的最顶部渲染。父页面只增加组件引入与一个标签，其余区块
顺序不变。

Props：`explain`、`quality`、`cf`、`refutation`、`form`。

### 一、结论

- 用一句话给出判断：**「这条视频预计热度 X（等级），主要由 A、B 拉高，被 C、D 拖累」**
- 等级阈值与预测页一致：低 < 684 ｜ 中 684~15,661 ｜ 高 ≥ 15,661
- 基线偏离：`delta = prediction_log - base_value`，同时给出原始热度相对基线的百分比
- 参数摘要：类别 / 粉丝数 / 小时 / 星期 / 月份，说明结论成立的前提

### 二、证据

- 正贡献 Top2、负贡献 Top2：特征名 + 取值 + SHAP 值（带正负号）
- 正负贡献合计：`Σ shap>0` 与 `Σ shap<0`，以及净效应，说明结论不是单一特征导致
- 贡献集中度：Top2 正贡献占全部正贡献的比例，用于说明「是否高度依赖一两个因素」
- 可信度三指标：k80 / Kendall τ / Jaccard；`quality` 缺失时显示「尚未运行解释质量实验」

### 三、建议

- 主体沿用后端 `explain.advice`（已包含粉丝、时段、星期、类别与 Top 特征解读）
- 若 `cf.suggestions` 存在，追加一条「最大提升空间」：维度、从 → 到、预计热度、提升百分比
- 若 `cf.suggestions` 为空，明确写「当前条件下未发现可单条调整的显著提升项」

### 四、局限

固定列出三条口径说明，避免把模型解释当成因果结论：

1. SHAP 是**模型内**归因，反映的是当前 active 模型版本的决策依据，不等于真实因果效应
2. 反事实建议来自模型内插值点估计；`refutation` 有数据时引用 CV 与区间，说明最优取值会漂移
3. `contributions` 只返回 Top-K 特征，其余贡献未展示；全局结论请以「全局归因」区块为准

## 验收

- `explain` 为空时组件不渲染，不出现空卡片
- 四段标题与内容齐全，结论句在无正/负贡献时也能成立
- `quality` / `cf` / `refutation` 任一缺失时优雅降级（不报错、不显示 undefined）
- 原有图表、CSV 导出、HTML 报告入口均不受影响
- 后端无改动，`mvn test` 保持 43 条全绿

## 不做

- 不新增后端接口，不改 SHAP 计算口径
- 不重排全局归因 / PDP / 交互效应区块
- 不引入 Markdown 渲染或 PDF 导出（HTML 报告仍走报告中心）
