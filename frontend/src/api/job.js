import { get, post } from '@/utils/request'

export default {
  // 任务分页（jobType / status 可筛选）
  page: params => get('/api/admin/job/page', params, 30000),
  // 单任务状态（轮询用）
  get: id => get(`/api/admin/job/${id}`, null, 30000),
  // 失败任务重试（以相同参数创建新任务）
  retry: id => post(`/api/admin/job/${id}/retry`, null, 30000)
}
