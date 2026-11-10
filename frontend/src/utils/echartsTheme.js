/**
 * 全站统一的 ECharts 主题。
 *
 * 颜色 / 文字 / 轴线令牌与 styles/theme.scss 对齐：
 * 页面用 CSS 变量，图表用同一组十六进制值，避免两套视觉体系。
 * 通过 ensureAppTheme 做一次性注册，任何 echarts 命名空间都只注册一次。
 */

export const APP_CHART_THEME = 'app'

const THEME = {
  color: ['#6366f1', '#8b5cf6', '#38bdf8', '#10b981', '#f59e0b', '#ef4444', '#14b8a6', '#a855f7'],
  backgroundColor: 'transparent',
  textStyle: {
    fontFamily: 'Inter, "PingFang SC", "Microsoft YaHei", sans-serif',
    color: '#475569'
  },
  title: {
    textStyle: { color: '#1e293b', fontWeight: 600, fontSize: 14 }
  },
  legend: {
    textStyle: { color: '#64748b', fontSize: 11 },
    itemWidth: 10,
    itemHeight: 10
  },
  tooltip: {
    backgroundColor: 'rgba(255,255,255,.98)',
    borderColor: '#e6e9f0',
    borderWidth: 1,
    textStyle: { color: '#334155', fontSize: 12 },
    extraCssText: 'box-shadow:0 8px 24px rgba(24,32,72,.12);border-radius:10px;'
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#e6e9f0' } },
    axisTick: { show: false },
    axisLabel: { color: '#94a3b8', fontSize: 11 },
    splitLine: { show: false }
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#94a3b8', fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(148,163,184,.16)' } }
  },
  grid: { left: 10, right: 24, top: 24, bottom: 8, containLabel: true },
  bar: { itemStyle: { borderRadius: [6, 6, 0, 0] } },
  line: { symbolSize: 6, smooth: true, lineStyle: { width: 2 } },
  pie: { itemStyle: { borderColor: '#fff', borderWidth: 2 } }
}

const registered = new WeakSet()

/** 注册 app 主题（同一 echarts 命名空间只注册一次） */
export function ensureAppTheme (echarts) {
  if (!echarts || registered.has(echarts)) return
  echarts.registerTheme(APP_CHART_THEME, THEME)
  registered.add(echarts)
}
