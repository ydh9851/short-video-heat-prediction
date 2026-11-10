/**
 * 项目关键数字的默认值与本地缓存。
 *
 * 关于页会拉实时接口并写回缓存；登录页在未登录状态下只读缓存，
 * 避免调用受保护接口导致 401 跳转。接口不可用时一律回退默认值。
 */

const STORAGE_KEY = 'projectStats'

export const DEFAULT_STATS = {
  samples: 36381,
  categories: 14,
  models: 6,
  experiments: 17,
  edaGroups: 13,
  bestR2: 0.818,
  coverage: 89.5,
  uplift: 9.46,
  inferMs: 34
}

/** 读取缓存（自动与默认值合并，缺失字段不会变成 undefined） */
export function readCachedStats () {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const cached = raw ? JSON.parse(raw) : {}
    return { ...DEFAULT_STATS, ...(cached || {}) }
  } catch (e) {
    return { ...DEFAULT_STATS }
  }
}

/** 写回缓存（只覆盖传入的字段） */
export function writeCachedStats (partial) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...readCachedStats(), ...(partial || {}) }))
  } catch (e) {
    // 隐私模式 / 存储配额不足时静默失败，不影响页面
  }
}
