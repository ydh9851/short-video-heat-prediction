import { post, get } from '@/utils/request'

export default {
  // 支持的实验模式元信息（含中文名、说明、产出图文件名）
  modes: () => get('/api/evaluation/modes', null, 30000),
  // 执行指定实验（交叉验证/调参等耗时较长，超时放宽到 10 分钟）
  run: query => post('/api/evaluation/run', query, 600000)
}
