/**
 * 图表初始化的统一封装。
 *
 * 统一四件事，避免每个页面各写一套：
 *   1. 动画参数：入场用较长的减速曲线（图表"长出来"而不是"跳出来"），
 *      更新用较短的曲线，切换实验时不会拖沓；
 *   2. 主题令牌：坐标轴与分割线的颜色统一取自全局 CSS 变量对应的常量；
 *   3. 尺寸兜底：容器宽高为 0 时（隐藏 Tab、折叠面板）延迟初始化，
 *      避免出现"图表不显示且不再重绘"的偶发问题；
 *   4. 主题：自动注册并使用 app 主题，统一全站图表配色。
 */

import { ensureAppTheme, APP_CHART_THEME } from './echartsTheme'

/** 入场动画：700ms 减速，比 ECharts 默认的 1000ms 更利落 */
export const CHART_ANIMATION = {
  animationDuration: 700,
  animationDurationUpdate: 360,
  animationEasing: 'cubicOut',
  animationEasingUpdate: 'cubicOut'
}

/** 与 styles/theme.scss 中的轴线、文本色保持一致 */
export const AXIS_COLOR = '#94a3b8'
export const TEXT_COLOR = '#475569'
export const SPLIT_COLOR = 'rgba(148, 163, 184, 0.18)'

/**
 * 创建图表实例。
 * @param {*} echarts echarts/core 命名空间
 * @param {HTMLElement} el 容器
 * @param {object} opts echarts.init 的额外选项
 */
export function createChart (echarts, el, opts) {
  if (!el) return null
  ensureAppTheme(echarts)
  const chart = echarts.init(el, APP_CHART_THEME, opts)
  // 容器尺寸为 0 时（隐藏面板内）延后初始化，等可见后再画
  if (!el.clientWidth || !el.clientHeight) {
    setTimeout(() => {
      if (!chart.isDisposed()) chart.resize()
    }, 60)
  }
  return chart
}

/**
 * 设置图表配置，自动补齐统一动画参数。
 * @param {*} chart 图表实例
 * @param {object} option 配置
 * @param {boolean} notMerge 是否不合并旧配置（切换实验时传 true）
 */
export function setChartOption (chart, option, notMerge) {
  if (!chart) return
  chart.setOption(Object.assign({ animationDuration: CHART_ANIMATION.animationDuration }, option), notMerge)
}
