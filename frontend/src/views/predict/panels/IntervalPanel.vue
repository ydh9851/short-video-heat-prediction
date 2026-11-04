<template>
  <div class="interval-block">
    <div class="interval-head">
      <div class="section-title">预测区间（LightGBM 分位数回归）</div>
      <span v-if="interval" class="coverage-tip">
        测试集区间覆盖率 {{ pct(interval.coverage_report && interval.coverage_report.coverage) }}
      </span>
    </div>
    <div v-if="interval" ref="chart" class="interval-chart" />
    <app-empty v-else compact title="区间模型加载中…" description="正在计算 LightGBM 分位数回归的 P10 / P50 / P90" />
    <div v-if="interval" class="interval-legend">
      <span><i class="dot p10" />P10 保守 {{ formatNum(interval.interval.p10) }}</span>
      <span><i class="dot p50" />P50 中性 {{ formatNum(interval.interval.p50) }}</span>
      <span><i class="dot p90" />P90 乐观 {{ formatNum(interval.interval.p90) }}</span>
      <span class="muted">区间宽度 {{ formatNum(interval.width) }}</span>
    </div>
    <div v-if="interval" class="interval-warn">
      分位数回归只做事后检验：测试集覆盖率 {{ pct(interval.coverage_report && interval.coverage_report.coverage) }}，
      低于名义 80%，且没有覆盖保证。下方保形区间可作对照。
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { createChart, setChartOption } from '@/utils/chart'
import { intervalOption } from '../charts/options.mjs'
import { formatNum, pct } from '@/utils/format'
import AppEmpty from '@/components/AppEmpty'

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, MarkLineComponent, CanvasRenderer])

/**
 * 预测区间区块：展示 LightGBM 分位数回归给出的 P10 / P50 / P90。
 *
 * 图表的 option 构造在 charts/options.mjs 中，这里只负责实例生命周期。
 */
export default {
  name: 'IntervalPanel',
  components: { AppEmpty },
  props: {
    interval: { type: Object, default: null }
  },
  data () {
    return { chart: null }
  },
  watch: {
    interval: {
      handler () {
        this.$nextTick(this.render)
      },
      immediate: true
    }
  },
  mounted () {
    window.addEventListener('resize', this.onResize)
  },
  beforeUnmount () {
    window.removeEventListener('resize', this.onResize)
    if (this.chart) {
      this.chart.dispose()
      this.chart = null
    }
  },
  methods: {
    formatNum,
    pct,
    render () {
      const el = this.$refs.chart
      if (!el || !this.interval) return
      if (!this.chart) this.chart = createChart(echarts, el)
      setChartOption(this.chart, intervalOption(this.interval.interval), true)
      this.chart.resize()
    },
    onResize () {
      if (this.chart) this.chart.resize()
    }
  }
}
</script>

<style lang="scss" scoped>
.interval-block {
  .interval-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;

    .section-title { margin-bottom: 0; }
  }
  .coverage-tip {
    font-size: 12px;
    color: #10b981;
    font-weight: 600;
  }
}

.interval-chart {
  width: 100%;
  height: 130px;
}

.interval-legend {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  align-items: center;
  font-size: 12.5px;
  color: #475569;
  padding-top: 4px;

  .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;

    &.p10 { background: #c7cbf7; }
    &.p50 { background: #1e293b; }
    &.p90 { background: #8b5cf6; }
  }
  .muted { color: #94a3b8; }
}

.interval-warn {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.75;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 8px 10px;
}
</style>
