import { get, post } from '@/utils/request'

export default {
  // 数据集注册表：各平台元信息（样本量/类别数/时间跨度/热度分位/是否已导入）
  platforms: () => get('/api/data/platforms', null, 30000),
  // 数据集总览（按平台）
  overview: platform => get('/api/data/overview', { platform }, 120000),
  // 样本分页预览（platform/page/size/category/keyword）
  samples: params => get('/api/data/samples', params, 120000),
  // 触发某平台原始数据导入（读取 data/raw 并归一化，耗时较长）
  importDataset: platform => post(`/api/data/import?platform=${encodeURIComponent(platform)}`, null, 900000)
}
