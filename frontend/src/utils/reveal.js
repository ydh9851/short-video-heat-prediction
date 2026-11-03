/**
 * 滚动浮现（Reveal on Scroll）
 * ------------------------------------------------------------
 * 元素进入视口时按层级依次浮现，而不是一次性全部显示。
 * 而不是一次性全部显示。
 *
 * 使用浏览器原生 IntersectionObserver，不引入任何前端依赖，
 * 保证离线环境也能构建与运行。
 *
 * 用法：在模板元素上加 data-reveal（可选 data-reveal-delay="120" 指定延迟毫秒），
 *      页面挂载后调用 initReveal()；路由切换后再次调用即可重新绑定。
 */

/** 是否已经初始化过全局观察器（同一页面只建一次） */
let observer = null
const observed = new WeakSet()

/** 系统是否要求减少动效 —— 此时直接显示，不做动画 */
function prefersReducedMotion () {
  return typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function showImmediately (el) {
  el.classList.add('is-revealed')
  el.style.removeProperty('--reveal-delay')
}

function ensureObserver () {
  if (observer || typeof IntersectionObserver === 'undefined') return observer
  observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return
      const el = entry.target
      const delay = parseInt(el.getAttribute('data-reveal-delay') || '0', 10)
      // 用 CSS 变量传递延迟，避免为每个元素写内联 style
      el.style.setProperty('--reveal-delay', delay + 'ms')
      el.classList.add('is-revealed')
      observer.unobserve(el)
    })
  }, {
    // 元素露出约 12% 或进入视口下方 8% 时触发，保证滚动时"刚好看见就开始动"
    threshold: 0.12,
    rootMargin: '0px 0px -8% 0px'
  })
  return observer
}

/**
 * 初始化滚动浮现。
 * @param {string} scope 作用域选择器，默认整个文档
 */
export function initReveal (scope) {
  const root = scope ? document.querySelector(scope) : document
  if (!root) return
  const targets = root.querySelectorAll('[data-reveal]:not([data-reveal-bound])')
  if (!targets.length) return

  if (prefersReducedMotion()) {
    targets.forEach(showImmediately)
    return
  }

  const obs = ensureObserver()
  if (!obs) {
    // 极老浏览器无 IntersectionObserver：直接显示，绝不隐藏内容
    targets.forEach(showImmediately)
    return
  }
  targets.forEach((el) => {
    el.setAttribute('data-reveal-bound', '1')
    observed.add(el)
    obs.observe(el)
  })
}

/** 路由切换后重置：把新页面的元素重新纳入观察 */
export function resetReveal (scope) {
  const root = scope ? document.querySelector(scope) : document
  if (!root) return
  root.querySelectorAll('[data-reveal][data-reveal-bound]').forEach((el) => {
    el.removeAttribute('data-reveal-bound')
    el.classList.remove('is-revealed')
    el.style.removeProperty('--reveal-delay')
  })
  initReveal(scope)
}

export default initReveal