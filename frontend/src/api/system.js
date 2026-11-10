import { get } from '@/utils/request'

export default {
  // 系统状态总览：推理引擎 / 实验线程池 / 预测指标 / JVM（仅 ADMIN）
  status: () => get('/api/admin/system/status', null, 30000)
}
