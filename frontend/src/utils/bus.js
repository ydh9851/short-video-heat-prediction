/**
 * 轻量事件总线（零依赖）。
 *
 * Vue 3 移除了 Vue 2 的 $root.$on / $root.$emit 实例事件 API，
 * 全局事件需自行实现。这里提供一个够用的最小实现：
 * 同一事件名可注册多个处理器，处理器内部异常不会影响其它监听者。
 */
const handlers = new Map()

export const bus = {
  /** 订阅事件，返回取消订阅的函数 */
  on (event, fn) {
    if (!handlers.has(event)) handlers.set(event, new Set())
    handlers.get(event).add(fn)
    return () => bus.off(event, fn)
  },

  /** 取消订阅；不传 fn 则移除该事件的所有处理器 */
  off (event, fn) {
    const set = handlers.get(event)
    if (!set) return
    if (fn) set.delete(fn)
    else set.clear()
  },

  /** 触发事件 */
  emit (event, payload) {
    const set = handlers.get(event)
    if (!set || !set.size) return
    for (const fn of Array.from(set)) {
      try {
        fn(payload)
      } catch (err) {
        console.error('[bus] 事件处理器异常：' + event, err)
      }
    }
  }
}

export default bus