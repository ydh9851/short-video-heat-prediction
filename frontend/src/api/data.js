import { get } from '@/utils/request'

export default {
  // 数据集总览
  overview: () => get('/api/data/overview', null, 60000),
  // 样本分页预览（page/size/category）
  samples: params => get('/api/data/samples', params, 60000)
}
