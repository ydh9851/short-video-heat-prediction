/**
 * 批量预测输入解析：把「类别,粉丝数,小时,星期,月份」的多行文本解析为请求数组。
 *
 * 抽成纯函数的原因：这段逻辑有明确的输入输出与错误语义（哪一行错、错在什么），
 * 放在组件里只能靠手工点页面验证；独立出来后可直接写单元测试覆盖边界情况。
 */

/** 单次批量预测的行数上限 */
export const MAX_BATCH_ROWS = 500

/**
 * 解析批量文本。
 * @param {string} text 多行文本，行内用逗号或中文逗号分隔
 * @returns {{items: Array, error: string}} 成功时 error 为空串，失败时 items 为空数组
 */
export function parseBatch (text) {
  const lines = (text || '').split(/\r?\n/).map(l => l.trim()).filter(l => l)
  if (!lines.length) {
    return { items: [], error: '请至少输入一行数据' }
  }

  const items = []
  for (let i = 0; i < lines.length; i++) {
    const p = lines[i].split(/[,，]/).map(s => s.trim())
    if (p.length < 5) {
      return { items: [], error: `第 ${i + 1} 行格式不对，应为：类别,粉丝数,小时,星期,月份` }
    }
    const fans = Number(p[1])
    const hour = Number(p[2])
    const weekday = Number(p[3])
    const month = Number(p[4])
    if ([fans, hour, weekday, month].some(v => Number.isNaN(v))) {
      return { items: [], error: `第 ${i + 1} 行含非数字字段` }
    }
    if (hour < 0 || hour > 23 || weekday < 0 || weekday > 6 || month < 1 || month > 12) {
      return { items: [], error: `第 ${i + 1} 行取值超出范围（小时 0-23，星期 0-6，月份 1-12）` }
    }
    items.push({
      videoCategory: p[0],
      authorFans: fans,
      publishHour: hour,
      publishWeekday: weekday,
      publishMonth: month
    })
  }

  if (items.length > MAX_BATCH_ROWS) {
    return { items: [], error: `一次最多 ${MAX_BATCH_ROWS} 条` }
  }
  return { items, error: '' }
}