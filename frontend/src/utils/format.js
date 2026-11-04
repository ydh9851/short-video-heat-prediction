/**
 * 展示层格式化函数。
 *
 * 抽出来是因为页面与子组件都要用同样的口径（千分位、百分比），
 * 各写一份迟早会出现"这里四舍五入、那里截断"的不一致。
 */

/** 千分位数字；非有限值显示为破折号 */
export function formatNum (v) {
  const n = Number(v)
  if (!isFinite(n)) return '—'
  return Math.round(n).toLocaleString('zh-CN')
}

/** 百分比；入参为 0~1 的比例，入参为空或非法时显示为破折号 */
export function pct (v) {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return (n * 100).toFixed(2) + '%'
}

/** 保留指定小数位 */
export function fmt (v, digits) {
  if (v === null || v === undefined || v === '') return '-'
  const n = Number(v)
  if (!Number.isFinite(n)) return '-'
  return n.toFixed(digits == null ? 3 : digits)
}