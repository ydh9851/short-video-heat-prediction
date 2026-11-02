import { post, get } from '@/utils/request'

export default {
  // 支持的实验模式元信息（含中文名、说明、产出图文件名）
  modes: () => get('/api/evaluation/modes', null, 30000),
  // 异步提交实验：立即返回 taskId，实验在后端线程池执行（分钟级实验不再占用长连接）
  submit: query => post('/api/evaluation/submit', query, 30000),
  // 轮询任务状态：QUEUED / RUNNING / DONE / FAILED，DONE 时带 result
  task: taskId => get(`/api/evaluation/task/${taskId}`, null, 30000),
  // 最近实验任务列表（摘要）
  tasks: () => get('/api/evaluation/tasks', null, 30000),
  // 实验台账：历史实验记录（含参数、耗时、traceId、结果）
  runs: (limit = 20) => get('/api/evaluation/runs', { limit }, 30000),
  // 某个实验模式最近一次成功运行的结果（供业务页面引用实验结论）
  latest: mode => get('/api/evaluation/latest', { mode }, 30000),
  // 同步执行（保留给脚本/调试，前端不再使用）
  run: query => post('/api/evaluation/run', query, 600000)
}
