import { post, get } from '@/utils/request'

export default {
  // 单条预测：首次调用可能需要训练模型，放宽超时
  predict: query => post('/api/predict', query, 120000),
  // 批量预测（多条：类别/粉丝数/发布时段 → 预测热度 + 等级）
  predictBatch: query => post('/api/predict/batch', query, 180000),
  // 多模型对照：各模型评估指标
  metrics: () => get('/api/predict/metrics', null, 120000)
}
