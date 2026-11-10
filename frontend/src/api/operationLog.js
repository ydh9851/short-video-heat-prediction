import { get } from '@/utils/request'

export default {
  // 管理操作审计日志分页（仅 ADMIN）：支持按操作标识 / 操作人筛选
  page: params => get('/api/admin/operation-log', params, 30000)
}
