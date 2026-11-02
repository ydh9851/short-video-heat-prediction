import { get, post } from '@/utils/request'

export default {
  // 模型注册表摘要（版本 / 阶段 / 指标）
  list: () => get('/api/models', null, 60000),
  // 扫描 model_cache 并登记新训练的模型
  sync: () => post('/api/models/sync', null, 180000),
  // 切换线上版本
  promote: (model, version) =>
    post(`/api/models/${encodeURIComponent(model)}/promote?version=${encodeURIComponent(version)}`, null, 60000),
  // 回滚到上一个版本
  rollback: model => post(`/api/models/${encodeURIComponent(model)}/rollback`, null, 60000),
  // 影子模式统计（线上模型 vs 候选模型的打分差异）
  shadow: (recent = 10) => get('/api/models/shadow', { recent }, 60000)
}
