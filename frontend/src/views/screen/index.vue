<template>
  <div class="screen-root" v-loading="loading">
    <!-- ============ 顶部工具栏（浮在各幕之上） ============ -->
    <div class="screen-toolbar">
      <div class="tb-left">
        <div class="tb-title">短视频热度数据大屏</div>
        <div class="tb-sub">四幕剧本 · 键盘 ← / → 切换 · F 全屏 · ESC 退出</div>
      </div>
      <div class="tb-right">
        <!-- 幕指示 -->
        <div class="scene-indicator">
          <button
            v-for="(s, i) in scenes"
            :key="i"
            type="button"
            class="scene-dot"
            :class="{ active: currentScene === i }"
            @click="gotoScene(i)"
            :title="s.title">
            {{ i + 1 }}
          </button>
        </div>
        <el-tag size="small" effect="plain" class="current-scene-tag">
          幕 {{ currentScene + 1 }} · {{ scenes[currentScene].title }}
        </el-tag>
        <div class="tb-divider" />
        <el-button size="small" circle @click="prevScene" title="上一幕 (←)">‹</el-button>
        <el-button size="small" circle @click="nextScene" title="下一幕 (→)">›</el-button>
        <div class="tb-divider" />
        <el-tooltip :content="autoPlay ? '暂停自动播放 (空格)' : '开启自动播放 (空格)'" placement="bottom">
          <el-button size="small" :type="autoPlay ? 'success' : 'default'" @click="toggleAutoPlay">
            {{ autoPlay ? '⏸ 自动播放' : '▶ 自动播放' }}
          </el-button>
        </el-tooltip>
        <div class="tb-divider" />
        <el-tooltip :content="isFullscreen ? '退出全屏 (ESC)' : '全屏投屏 (F11/F)'" placement="bottom">
          <el-button size="small" type="primary" :icon="isFullscreen ? '' : ''" @click="toggleFullscreen">
            {{ isFullscreen ? '⛶ 退出全屏' : '⛶ 全屏投屏' }}
          </el-button>
        </el-tooltip>
        <el-button size="small" @click="loadAll" title="刷新">刷新</el-button>
        <el-button size="small" text @click="$router.back()" title="返回上一页">← 返回</el-button>
      </div>
    </div>

    <!-- ============ 幕 1：数据可信（KPI + 平台柱图） ============ -->
    <div class="scene" :class="{ active: currentScene === 0 }">
      <div class="kpi-row">
        <div v-for="k in kpis" :key="k.label" class="kpi">
          <div class="kpi-label">{{ k.label }}</div>
          <div class="kpi-value">{{ k.value }}</div>
          <div class="kpi-sub">{{ k.sub }}</div>
        </div>
      </div>
      <div class="scene-body">
        <div class="chart-card wide">
          <div class="chart-title">各平台样本量对比（对数刻度）</div>
          <div ref="platformChart" class="chart-body tall" />
        </div>
      </div>
    </div>

    <!-- ============ 幕 2：热度分级与内容偏好 ============ -->
    <div class="scene" :class="{ active: currentScene === 1 }">
      <div class="scene-body two-col">
        <div class="chart-card">
          <div class="chart-title">热度等级分布</div>
          <div ref="gradeChart" class="chart-body tall" />
        </div>
        <div class="chart-card">
          <div class="chart-title">内容类别 Top 10</div>
          <div ref="categoryChart" class="chart-body tall" />
        </div>
      </div>
    </div>

    <!-- ============ 幕 3：热度分布 ============ -->
    <div class="scene" :class="{ active: currentScene === 2 }">
      <div class="scene-body">
        <div class="chart-card wide">
          <div class="chart-title">热度分位数（加权互动量，对数刻度）</div>
          <div ref="quantileChart" class="chart-body tall" />
        </div>
      </div>
    </div>

    <!-- ============ 幕 4：系统在跑（实时预测流） ============ -->
    <div class="scene" :class="{ active: currentScene === 3 }">
      <div class="stream-full">
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

    <!-- ============ 底部时钟 ============ -->
    <div class="screen-footer">
      <span class="clock">{{ now }}</span>
      <span class="kbd-hint">键盘: ← → 切换 · 1-4 跳幕 · F11 全屏 · 空格 自动播放 · ESC 退出</span>
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
      // 四幕剧本
      scenes: [
        { title: '数据可信' },
        { title: '热度分级与内容偏好' },
        { title: '热度分布' },
        { title: '系统在跑' }
      ],
      currentScene: 0,
      autoPlay: false,
      autoPlayTimer: null,
      sceneTimer: 10000,
      // 实时预测流
      stream: [],
      streamTimer: null,
      lastStreamId: null,
      // 全屏
      isFullscreen: false
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
    window.addEventListener('keydown', this.onKeyDown)
    window.addEventListener('focus', this.onWindowFocus)
    window.addEventListener('blur', this.onWindowBlur)
    document.addEventListener('fullscreenchange', this.onFullscreenChange)
  },
  beforeUnmount () {
    if (this.clockTimer) clearInterval(this.clockTimer)
    if (this.streamTimer) clearInterval(this.streamTimer)
    if (this.autoPlayTimer) clearInterval(this.autoPlayTimer)
    window.removeEventListener('resize', this.resizeCharts)
    window.removeEventListener('keydown', this.onKeyDown)
    window.removeEventListener('focus', this.onWindowFocus)
    window.removeEventListener('blur', this.onWindowBlur)
    document.removeEventListener('fullscreenchange', this.onFullscreenChange)
    Object.values(this.charts).forEach(c => c && c.dispose())
    this.charts = {}
    // 若因全屏进入而退出全屏
    if (document.fullscreenElement) {
      try { document.exitFullscreen() } catch (e) { /* ignore */ }
    }
  },
  watch: {
    currentScene () {
      // 幕切换时触发 ECharts resize，保证新幕的容器拿到正确尺寸
      this.$nextTick(this.resizeCharts)
    }
  },
  methods: {
    // ======== 幕切换 ========
    gotoScene (i) {
      this.currentScene = Math.max(0, Math.min(this.scenes.length - 1, i))
    },
    nextScene () { this.gotoScene((this.currentScene + 1) % this.scenes.length) },
    prevScene () { this.gotoScene((this.currentScene - 1 + this.scenes.length) % this.scenes.length) },

    // ======== 自动播放 ========
    toggleAutoPlay () {
      this.autoPlay = !this.autoPlay
      this.applyAutoPlayTimer()
    },
    applyAutoPlayTimer () {
      if (this.autoPlayTimer) {
        clearInterval(this.autoPlayTimer)
        this.autoPlayTimer = null
      }
      if (this.autoPlay) {
        this.autoPlayTimer = setInterval(() => {
          // 鼠标悬停图表时不自动切换（通过 el-tooltip 里的悬停判断：DOM 上有 tooltip 打开）
          const hovered = document.querySelector('.el-tooltip__popper[aria-hidden="false"], .el-popper[aria-hidden="false"]')
          if (!hovered) this.nextScene()
        }, this.sceneTimer)
      }
    },
    onWindowBlur () { this.autoPlay && clearInterval(this.autoPlayTimer) },
    onWindowFocus () { this.autoPlay && this.applyAutoPlayTimer() },

    // ======== 键盘 ========
    onKeyDown (e) {
      // 输入框内不拦截
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
      const k = e.key
      if (k === 'ArrowLeft') { e.preventDefault(); this.prevScene() }
      else if (k === 'ArrowRight') { e.preventDefault(); this.nextScene() }
      else if (k === ' ') { e.preventDefault(); this.toggleAutoPlay() }
      else if (k >= '1' && k <= '4') { this.gotoScene(Number(k) - 1) }
      else if (k === 'f' || k === 'F') { e.preventDefault(); this.toggleFullscreen() }
      // ESC 退出全屏由浏览器原生处理 + fullscreenchange 事件同步
    },

    // ======== 全屏 ========
    toggleFullscreen () {
      const el = document.documentElement
      if (!document.fullscreenElement) {
        try { el.requestFullscreen() } catch (e) { /* 旧浏览器不支持 */ }
      } else {
        try { document.exitFullscreen() } catch (e) { /* ignore */ }
      }
    },
    onFullscreenChange () {
      this.isFullscreen = !!document.fullscreenElement
    },

    // ======== 数据加载 ========
    loadStream () {
      predictApi.logs({ page: 1, size: 10 }).then(re => {
        const list = (re.response && re.response.list) || []
        const newest = list.length ? list[0].id : null
        const isNew = this.lastStreamId != null && newest != null && newest > this.lastStreamId
        this.lastStreamId = newest
        this.stream = list.map((r, i) => Object.assign({}, r, { fresh: isNew && i === 0 }))
      }).catch(() => { /* 大屏静默失败 */ })
    },
    fmtFans (v) {
      const n = Number(v)
      if (!isFinite(n)) return '—'
      if (n >= 10000) return (n / 10000).toFixed(1).replace(/\.0$/, '') + ' 万'
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
        grid: { left: 80, right: 40, top: 40, bottom: 40 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: params => `${params[0].name}<br/>样本量：${Number(params[0].value).toLocaleString()}` },
        xAxis: { type: 'category', data: names, axisLabel: { color: TEXT_COLOR, fontSize: 15 }, axisLine: { lineStyle: { color: SPLIT_COLOR } } },
        yAxis: { type: 'log', min: 1, axisLabel: { color: TEXT_COLOR, fontSize: 14 }, splitLine: { lineStyle: { color: SPLIT_COLOR } } },
        series: [{ type: 'bar', data: values, barWidth: '45%', itemStyle: { borderRadius: [8, 8, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#38bdf8' }, { offset: 1, color: '#6366f1' }]) } }]
      }, true)
    },
    renderGrade () {
      const chart = this.chartOf('gradeChart')
      if (!chart) return
      const dist = this.ov.gradeDistribution || {}
      const data = Array.isArray(dist)
        ? dist.map(d => ({ name: d.name || d.grade, value: Number(d.value != null ? d.value : d.count) || 0 }))
        : Object.keys(dist).map(k => ({ name: k, value: dist[k] }))
      chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}：{c} 条（{d}%）' },
        legend: { bottom: 0, textStyle: { color: TEXT_COLOR, fontSize: 14 } },
        series: [{ type: 'pie', radius: ['48%', '72%'], center: ['50%', '45%'], avoidLabelOverlap: true,
          itemStyle: { borderColor: '#0b1220', borderWidth: 3 },
          label: { color: TEXT_COLOR, fontSize: 14, formatter: '{b}\n{d}%' },
          data, color: ['#38bdf8', '#8b5cf6', '#fbbf24'] }]
      }, true)
    },
    renderCategory () {
      const chart = this.chartOf('categoryChart')
      if (!chart) return
      const cats = (this.ov.categories || []).slice(0, 10).map(c => ({ name: c.name, value: c.count }))
      cats.reverse()
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { left: 90, right: 50, top: 20, bottom: 20 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        xAxis: { type: 'value', axisLabel: { color: TEXT_COLOR, fontSize: 14 }, splitLine: { lineStyle: { color: SPLIT_COLOR } } },
        yAxis: { type: 'category', data: cats.map(c => c.name), axisLabel: { color: TEXT_COLOR, fontSize: 14 }, axisLine: { lineStyle: { color: SPLIT_COLOR } } },
        series: [{ type: 'bar', data: cats.map(c => c.value), barWidth: '55%',
          itemStyle: { borderRadius: [0, 6, 6, 0], color: '#22d3ee' },
          label: { show: true, position: 'right', color: TEXT_COLOR, fontSize: 13 } }]
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
        grid: { left: 90, right: 40, top: 40, bottom: 40 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: params => `${params[0].name}<br/>热度：${Number(params[0].value).toLocaleString()}` },
        xAxis: { type: 'category', data: labels, axisLabel: { color: TEXT_COLOR, fontSize: 15 }, axisLine: { lineStyle: { color: SPLIT_COLOR } } },
        yAxis: { type: 'log', min: 1, axisLabel: { color: TEXT_COLOR, fontSize: 14 }, splitLine: { lineStyle: { color: SPLIT_COLOR } } },
        series: [{ type: 'bar', data: values, barWidth: '40%',
          itemStyle: { borderRadius: [8, 8, 0, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#a855f7' }, { offset: 1, color: '#38bdf8' }]) } }]
      }, true)
    }
  }
}
</script>

<style lang="scss" scoped>
/* ============ 根容器：100vw × 100vh，无圆角无外边距 ============ */
html, body, #app {
  margin: 0 !important;
  padding: 0 !important;
  height: 100% !important;
}
.screen-root {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100vh;
  padding: 70px 40px 40px;
  box-sizing: border-box;
  background:
    radial-gradient(1400px 520px at 18% -10%, rgba(56, 189, 248, .18), transparent 60%),
    radial-gradient(1100px 480px at 88% -6%, rgba(139, 92, 246, .18), transparent 58%),
    linear-gradient(180deg, #0b1220 0%, #070c16 100%);
  color: #e2e8f0;
  overflow: hidden;
}

/* ============ 顶部工具栏 ============ */
.screen-toolbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 58px;
  padding: 0 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(180deg, rgba(11, 18, 32, 0.92), rgba(11, 18, 32, 0.05));
  backdrop-filter: blur(6px);
  z-index: 10;
}
.tb-title {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 1.5px;
  background: linear-gradient(90deg, #38bdf8, #a855f7);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.tb-sub { font-size: 12px; color: #7c8ba1; margin-top: 2px; }
.tb-right { display: flex; align-items: center; gap: 8px; }
.scene-indicator { display: flex; gap: 4px; }
.scene-dot {
  width: 26px; height: 26px; border-radius: 50%; border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(15, 23, 42, 0.4); color: #cbd5e1; font-size: 12px; cursor: pointer;
  transition: all 0.18s ease;
  &.active { background: #6366f1; color: #fff; border-color: #818cf8; transform: scale(1.1); }
  &:hover { border-color: #38bdf8; }
}
.current-scene-tag {
  background: rgba(99, 102, 241, 0.18);
  border-color: rgba(99, 102, 241, 0.5);
  color: #a5b4fc;
}
.tb-divider { width: 1px; height: 20px; background: rgba(148, 163, 184, 0.3); margin: 0 4px; }

/* ============ 幕容器 ============ */
.scene {
  position: absolute;
  top: 70px; left: 40px; right: 40px; bottom: 56px;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.36s ease, transform 0.36s ease;
  transform: translateY(12px);
}
.scene.active {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
  transform: translateY(0);
}

/* ============ KPI 行 ============ */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 18px;
}
.kpi {
  padding: 16px 20px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 12px;
  background: linear-gradient(160deg, rgba(56, 189, 248, 0.10), rgba(15, 23, 42, 0.5) 60%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.07);
}
.kpi-label { font-size: 12px; color: #7c8aa5; letter-spacing: 0.06em; }
.kpi-value {
  font-size: 32px; font-weight: 700; letter-spacing: -0.02em; margin-top: 4px;
  background: linear-gradient(140deg, #f8fafc, #7dd3fc 90%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.kpi-sub { font-size: 11px; color: #64748b; margin-top: 2px; }

/* ============ 图表卡 ============ */
.scene-body { height: calc(100% - 110px); }
.scene-body.two-col {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px; height: calc(100% - 10px);
}
.chart-card {
  position: relative;
  padding: 14px 18px 8px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.42);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
  height: 100%;
  box-sizing: border-box;
}
.chart-card.wide { width: 100%; height: 100%; }
.chart-title { font-size: 13.5px; font-weight: 600; color: #cbd5e1; letter-spacing: 0.02em; margin-bottom: 4px; }
.chart-body { width: 100%; height: calc(100% - 32px); }
.chart-body.tall { height: calc(100% - 32px); }

/* ============ 实时流 ============ */
.stream-full {
  height: 100%;
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 14px;
  background: linear-gradient(160deg, rgba(56, 189, 248, 0.07), rgba(15, 23, 42, 0.5) 60%);
  padding: 14px 18px 16px;
  display: flex;
  flex-direction: column;
}
.stream-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.stream-title { font-size: 16px; font-weight: 600; color: #e2e8f0; display: inline-flex; align-items: center; gap: 8px; }
.stream-sub { font-size: 12px; color: #64748b; }
.live-dot {
  width: 10px; height: 10px; border-radius: 50%; background: #34d399;
  box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.6);
  animation: live-pulse 2s infinite;
}
@keyframes live-pulse {
  0% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.55); }
  70% { box-shadow: 0 0 0 10px rgba(52, 211, 153, 0); }
  100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }
}
.stream-body { flex: 1; display: flex; flex-direction: column; gap: 4px; overflow-y: auto; }
.stream-row {
  display: grid;
  grid-template-columns: 100px 1fr 140px 110px 150px 80px;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #cbd5e1;
  padding: 10px 12px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.35);
}
.stream-row.fresh { background: rgba(52, 211, 153, 0.14); animation: fresh-fade 2.4s ease-out; }
@keyframes fresh-fade {
  0% { background: rgba(52, 211, 153, 0.3); }
  100% { background: rgba(15, 23, 42, 0.35); }
}
.c-time { color: #64748b; font-variant-numeric: tabular-nums; }
.c-cat { color: #e2e8f0; font-weight: 600; }
.c-fans, .c-hour { color: #94a3b8; font-size: 13px; }
.c-heat { color: #38bdf8; font-weight: 700; font-variant-numeric: tabular-nums; font-size: 15px; }
.c-grade { text-align: center; border-radius: 4px; padding: 4px 0; font-size: 13px; }
.g-high { color: #fca5a5; background: rgba(248, 113, 113, 0.16); }
.g-mid { color: #fcd34d; background: rgba(252, 211, 77, 0.14); }
.g-low { color: #94a3b8; background: rgba(148, 163, 184, 0.14); }
.stream-empty { font-size: 14px; color: #64748b; padding: 14px 8px; text-align: center; }

/* ============ 底部时钟 ============ */
.screen-footer {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 36px;
  padding: 0 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(0deg, rgba(11, 18, 32, 0.92), rgba(11, 18, 32, 0.05));
  backdrop-filter: blur(6px);
  z-index: 10;
  font-size: 12px;
}
.clock { color: #38bdf8; font-family: Consolas, Menlo, monospace; font-variant-numeric: tabular-nums; letter-spacing: 0.04em; }
.kbd-hint { color: #64748b; }

/* ============ 响应式 ============ */
@media (max-width: 1400px) {
  .screen-root { padding: 66px 28px 36px; }
  .scene { left: 28px; right: 28px; top: 66px; bottom: 52px; }
}
@media (max-width: 1100px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .scene-body.two-col { grid-template-columns: 1fr; }
}
</style>
