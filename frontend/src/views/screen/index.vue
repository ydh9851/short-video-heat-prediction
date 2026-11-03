<template>
  <div class="screen-page" v-loading="loading">
    <!-- 顶部标题栏 -->
    <div class="screen-head">
      <div class="head-left">
        <div class="head-title">短视频热度数据大屏</div>
        <div class="head-sub">多平台数据集总览 · 类别与热度分布</div>
      </div>
      <div class="head-right">
        <span class="clock">{{ now }}</span>
        <el-button size="small" :loading="loading" @click="loadAll">刷新</el-button>
      </div>
    </div>

    <!-- 关键指标 -->
    <div class="kpi-row">
      <div v-for="k in kpis" :key="k.label" class="kpi">
        <div class="kpi-label">{{ k.label }}</div>
        <div class="kpi-value">{{ k.value }}</div>
        <div class="kpi-sub">{{ k.sub }}</div>
      </div>
    </div>

    <!-- 图表区 -->
    <div class="chart-grid">
      <div class="chart-card wide">
        <div class="chart-title">各平台样本量对比（对数刻度）</div>
        <div ref="platformChart" class="chart-body"></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">热度等级分布</div>
        <div ref="gradeChart" class="chart-body"></div>
      </div>
      <div class="chart-card">
        <div class="chart-title">内容类别 Top 10</div>
        <div ref="categoryChart" class="chart-body"></div>
      </div>
      <div class="chart-card wide">
        <div class="chart-title">热度分位数（加权互动量，对数刻度）</div>
        <div ref="quantileChart" class="chart-body"></div>
      </div>
    </div>

    <!-- 实时预测流：让大屏反映"系统是活的" -->
    <div class="stream-card">
      <div class="stream-head">
        <span class="stream-title">
          <i class="live-dot" />实时预测流
        </span>
        <span class="stream-sub">最近 {{ stream.length }} 条预测记录 · 每 5 秒刷新</span>
      </div>
      <div class="stream-body">
        <div v-if="!stream.length" class="stream-empty">暂无预测记录</div>
        <div v-for="(r, i) in stream" :key="r.id" class="stream-row" :class="{ fresh: i === 0 && r.fresh }">
          <span class="c-time">{{ (r.createTime || '').slice(11) }}</span>
          <span class="c-cat">{{ r.videoCategory }}</span>
          <span class="c-fans">{{ fmtFans(r.authorFans) }} 粉丝</span>
          <span class="c-hour">{{ r.publishHour }}:00 发布</span>
          <span class="c-heat">{{ fmtInt(r.prediction) }}</span>
          <span class="c-grade" :class="gradeClass(r.grade)">{{ r.grade }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import dataApi from '@/api/data'
import predictApi from '@/api/predict'

echarts.use([BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const AXIS_COLOR = '#64748b'
const TEXT_COLOR = '#cbd5e1'
const SPLIT_COLOR = 'rgba(148, 163, 184, 0.18)'

export default {
  name: 'ScreenPage',
  data () {
    return {
      loading: true,
      now: '',
      clockTimer: null,
      platformMeta: [],
      platforms: [],
      ov: {},
      charts: {},
      // 实时预测流
      stream: [],
      streamTimer: null,
      lastStreamId: null
    }
  },
  computed: {
    kpis () {
      const heat = this.ov.heat || {}
      const totalRows = this.platforms.reduce((sum, p) => sum + (p.rows || 0), 0)
      return [
        { label: '样本总量', value: this.fmtInt(totalRows), sub: this.platforms.length + ' 个平台原始数据' },
        { label: '内容类别', value: (this.ov.categoryCount || 0) + ' 类', sub: this.ov.displayName || '默认平台' },
        { label: '热度中位数', value: this.fmtInt(heat.median), sub: '加权互动量' },
        { label: '热度 P90', value: this.fmtInt(heat.p90), sub: '头部爆款水位' }
      ]
    }
  },
  created () {
    this.loadAll()
  },
  mounted () {
    this.tick()
    this.clockTimer = setInterval(this.tick, 1000)
    this.loadStream()
    this.streamTimer = setInterval(this.loadStream, 5000)
    window.addEventListener('resize', this.resizeCharts)
  },
  beforeUnmount () {
    if (this.clockTimer) clearInterval(this.clockTimer)
    if (this.streamTimer) clearInterval(this.streamTimer)
    window.removeEventListener('resize', this.resizeCharts)
    Object.values(this.charts).forEach(c => c && c.dispose())
    this.charts = {}
  },
  methods: {
    /**
     * 拉取最近预测记录并渲染成滚动流。
     * 首次拉取或出现新记录时，最新一条会带高亮（fresh），让大屏一眼能看出"系统在跑"。
     */
    loadStream () {
      predictApi.logs({ page: 1, size: 10 }).then(re => {
        const list = (re.response && re.response.list) || []
        const newest = list.length ? list[0].id : null
        const isNew = this.lastStreamId != null && newest != null && newest > this.lastStreamId
        this.lastStreamId = newest
        this.stream = list.map((r, i) => Object.assign({}, r, { fresh: isNew && i === 0 }))
      }).catch(() => { /* 大屏静默失败：不影响其它面板 */ })
    },
    fmtFans (v) {
      const n = Number(v)
      if (!isFinite(n)) return '—'
      if (n >= 10000) return (n / 10000).toFixed(1) + ' 万'
      return String(Math.round(n))
    },
    gradeClass (grade) {
      if (grade === '高热度') return 'g-high'
      if (grade === '中热度') return 'g-mid'
      return 'g-low'
    },
    tick () {
      const d = new Date()
      const pad = n => String(n).padStart(2, '0')
      this.now = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    },
    fmtInt (v) {
      const n = Number(v)
      if (!isFinite(n)) return '—'
      return n.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
    },
    loadAll () {
      this.loading = true
      dataApi.platforms().then(re => {
        const d = re.response || {}
        this.platforms = d.platforms || []
        this.platformMeta = this.platforms
        const target = d.defaultPlatform || (this.platforms[0] && this.platforms[0].platform) || 'douyin'
        return dataApi.overview(target)
      }).then(re => {
        this.ov = (re && re.response) || {}
        this.loading = false
        this.$nextTick(this.renderCharts)
      }).catch(() => {
        this.loading = false
        this.$nextTick(this.renderCharts)
      })
    },
    chartOf (refName) {
      const el = this.$refs[refName]
      if (!el) return null
      if (!this.charts[refName]) {
        this.charts[refName] = echarts.init(el)
      }
      return this.charts[refName]
    },
    resizeCharts () {
      Object.values(this.charts).forEach(c => c && c.resize())
    },
    renderCharts () {
      this.renderPlatform()
      this.renderGrade()
      this.renderCategory()
      this.renderQuantile()
    },
    renderPlatform () {
      const chart = this.chartOf('platformChart')
      if (!chart) return
      const names = this.platforms.map(p => p.displayName || p.platform)
      const values = this.platforms.map(p => Math.max(p.rows || 0, 1))
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: 60, right: 30, top: 30, bottom: 30 },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: params => `${params[0].name}<br/>样本量：${Number(params[0].value).toLocaleString()}`
        },
        xAxis: { type: 'category', data: names, axisLabel: { color: TEXT_COLOR }, axisLine: { lineStyle: { color: SPLIT_COLOR } } },
        yAxis: {
          type: 'log',
          min: 1,
          axisLabel: { color: TEXT_COLOR },
          splitLine: { lineStyle: { color: SPLIT_COLOR } }
        },
        series: [{
          type: 'bar',
          data: values,
          barWidth: '45%',
          itemStyle: {
            borderRadius: [6, 6, 0, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#38bdf8' },
              { offset: 1, color: '#6366f1' }
            ])
          }
        }]
      }, true)
    },
    renderGrade () {
      const chart = this.chartOf('gradeChart')
      if (!chart) return
      const dist = this.ov.gradeDistribution || {}
      // 后端返回 [{ grade, count }]，ECharts 饼图需要 [{ name, value }]，这里做一次字段归一
      const data = Array.isArray(dist)
        ? dist.map(d => ({ name: d.name || d.grade, value: Number(d.value != null ? d.value : d.count) || 0 }))
        : Object.keys(dist).map(k => ({ name: k, value: dist[k] }))
      chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}：{c} 条（{d}%）' },
        legend: { bottom: 0, textStyle: { color: TEXT_COLOR } },
        series: [{
          type: 'pie',
          radius: ['48%', '72%'],
          center: ['50%', '45%'],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: '#0b1220', borderWidth: 3 },
          label: { color: TEXT_COLOR, formatter: '{b}\n{d}%' },
          data,
          color: ['#38bdf8', '#8b5cf6', '#fbbf24']
        }]
      }, true)
    },
    renderCategory () {
      const chart = this.chartOf('categoryChart')
      if (!chart) return
      const cats = (this.ov.categories || []).slice(0, 10).map(c => ({ name: c.name, value: c.count }))
      cats.reverse()
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: 70, right: 40, top: 20, bottom: 20 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        xAxis: { type: 'value', axisLabel: { color: TEXT_COLOR }, splitLine: { lineStyle: { color: SPLIT_COLOR } } },
        yAxis: { type: 'category', data: cats.map(c => c.name), axisLabel: { color: TEXT_COLOR }, axisLine: { lineStyle: { color: SPLIT_COLOR } } },
        series: [{
          type: 'bar',
          data: cats.map(c => c.value),
          barWidth: '55%',
          itemStyle: { borderRadius: [0, 6, 6, 0], color: '#22d3ee' },
          label: { show: true, position: 'right', color: TEXT_COLOR, fontSize: 11 }
        }]
      }, true)
    },
    renderQuantile () {
      const chart = this.chartOf('quantileChart')
      if (!chart) return
      const heat = this.ov.heat || {}
      const labels = ['Q25', '中位数', 'Q75', 'P90', '最大值']
      const values = [heat.q25, heat.median, heat.q75, heat.p90, heat.max].map(v => Math.max(Number(v) || 1, 1))
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: 80, right: 30, top: 30, bottom: 30 },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: params => `${params[0].name}<br/>热度：${Number(params[0].value).toLocaleString()}`
        },
        xAxis: { type: 'category', data: labels, axisLabel: { color: TEXT_COLOR }, axisLine: { lineStyle: { color: SPLIT_COLOR } } },
        yAxis: { type: 'log', min: 1, axisLabel: { color: TEXT_COLOR }, splitLine: { lineStyle: { color: SPLIT_COLOR } } },
        series: [{
          type: 'bar',
          data: values,
          barWidth: '40%',
          itemStyle: {
            borderRadius: [6, 6, 0, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#a855f7' },
              { offset: 1, color: '#38bdf8' }
            ])
          }
        }]
      }, true)
    }
  }
}
</script>

<style lang="scss" scoped>
.screen-page {
  min-height: calc(100vh - 120px);
  padding: 16px 20px 24px;
  border-radius: 12px;
  background: radial-gradient(circle at 20% 0%, #16233d 0%, #0b1220 55%, #070c16 100%);
  color: #e2e8f0;
}

.screen-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);

  .head-title {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 2px;
    background: linear-gradient(90deg, #38bdf8, #a855f7);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  .head-sub {
    margin-top: 4px;
    font-size: 12px;
    color: #7c8ba1;
  }

  .head-right {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .clock {
    font-family: 'Consolas', 'Menlo', monospace;
    font-size: 14px;
    color: #38bdf8;
  }
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin: 16px 0;

  .kpi {
    padding: 14px 18px;
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 10px;
    background: linear-gradient(160deg, rgba(56, 189, 248, 0.12), rgba(99, 102, 241, 0.05));
  }

  .kpi-label {
    font-size: 12px;
    color: #8ba0b8;
  }

  .kpi-value {
    margin: 6px 0 4px;
    font-size: 26px;
    font-weight: 700;
    color: #e0f2fe;
  }

  .kpi-sub {
    font-size: 12px;
    color: #64748b;
  }
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.chart-card {
  padding: 12px 16px 6px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.55);

  &.wide {
    grid-column: span 2;
  }
}

.chart-title {
  margin-bottom: 6px;
  font-size: 13px;
  color: #93c5fd;
  letter-spacing: 1px;
}

.chart-body {
  width: 100%;
  height: 260px;
}

.chart-card.wide .chart-body {
  height: 220px;
}

@media (max-width: 1200px) {
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .chart-grid {
    grid-template-columns: 1fr;
  }
  .chart-card.wide {
    grid-column: span 1;
  }
}

/* ============ 实时预测流 ============ */
.stream-card {
  margin-top: 14px;
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 10px;
  background: linear-gradient(160deg, rgba(56, 189, 248, 0.08), rgba(15, 23, 42, 0.55));
  padding: 12px 16px 14px;
}

.stream-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.stream-title {
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.6);
  animation: live-pulse 2s infinite;
}

@keyframes live-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.55);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(52, 211, 153, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(52, 211, 153, 0);
  }
}

.stream-sub {
  font-size: 12px;
  color: #64748b;
}

.stream-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 188px;
  overflow-y: auto;
}

.stream-row {
  display: grid;
  grid-template-columns: 82px 90px 120px 100px 1fr 76px;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #cbd5e1;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.35);
}

.stream-row.fresh {
  background: rgba(52, 211, 153, 0.12);
  animation: fresh-fade 2.4s ease-out;
}

@keyframes fresh-fade {
  0% {
    background: rgba(52, 211, 153, 0.28);
  }
  100% {
    background: rgba(15, 23, 42, 0.35);
  }
}

.c-time {
  color: #64748b;
  font-variant-numeric: tabular-nums;
}

.c-cat {
  color: #e2e8f0;
  font-weight: 600;
}

.c-fans,
.c-hour {
  color: #94a3b8;
  font-size: 12px;
}

.c-heat {
  color: #38bdf8;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.c-grade {
  text-align: center;
  border-radius: 4px;
  padding: 2px 0;
  font-size: 12px;
}

.g-high {
  color: #fca5a5;
  background: rgba(248, 113, 113, 0.16);
}

.g-mid {
  color: #fcd34d;
  background: rgba(252, 211, 77, 0.14);
}

.g-low {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.14);
}

.stream-empty {
  font-size: 13px;
  color: #64748b;
  padding: 14px 8px;
  text-align: center;
}

/* ============================================================
 * 大屏样式覆盖（在前面的基础样式之上）
 * ------------------------------------------------------------
 * 深色场景下的玻璃质感与浅色不同：靠低透明度冷色叠加 + 发丝边框 +
 * 顶部微光；深底上单纯加 blur 几乎不可见，反而发灰。
 * ============================================================ */
.screen-page {
  position: relative;
  padding: 28px 32px 32px;
  border-radius: 20px;
  background:
    radial-gradient(1200px 520px at 18% -10%, rgba(56, 189, 248, .16), transparent 60%),
    radial-gradient(900px 460px at 88% -6%, rgba(139, 92, 246, .16), transparent 58%),
    radial-gradient(circle at 50% 120%, rgba(99, 102, 241, .12), transparent 62%),
    linear-gradient(180deg, #0b1220 0%, #070c16 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .06), var(--shadow-lift);
  overflow: hidden;
}

.screen-head {
  align-items: flex-end;
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(148, 163, 184, .14);

  .head-title {
    font-size: clamp(26px, 2.6vw, 38px);
    font-weight: 700;
    letter-spacing: -.022em;
    line-height: 1.1;
    background: linear-gradient(120deg, #f8fafc 20%, #a5b4fc 60%, #c4b5fd 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  .head-sub {
    font-size: 14px;
    color: #7c8aa5;
    letter-spacing: .02em;
    margin-top: 8px;
  }

  .clock {
    font-size: 15px;
    color: #cbd5e1;
    font-variant-numeric: tabular-nums;
    letter-spacing: .04em;
  }
}

/* KPI：半透明 + 发丝边 + 悬停抬升，数字用大字号做视觉锚点 */
.kpi-row {
  gap: 16px;
  margin: 22px 0 18px;

  .kpi {
    position: relative;
    padding: 18px 20px;
    border-radius: 16px;
    border: 1px solid rgba(148, 163, 184, .16);
    background: linear-gradient(160deg, rgba(56, 189, 248, .10), rgba(15, 23, 42, .5) 60%);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .07);
    transition:
      transform var(--dur-base) var(--spring-soft),
      border-color var(--dur-base) var(--spring-smooth),
      box-shadow var(--dur-base) var(--spring-smooth);

    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 12%;
      right: 12%;
      height: 1px;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, .28), transparent);
      pointer-events: none;
    }

    &:hover {
      transform: translate3d(0, -4px, 0);
      border-color: rgba(56, 189, 248, .32);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, .1), 0 18px 40px rgba(0, 0, 0, .45);
    }
  }

  .kpi-label {
    font-size: 12px;
    color: #7c8aa5;
    letter-spacing: .06em;
  }

  .kpi-value {
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -.028em;
    line-height: 1.15;
    margin-top: 6px;
    background: linear-gradient(140deg, #f8fafc, #7dd3fc 90%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  .kpi-sub {
    font-size: 11.5px;
    color: #64748b;
    margin-top: 4px;
  }
}

/* 图表卡：深色玻璃 */
.chart-card {
  position: relative;
  padding: 16px 18px 10px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, .14);
  background: rgba(15, 23, 42, .42);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .05);
  transition:
    transform var(--dur-base) var(--spring-soft),
    border-color var(--dur-base) var(--spring-smooth);

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 10%;
    right: 10%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, .22), transparent);
    pointer-events: none;
  }

  &:hover {
    transform: translate3d(0, -3px, 0);
    border-color: rgba(148, 163, 184, .26);
  }

  .chart-title {
    font-size: 13.5px;
    font-weight: 600;
    letter-spacing: .02em;
    color: #cbd5e1;
  }
}

/* 实时流卡同样升级材质 */
.stream-card {
  border-radius: 16px;
  border-color: rgba(56, 189, 248, .2);
  background: linear-gradient(160deg, rgba(56, 189, 248, .07), rgba(15, 23, 42, .5) 60%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .06);
}

@media (max-width: 1200px) {
  .screen-page {
    padding: 18px 16px 22px;
  }
}
</style>
