import { get, post } from '@/utils/request'

export default {
  // 模型注册表摘要（版本 / 阶段 / 指标）
  list: () => get('/api/models', null, 60000),
  // 扫描 model_cache 并登记新训练的模型
  sync: () => post('/api/models/sync', null, 180000),
  // 切换线上版本（默认要求已通过上线预演；force=true 强制切换）
  promote: (model, version, force = false) =>
    post(`/api/models/${encodeURIComponent(model)}/promote?version=${encodeURIComponent(version)}${force ? '&force=true' : ''}`, null, 60000),
  // 回滚到上一个版本
  rollback: model => post(`/api/models/${encodeURIComponent(model)}/rollback`, null, 60000),
  // 影子模式统计（线上模型 vs 候选模型的打分差异）
  shadow: (recent = 10) => get('/api/models/shadow', { recent }, 60000),
  // 提交漂移检测任务（异步），返回 { jobId }
  driftRun: () => post('/api/models/drift/run', null, 30000),
  // 最新一份漂移报告（无报告时 response 为 null）
  driftLatest: () => get('/api/models/drift/latest', null, 30000),
  // 提交上线预演任务：候选版本 vs 当前线上版本
  rehearsalRun: (model, version) =>
    post(`/api/models/${encodeURIComponent(model)}/rehearsal?version=${encodeURIComponent(version)}`, null, 30000),
  // 该（模型, 候选版本）最新一份预演报告
  rehearsalLatest: (model, version) =>
    get(`/api/models/${encodeURIComponent(model)}/rehearsal`, { version }, 30000),
  // 治理任务状态轮询（漂移 / 预演）
  job: id => get(`/api/models/job/${id}`, null, 30000)
}
