/**
 * 图表 option 构造：把 ECharts 配置从组件生命周期里剥离成纯函数。
 *
 * 好处有三：
 *   1. 组件只负责 init / setOption / resize，逻辑边界清晰；
 *   2. option 可在不挂载 DOM 的情况下断言，便于测试；
 *   3. 同一套配色与坐标轴规则集中在此，改视觉不会散落到各处。
 */

/** 千分位整数格式化 */
function fmtInt (v) {
  const n = Number(v)
  if (!isFinite(n)) return '—'
  return Math.round(n).toLocaleString('zh-CN')
}

const AXIS_LINE = { lineStyle: { color: '#e6e9f0' } }
const SPLIT_LINE = { lineStyle: { color: '#f1f3f8' } }
const LABEL = { color: '#94a3b8', fontSize: 11 }

/**
 * 预测区间图：分位数回归给出的 P10 / P50 / P90。
 * 画法是「透明占位条 + 区间条」堆叠，中间用 markLine 标出 P50。
 */
export function intervalOption (iv) {
  const lower = Math.max(iv.p10, 0)
  const span = Math.max(iv.p90 - lower, 1)
  return {
    grid: { left: 10, right: 30, top: 26, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: () => `P10（保守）：${fmtInt(iv.p10)}<br/>P50（中性）：${fmtInt(iv.p50)}<br/>P90（乐观）：${fmtInt(iv.p90)}`
    },
    xAxis: {
      type: 'value',
      splitLine: SPLIT_LINE,
      axisLabel: { ...LABEL, formatter: v => fmtInt(v) }
    },
    yAxis: {
      type: 'category',
      data: ['预测区间'],
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#475569', fontSize: 12 }
    },
    series: [
      {
        name: '下限占位', type: 'bar', stack: 'range', data: [lower],
        itemStyle: { color: 'transparent' }, silent: true, barWidth: 26
      },
      {
        name: '区间',
        type: 'bar',
        stack: 'range',
        data: [span],
        barWidth: 26,
        itemStyle: {
          borderRadius: 8,
          color: {
            type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [{ offset: 0, color: '#c7cbf7' }, { offset: 1, color: '#8b5cf6' }]
          }
        },
        label: {
          show: true, position: 'inside', color: '#fff', fontWeight: 600,
          formatter: () => `P10 ${fmtInt(iv.p10)}`
        },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#1e293b', width: 2, type: 'solid' },
          label: {
            formatter: () => `P50 ${fmtInt(iv.p50)}`,
            position: 'end', color: '#1e293b', fontWeight: 600, fontSize: 11
          },
          data: [{ xAxis: iv.p50 }]
        }
      }
    ]
  }
}
/** 模型中文名映射 */
const MODEL_NAMES = {
  lgbm: 'LightGBM', xgb: 'XGBoost', rf: '随机森林',
  lr: '线性回归', knn: 'K 近邻', dt: '决策树', svm: 'SVR'
}

/**
 * 多模型效果对比图：各模型在测试集上的 R²(log)。
 * 最优模型用渐变柱，其余用浅色，视觉上直接指向结论。
 */
export function modelOption (metrics) {
  const list = (metrics || []).filter(m => m.trained)
  return {
    grid: { left: 6, right: 16, top: 20, bottom: 6, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: p => `${p[0].name}<br/>R²(log) = ${Number(p[0].value).toFixed(4)}`
    },
    xAxis: {
      type: 'category',
      data: list.map(m => MODEL_NAMES[m.model] || m.model),
      axisLine: AXIS_LINE,
      axisTick: { show: false },
      axisLabel: { color: '#64748b', fontSize: 11, interval: 0 }
    },
    yAxis: { type: 'value', max: 1, splitLine: SPLIT_LINE, axisLabel: LABEL },
    series: [{
      type: 'bar',
      data: list.map(m => ({
        value: m.r2,
        itemStyle: {
          borderRadius: [7, 7, 0, 0],
          color: m.model === 'lgbm'
            ? {
                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{ offset: 0, color: '#a855f7' }, { offset: 1, color: '#6366f1' }]
              }
            : '#c7cbf7'
        }
      })),
      barWidth: '42%',
      label: {
        show: true, position: 'top', color: '#64748b', fontSize: 11,
        formatter: p => Number(p.value).toFixed(3)
      }
    }]
  }
}

/**
 * what-if 响应曲线：某个参数取遍全部候选值时的预测热度。
 * 橙色标记为最优取值，绿色虚线标出当前取值。
 */
export function whatIfOption (whatif) {
  const items = (whatif && whatif.candidates) || []
  const labels = items.map(c => c.label)
  const values = items.map(c => Math.round(c.prediction))
  const currentLabel = whatif ? whatif.current_label : ''
  const curIdx = labels.indexOf(currentLabel)
  return {
    grid: { left: 58, right: 24, top: 28, bottom: 34 },
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        const c = items[params[0].dataIndex]
        if (!c) return ''
        const sign = c.gain_pct >= 0 ? '+' : ''
        return `${c.label}<br/>预测热度：${Number(c.prediction).toLocaleString()}<br/>`
          + `等级：${c.grade}<br/>相对当前：${sign}${(c.gain_pct * 100).toFixed(1)}%`
      }
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { color: '#94a3b8', fontSize: 11, interval: labels.length > 12 ? 1 : 0 },
      axisLine: { lineStyle: { color: 'rgba(148,163,184,0.25)' } }
    },
    yAxis: {
      type: 'value',
      name: '热度',
      nameTextStyle: { color: '#94a3b8', fontSize: 11 },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
      splitLine: { lineStyle: { color: 'rgba(148,163,184,0.15)' } }
    },
    series: [{
      type: 'line',
      smooth: true,
      data: values,
      symbolSize: 6,
      lineStyle: { width: 2, color: '#6366f1' },
      itemStyle: { color: '#6366f1' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(99,102,241,0.28)' },
            { offset: 1, color: 'rgba(99,102,241,0.02)' }
          ]
        }
      },
      markPoint: {
        symbolSize: 44,
        label: { color: '#fff', fontSize: 10, formatter: '最优' },
        itemStyle: { color: '#f59e0b' },
        data: [{ type: 'max', name: '最优' }]
      },
      markLine: {
        symbol: 'none',
        lineStyle: { color: '#10b981', type: 'dashed', width: 1.5 },
        label: { color: '#10b981', fontSize: 10, formatter: '当前 ' + (currentLabel || '') },
        data: [{ xAxis: curIdx >= 0 ? curIdx : 0 }]
      }
    }]
  }
}