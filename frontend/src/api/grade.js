import { get } from '@/utils/request'

export default {
  // 热度分级（首次需聚类 + 训练分类器，耗时较长）
  grade: k => get('/api/grade', { k }, 300000)
}
