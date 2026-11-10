import { get, post, put, del } from '@/utils/request'

export default {
  // 创建场景（数据样本页 / 预测页「存为场景」）
  create: data => post('/api/case', data),
  // 场景分页（普通用户只见自己的，管理员见全部）
  page: params => get('/api/case/page', params, 30000),
  get: id => get(`/api/case/${id}`, null, 30000),
  update: (id, data) => put(`/api/case/${id}`, data),
  remove: id => del(`/api/case/${id}`),
  // 场景对比：2~3 个场景并排返回预测、保形区间与核心输入
  compare: ids => post('/api/case/compare', { ids }, 600000)
}
