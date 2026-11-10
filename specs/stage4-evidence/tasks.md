# 阶段 4：论文与答辩证据 — 任务清单

依据 `spec.md`。

## 一、事实核对

- [x] T1 核对后端 43 条 / 算法 47 条测试结果，导出逐类统计
- [x] T2 核对数据资产（dataset_registry / quality_report / model_registry）关键数字
- [x] T3 核对 Controller 端点清单与 `docs/API.md` 现有分组差异

## 二、文档撰写

- [x] T4 `docs/需求与用例.md`
- [x] T5 `docs/概要设计.md`
- [x] T6 `docs/数据库设计.md`（含 Mermaid ER）
- [x] T7 `docs/测试报告.md`（含性能实测记录 + SUS 模板）
- [x] T8 `docs/部署手册.md`
- [x] T9 `docs/演示脚本.md`（5 分钟六幕，对齐阶段 3 新增能力）

## 三、索引与一致性

- [x] T10 `README.md` 增加文档导航；`docs/API.md` 补齐缺失分组
- [x] T11 交叉引用与占位符自查（无 TODO/XXX）

## 四、验证

- [x] T12 `mvn test` 仍 43 条全绿
- [x] T13 `pytest algorithm/tests` 仍 47 条全绿
- [x] T14 提示用户执行 `npm run build` 与截图更新清单
