/**
 * 演示模式：地址后加 ?demo=1 即可进入。
 *
 * 目的：现场展示时把与结论无关的界面元素收起，让注意力集中在图表与结论上。
 * 做了三件事：
 *   1. 侧边栏自动折叠（图标条），给内容让出横向空间；
 *   2. 隐藏顶部标签栏（TagsView），减少视觉噪音；
 *   3. 给 <html> 加 demo-mode 类，供样式做统一调整。
 *
 * 不改动任何业务逻辑，也不写 Cookie——退出演示模式即恢复原状。
 */

export function isDemoMode () {
  try {
    const sp = new URLSearchParams(window.location.search)
    return sp.get('demo') === '1'
  } catch (e) {
    return false
  }
}

/**
 * 初始化演示模式。需要在 store 安装之后、路由挂载之前调用。
 * @param {import('vuex').Store} store
 * @returns {boolean} 是否进入演示模式
 */
export function initDemoMode (store) {
  if (!isDemoMode()) {
    return false
  }
  document.documentElement.classList.add('demo-mode')
  try {
    // closeSideBar 不写 Cookie，不会污染用户平时的偏好
    store.dispatch('app/closeSideBar', { withoutAnimation: true })
  } catch (e) {
    // store 尚未就绪时忽略，样式类仍然生效
  }
  return true
}
