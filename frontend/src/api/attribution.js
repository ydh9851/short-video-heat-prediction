import { post, get } from '@/utils/request'

export default {
  // 全局归因（首次需跑 SHAP，耗时较长）
  global: () => get('/api/attribution/global', null, 200000),
  // 单样本归因：各特征对预测热度的贡献 + 运营建议
  explain: query => post('/api/attribution/explain', query, 200000),
  // 部分依赖图
  pdp: feature => get('/api/attribution/pdp', { feature }, 200000)
}
