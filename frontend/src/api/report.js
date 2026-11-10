import { get, post, del } from '@/utils/request'

export default {
  // 提交报告生成（异步）：{ name?, caseId?, model?, videoCategory?, ... } → { reportId, jobId }
  generate: data => post('/api/report/generate', data, 30000),
  // 报告分页（普通用户仅自己的，管理员全部）
  page: params => get('/api/report/page', params, 30000),
  // 单条详情（轮询生成状态用）
  get: id => get(`/api/report/${id}`, null, 30000),
  remove: id => del(`/api/report/${id}`),
  // 开启分享 → { token, url }
  share: id => post(`/api/report/${id}/share`),
  // 取消分享
  unshare: id => del(`/api/report/${id}/share`)
}
