<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">数据管理</div>
        <div class="page-desc">
          当前平台：<b>{{ currentPlatformMeta.displayName || platform }}</b>。规范化数据集（缺失值处理、类别编码与特征工程后）
          的分布统计与样本预览，由 <code>algorithm/datasets/ingest.py</code> 统一归一化产出。
        </div>
      </div>
      <div class="page-head-actions">
        <el-select v-model="platform" style="width:180px" @change="onPlatformChange">
          <el-option
            v-for="p in platforms"
            :key="p.platform"
            :label="p.displayName + (p.available ? '' : '（未导入）')"
            :value="p.platform" />
        </el-select>
        <el-button
          v-if="platforms.length && !currentPlatformMeta.available"
          type="primary"
          :loading="importing"
          @click="doImport">导入数据集</el-button>
        <el-button :loading="loadingOverview" @click="refreshAll">重新加载</el-button>
      </div>
    </div>

    <el-alert
      v-if="platforms.length && !currentPlatformMeta.available"
      type="warning"
      :closable="false"
      show-icon
      class="import-tip"
      title="该平台数据集尚未导入：请把原始数据文件放入 data/raw 目录（文件名需含平台关键字，如 youtube/tiktok/bilibili），然后点击「导入数据集」；算法引擎会自动识别列名并归一化为统一字段。" />

    <!-- ============ 关键指标 ============ -->
    <div class="kpi-grid" v-loading="loadingOverview">
      <div v-for="k in kpis" :key="k.label" class="kpi-card">
        <div class="kpi-icon" :class="'tone-' + k.tone">
          <svg-icon :icon-class="k.icon" />
        </div>
        <div class="kpi-body">
          <div class="kpi-label">{{ k.label }}</div>
          <div class="kpi-value" :class="{ small: k.small }">{{ k.value }}</div>
          <div class="kpi-sub">{{ k.sub }}</div>
        </div>
      </div>
    </div>

    <!-- ============ 分布图表 ============ -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="chart-card">
          <div class="card-head">
            <div class="section-title">视频类别分布</div>
            <el-tag size="small" type="info">{{ ov.categoryCount || 0 }} 个类别</el-tag>
          </div>
          <div ref="categoryChart" v-loading="loadingOverview" class="chart-box" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="chart-card">
          <div class="card-head">
            <div class="section-title">热度等级分布</div>
            <el-tag size="small" type="warning">K-Means 分级口径</el-tag>
          </div>
          <div ref="gradeChart" v-loading="loadingOverview" class="chart-box" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="chart-card">
          <div class="card-head">
            <div class="section-title">热度分位数与分级阈值</div>
            <el-tag size="small" type="info">长尾分布</el-tag>
          </div>
          <div ref="heatChart" v-loading="loadingOverview" class="chart-box" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="chart-card">
          <div class="card-head">
            <div class="section-title">作者粉丝数分位数</div>
            <el-tag size="small" type="success">核心先验特征</el-tag>
          </div>
          <div ref="fansChart" v-loading="loadingOverview" class="chart-box" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ============ 样本预览 ============ -->
    <el-card shadow="never" class="list-card">
      <div class="list-toolbar">
        <div class="list-toolbar-filters">
          <el-input
            v-model="keyword"
            size="small"
            clearable
            placeholder="按视频 ID 检索"
            style="width:200px"
            @keyup.enter="onFilter"
            @clear="onFilter">
            <template #prefix><svg-icon icon-class="search" /></template>
          </el-input>
          <el-select v-model="category" size="small" style="width:160px" @change="onFilter">
            <el-option label="全部类别" value="" />
            <el-option v-for="c in (ov.categories || [])" :key="c.name" :label="c.name" :value="c.name" />
          </el-select>
          <el-button size="small" type="primary" @click="onFilter">
            <svg-icon icon-class="search" />&nbsp;查询
          </el-button>
          <el-button size="small" @click="resetFilter">重置</el-button>
        </div>
        <div class="muted">共 {{ fmtInt(sampleTotal) }} 条匹配样本</div>
      </div>

      <el-table :data="samples" size="small" stripe v-loading="loadingSamples">
        <el-table-column prop="videoId" label="视频 ID" min-width="180" show-overflow-tooltip />
        <el-table-column prop="videoCategory" label="类别" width="90" />
        <el-table-column label="作者粉丝数" width="120">
          <template #default="{ row }">{{ fmtInt(row.authorFans) }}</template>
        </el-table-column>
        <el-table-column prop="publishTime" label="发布时间" width="165" />
        <el-table-column label="播放量" width="110">
          <template #default="{ row }">{{ fmtInt(row.playCnt) }}</template>
        </el-table-column>
        <el-table-column label="点赞" width="90">
          <template #default="{ row }">{{ fmtInt(row.likeCnt) }}</template>
        </el-table-column>
        <el-table-column label="评论" width="80">
          <template #default="{ row }">{{ fmtInt(row.commentCnt) }}</template>
        </el-table-column>
        <el-table-column label="转发" width="80">
          <template #default="{ row }">{{ fmtInt(row.shareCnt) }}</template>
        </el-table-column>
        <el-table-column label="热度（加权互动量）" min-width="130">
          <template #default="{ row }"><b class="heat-val">{{ fmtInt(row.heat) }}</b></template>
        </el-table-column>
        <el-table-column label="等级" width="100">
          <template #default="{ row }">
            <el-tag :type="gradeTag(row.grade)" size="small" effect="light">{{ row.grade }}</el-tag>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="没有符合条件的样本，试试调整筛选条件" :image-size="80" />
        </template>
      </el-table>

      <div class="list-footer">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="sampleTotal"
          :page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :current-page="page"
          @size-change="onSizeChange"
          @current-change="onPageChange" />
      </div>
    </el-card>
  </div>
</template>

<script>
import * as echarts from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, GraphicComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import dataApi from '@/api/data'

echarts.use([BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, GraphicComponent, CanvasRenderer])

const PALETTE = ['#6366f1', '#8b5cf6', '#a855f7', '#38bdf8', '#22d3ee', '#34d399', '#fbbf24', '#fb7185']

export default {
  name: 'DataManage',
  data () {
    return {
      loadingOverview: false,
      loadingSamples: false,
      importing: false,
      platforms: [],
      platform: 'douyin',
      ov: {},
      samples: [],
      sampleTotal: 0,
      page: 1,
      pageSize: 20,
      category: '',
      keyword: '',
      charts: {}
    }
  },
  computed: {
    currentPlatformMeta () {
      return this.platforms.find(p => p.platform === this.platform) || {}
    },
    kpis () {
      const h = this.ov.heat || {}
      const range = this.ov.publishRange || {}
      const span = range.start && range.end
        ? range.start.slice(0, 10) + ' ~ ' + range.end.slice(0, 10)
        : '—'
      return [
        { label: '样本总量', value: this.fmtInt(this.ov.total), icon: 'table', tone: 'indigo', sub: '规范化训练数据集' },
        { label: '视频类别数', value: this.ov.categoryCount || 0, icon: 'chart', tone: 'violet', sub: '内容类目标签种类' },
        { label: '热度中位数', value: this.fmtInt(h.median), icon: 'star', tone: 'blue', sub: '加权互动量 · 全体样本' },
        { label: '数据时间跨度', value: span, icon: 'log', tone: 'green', small: true, sub: '视频发布日期范围' }
      ]
    }
  },
  created () {
    this.loadPlatforms()
  },
  mounted () {
    window.addEventListener('resize', this.resizeHandler)
    this.sidebarEl = document.querySelector('.sidebar-container')
    if (this.sidebarEl) this.sidebarEl.addEventListener('transitionend', this.sidebarResizeHandler)
    this.$nextTick(this.renderCharts)
  },
  activated () {
    this.$nextTick(this.renderCharts)
  },
  beforeUnmount () {
    window.removeEventListener('resize', this.resizeHandler)
    if (this.sidebarEl) this.sidebarEl.removeEventListener('transitionend', this.sidebarResizeHandler)
    Object.values(this.charts).forEach(c => c && c.dispose())
    this.charts = {}
  },
  methods: {
    resizeHandler () {
      Object.values(this.charts).forEach(c => c && c.resize())
    },
    sidebarResizeHandler (e) {
      if (e.propertyName === 'width') this.resizeHandler()
    },
    refreshAll () {
      // loadPlatforms 内部会串行刷新总览与样本，避免重复请求
      this.loadPlatforms()
    },
    loadPlatforms () {
      dataApi.platforms().then(re => {
        const d = re.response || {}
        this.platforms = d.platforms || []
        this.platform = d.defaultPlatform || (this.platforms[0] && this.platforms[0].platform) || 'douyin'
        this.loadOverview()
        this.loadSamples()
      }).catch(() => {
        this.platforms = []
        this.loadOverview()
        this.loadSamples()
      })
    },
    onPlatformChange () {
      this.page = 1
      this.category = ''
      this.keyword = ''
      this.loadOverview()
      this.loadSamples()
    },
    doImport () {
      this.importing = true
      dataApi.importDataset(this.platform).then(re => {
        const d = re.response || {}
        if (d.code === 1) {
          this.$message.success(d.message || '导入成功')
        } else {
          this.$message.error(d.message || '导入失败')
        }
        this.importing = false
        this.refreshAll()
      }).catch(() => { this.importing = false })
    },
    loadOverview () {
      this.loadingOverview = true
      dataApi.overview(this.platform).then(re => {
        this.ov = re.response || {}
        this.loadingOverview = false
        this.$nextTick(this.renderCharts)
      }).catch(() => { this.loadingOverview = false })
    },
    loadSamples () {
      this.loadingSamples = true
      dataApi.samples({ platform: this.platform, page: this.page, size: this.pageSize, category: this.category, keyword: this.keyword })
        .then(re => {
          const r = re.response || {}
          this.samples = r.list || []
          this.sampleTotal = r.total || 0
          this.loadingSamples = false
        }).catch(() => { this.loadingSamples = false })
    },
    onFilter () {
      this.page = 1
      this.loadSamples()
    },
    resetFilter () {
      this.keyword = ''
      this.category = ''
      this.page = 1
      this.loadSamples()
    },
    onPageChange (p) {
      this.page = p
      this.loadSamples()
    },
    onSizeChange (s) {
      this.pageSize = s
      this.page = 1
      this.loadSamples()
    },
    /* ---------------- 图表渲染 ---------------- */
    renderCharts () {
      this.renderCategory()
      this.renderGrade()
      this.renderHeat()
      this.renderFans()
    },
    renderCategory () {
      const el = this.$refs.categoryChart
      if (!el) return
      if (!this.charts.category) this.charts.category = echarts.init(el)
      const list = (this.ov.categories || []).slice(0, 12).slice().reverse()
      this.charts.category.setOption({
        grid: { left: 10, right: 40, top: 12, bottom: 6, containLabel: true },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => `${p[0].name}<br/>样本数：${this.fmtInt(p[0].value)}` },
        xAxis: { type: 'value', splitLine: { lineStyle: { color: '#f1f3f8' } }, axisLabel: { color: '#94a3b8', formatter: v => this.fmtShort(v) } },
        yAxis: {
          type: 'category',
          data: list.map(i => i.name),
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: '#475569', fontSize: 12 }
        },
        series: [{
          type: 'bar',
          data: list.map(i => i.count),
          barWidth: 13,
          itemStyle: {
            borderRadius: [0, 7, 7, 0],
            color: {
              type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
              colorStops: [{ offset: 0, color: '#6366f1' }, { offset: 1, color: '#a855f7' }]
            }
          },
          label: { show: true, position: 'right', color: '#94a3b8', fontSize: 11, formatter: p => this.fmtShort(p.value) }
        }]
      }, true)
    },
    renderGrade () {
      const el = this.$refs.gradeChart
      if (!el) return
      if (!this.charts.grade) this.charts.grade = echarts.init(el)
      const colorMap = { 低热度: '#94a3b8', 中热度: '#f59e0b', 高热度: '#ef4444' }
      const data = (this.ov.gradeDistribution || []).map((g, i) => ({
        name: g.grade,
        value: g.count,
        itemStyle: { color: colorMap[g.grade] || PALETTE[i % PALETTE.length] }
      }))
      const totalCnt = data.reduce((s, d) => s + (d.value || 0), 0)
      this.charts.grade.setOption({
        tooltip: { trigger: 'item', formatter: p => `${p.name}<br/>${this.fmtInt(p.value)} 条（${p.percent}%）` },
        legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { color: '#64748b', fontSize: 12 } },
        series: [{
          type: 'pie',
          radius: ['52%', '72%'],
          center: ['50%', '44%'],
          avoidLabelOverlap: true,
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', formatter: '{b}\n{d}%' } },
          data
        }],
        graphic: totalCnt ? [{
          type: 'text',
          left: 'center',
          top: '36%',
          style: { text: this.fmtInt(totalCnt) + '\n样本', textAlign: 'center', fill: '#1e293b', fontSize: 15, fontWeight: 700, lineHeight: 20 }
        }] : []
      }, true)
    },
    renderHeat () {
      const el = this.$refs.heatChart
      if (!el || !this.ov.heat) return
      if (!this.charts.heat) this.charts.heat = echarts.init(el)
      const h = this.ov.heat
      const names = ['最小值', 'P25', '中位数', 'P75', '最大值']
      const vals = [h.min, h.q1, h.median, h.q3, h.max]
      this.charts.heat.setOption({
        grid: { left: 10, right: 20, top: 24, bottom: 6, containLabel: true },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => `${p[0].name}<br/>热度：${this.fmtInt(p[0].value)}` },
        xAxis: {
          type: 'category', data: names,
          axisLine: { lineStyle: { color: '#e6e9f0' } },
          axisTick: { show: false },
          axisLabel: { color: '#475569', fontSize: 12 }
        },
        yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f1f3f8' } }, axisLabel: { color: '#94a3b8', formatter: v => this.fmtShort(v) } },
        series: [{
          type: 'bar',
          data: vals.map((v, i) => ({
            value: v,
            itemStyle: {
              borderRadius: [8, 8, 0, 0],
              color: {
                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{ offset: 0, color: PALETTE[i % PALETTE.length] }, { offset: 1, color: '#c7cbf7' }]
              }
            }
          })),
          barWidth: '42%',
          label: { show: true, position: 'top', color: '#64748b', fontSize: 11, formatter: p => this.fmtShort(p.value) },
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: '#f59e0b', type: 'dashed', width: 1.4 },
            label: { color: '#b45309', fontSize: 11, formatter: '低/中阈值 684' },
            data: [{ yAxis: 684 }]
          }
        }]
      }, true)
    },
    renderFans () {
      const el = this.$refs.fansChart
      if (!el || !this.ov.fans) return
      if (!this.charts.fans) this.charts.fans = echarts.init(el)
      const f = this.ov.fans
      const names = ['最小值', '中位数', '均值', '最大值']
      const vals = [f.min, f.median, f.mean, f.max]
      this.charts.fans.setOption({
        grid: { left: 10, right: 24, top: 24, bottom: 6, containLabel: true },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => `${p[0].name}<br/>粉丝数：${this.fmtInt(p[0].value)}` },
        xAxis: {
          type: 'category', data: names,
          axisLine: { lineStyle: { color: '#e6e9f0' } },
          axisTick: { show: false },
          axisLabel: { color: '#475569', fontSize: 12 }
        },
        yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f1f3f8' } }, axisLabel: { color: '#94a3b8', formatter: v => this.fmtShort(v) } },
        series: [{
          type: 'bar',
          data: vals.map(v => ({
            value: v,
            itemStyle: {
              borderRadius: [8, 8, 0, 0],
              color: {
                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [{ offset: 0, color: '#34d399' }, { offset: 1, color: '#a7f3d0' }]
              }
            }
          })),
          barWidth: '34%',
          label: { show: true, position: 'top', color: '#64748b', fontSize: 11, formatter: p => this.fmtShort(p.value) }
        }]
      }, true)
    },
    /* ---------------- 格式化 ---------------- */
    fmtInt (v) {
      if (v == null || Number.isNaN(Number(v))) return '-'
      return Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })
    },
    fmtShort (v) {
      const n = Number(v)
      if (!Number.isFinite(n)) return '-'
      if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(1) + '亿'
      if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(1) + '万'
      return n.toLocaleString('en-US', { maximumFractionDigits: 0 })
    },
    gradeTag (g) {
      return { 低热度: 'info', 中热度: 'warning', 高热度: 'danger' }[g] || 'info'
    }
  }
}
</script>

<style lang="scss" scoped>
.app-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ---------------- KPI ---------------- */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 16px;
}
.kpi-card {
  background: #fff;
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  box-shadow: var(--app-shadow-1);
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 15px;
  transition: box-shadow .22s ease, transform .22s ease;

  &:hover {
    box-shadow: var(--app-shadow-2);
    transform: translateY(-2px);
  }
}
.kpi-icon {
  width: 46px;
  height: 46px;
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #fff;
  flex-shrink: 0;

  &.tone-indigo { background: linear-gradient(135deg, #6366f1, #8b5cf6); box-shadow: 0 8px 18px rgba(99, 102, 241, .32); }
  &.tone-violet { background: linear-gradient(135deg, #8b5cf6, #d946ef); box-shadow: 0 8px 18px rgba(139, 92, 246, .32); }
  &.tone-blue { background: linear-gradient(135deg, #38bdf8, #6366f1); box-shadow: 0 8px 18px rgba(56, 189, 248, .32); }
  &.tone-green { background: linear-gradient(135deg, #34d399, #10b981); box-shadow: 0 8px 18px rgba(16, 185, 129, .32); }
}
.kpi-body {
  min-width: 0;
  flex: 1;
}
.kpi-label {
  font-size: 13px;
  color: #94a3b8;
}
.kpi-value {
  font-size: 25px;
  font-weight: 750;
  color: var(--app-text);
  line-height: 1.35;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;

  &.small {
    font-size: 16px;
    font-weight: 650;
  }
}
.kpi-sub {
  font-size: 11.5px;
  color: #b6bec9;
  margin-top: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---------------- 图表 ---------------- */
.chart-row {
  margin: 0 !important;
}
.chart-card {
  margin-bottom: 0;

  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;

    .section-title {
      margin-bottom: 0;
    }
  }
}
.chart-box {
  width: 100%;
  height: 300px;
}
.el-col {
  margin-bottom: 16px;
}

.heat-val {
  color: var(--app-primary);
}

.import-tip {
  margin-bottom: 16px;
}

/* ---------------- 移动端 ---------------- */
@media (max-width: 640px) {
  .page-head {
    align-items: flex-start;
  }
  .kpi-grid {
    grid-template-columns: 1fr;
  }
  .chart-box {
    height: 260px;
  }
}
</style>
