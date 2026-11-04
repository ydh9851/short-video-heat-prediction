<template>
  <div class="whatif-block">
    <div class="interval-head">
      <div class="section-title">交互式 what-if：如果改这个参数会怎样</div>
      <div class="whatif-actions">
        <el-radio-group :model-value="dimension" size="small" @change="onDimensionChange">
          <el-radio-button value="publishHour">发布时段</el-radio-button>
          <el-radio-button value="publishWeekday">发布星期</el-radio-button>
          <el-radio-button value="publishMonth">发布月份</el-radio-button>
          <el-radio-button value="videoCategory">视频类别</el-radio-button>
        </el-radio-group>
        <el-button size="small" type="primary" plain :loading="loading" @click="$emit('recalc')">
          {{ whatif ? '重新计算' : '开始探索' }}
        </el-button>
      </div>
    </div>
    <div v-if="whatif" class="whatif-body">
      <div ref="chart" class="whatif-chart" />
      <div class="whatif-summary">
        <div class="wi-item">
          <span>当前取值</span>
          <b>{{ whatif.current_label || '—' }}</b>
        </div>
        <div class="wi-item">
          <span>当前预测热度</span>
          <b>{{ formatNum(whatif.baseline) }}</b>
          <em>{{ whatif.baseline_grade }}</em>
        </div>
        <div class="wi-item best">
          <span>最优取值</span>
          <b>{{ whatif.best.label }}</b>
          <em>{{ formatNum(whatif.best.prediction) }} · {{ whatif.best.grade }}</em>
        </div>
        <div class="wi-item">
          <span>可获得增益</span>
          <b class="up">+{{ (whatif.best.gain_pct * 100).toFixed(1) }}%</b>
          <em>{{ formatNum(whatif.best.gain) }}</em>
        </div>
      </div>
      <div class="whatif-note">
        {{ whatif.note }}
      </div>
    </div>
    <app-empty
      v-else
      compact
      title="尚未探索"
      description="选择一个维度后点击「开始探索」，系统会在同一模型上扫描该参数的全部候选取值，给出响应曲线与最优建议"
    />
  </div>
</template>

<script>
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, MarkPointComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { createChart, setChartOption } from '@/utils/chart'
import { whatIfOption } from '../charts/options.mjs'
import { formatNum } from '@/utils/format'
import AppEmpty from '@/components/AppEmpty'

echarts.use([LineChart, GridComponent, TooltipComponent, MarkPointComponent, MarkLineComponent, CanvasRenderer])

/**
 * 交互式 what-if 区块：在同一模型上扫描某个参数的全部候选取值，画出响应曲线。
 *
 * 维度切换与重新计算都交给父组件（需要重新请求后端），
 * 本组件只负责展示与图表生命周期。
 */
export default {
  name: 'WhatIfPanel',
  components: { AppEmpty },
  props: {
    whatif: { type: Object, default: null },
    loading: { type: Boolean, default: false },
    dimension: { type: String, default: 'publishHour' }
  },
  emits: ['recalc', 'dimension-change'],
  data () {
    return { chart: null }
  },
  watch: {
    whatif: {
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
    onDimensionChange (val) {
      this.$emit('dimension-change', val)
    },
    render () {
      const el = this.$refs.chart
      if (!el || !this.whatif) return
      if (!this.chart) this.chart = createChart(echarts, el)
      setChartOption(this.chart, whatIfOption(this.whatif), true)
      this.chart.resize()
    },
    onResize () {
      if (this.chart) this.chart.resize()
    }
  }
}
</script>

<style lang="scss" scoped>
.whatif-block {
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid #e6e2fb;
  border-radius: 10px;
  background: linear-gradient(160deg, #fafaff 0%, #ffffff 100%);
}

.whatif-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.whatif-body {
  margin-top: 10px;
}

.whatif-chart {
  width: 100%;
  height: 260px;
}

.whatif-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
}

.wi-item {
  flex: 1 1 130px;
  border: 1px solid #eceafc;
  border-radius: 8px;
  background: #fff;
  padding: 8px 10px;

  span {
    display: block;
    font-size: 11.5px;
    color: #94a3b8;
    margin-bottom: 2px;
  }

  b {
    font-size: 15px;
    color: #1e293b;
  }

  em {
    display: block;
    font-style: normal;
    font-size: 11.5px;
    color: #94a3b8;
    margin-top: 2px;
  }

  &.best {
    border-color: #fde68a;
    background: #fffbeb;

    b {
      color: #b45309;
    }
  }

  b.up {
    color: #10b981;
  }
}

.whatif-note {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.8;
  color: #64748b;
}
</style>
