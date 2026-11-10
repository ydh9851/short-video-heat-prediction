<template>
  <div class="eda-interactive" v-loading="loading">
    <div class="ei-toolbar">
      <div class="ei-filters">
        <span class="ei-chip">平台 {{ platformLabel }}</span>
        <span v-if="selectedCategory" class="ei-chip is-active">
          类别 {{ selectedCategory }}
          <i @click="selectedCategory = ''">×</i>
        </span>
        <span v-if="selectedGrade" class="ei-chip is-active">
          等级 {{ selectedGrade }}
          <i @click="selectedGrade = ''">×</i>
        </span>
        <span v-if="!selectedCategory && !selectedGrade" class="ei-hint">点击下方图表进行筛选，三张图会联动</span>
      </div>
      <el-button size="small" :disabled="!selectedCategory && !selectedGrade" @click="reset">重置筛选</el-button>
    </div>

    <app-empty
      v-if="error"
      compact
      :title="error"
      description="请先在数据管理页完成数据集导入，再回到这里查看交互洞察" />

    <template v-else>
      <el-row :gutter="14">
        <el-col :xs="24" :lg="14">
          <div class="ei-panel">
            <div class="ei-title">类别样本量 <em>点击柱子筛选</em></div>
            <div ref="catChart" class="ei-chart" />
          </div>
        </el-col>
        <el-col :xs="24" :lg="10">
          <div class="ei-panel">
            <div class="ei-title">热度等级分布 <em>点击扇区筛选</em></div>
            <div ref="gradeChart" class="ei-chart" />
          </div>
        </el-col>
      </el-row>

      <div class="ei-panel">
        <div class="ei-title">
          粉丝数 × 热度
          <em>基于最近 {{ samples.length }} 条抽样样本，双对数轴</em>
        </div>
        <div ref="scatterChart" class="ei-chart is-tall" />
      </div>

      <insight-card
        class="ei-insight"
        :title="insight.title"
        :desc="insight.desc"
        :tone="insight.tone"
        :tag="insight.tag" />
    </template>
  </div>
</template>

<script>
import * as echarts from 'echarts/core'
import { BarChart, PieChart, ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import dataApi from '@/api/data'
import { createChart, setChartOption } from '@/utils/chart'
import AppEmpty from '@/components/AppEmpty'
import InsightCard from '@/components/InsightCard'

echarts.use([BarChart, PieChart, ScatterChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const GRADE_COLORS = { 低热度: '#94a3b8', 中热度: '#f59e0b', 高热度: '#ef4444' }
const GRADE_ORDER = ['低热度', '中热度', '高热度']

/**
 * EDA 交互洞察：类别 / 等级 / 粉丝-热度三图联动。
 *
 * 数据来自已有的 overview 与 samples 接口，不新增后端能力；
 * 点击类别柱或等级扇区即设置筛选条件，散点与结论卡同步刷新。
 */
export default {
  name: 'EdaInteractive',
  components: { AppEmpty, InsightCard },
  data () {
    return {
      loading: false,
      error: '',
      platform: '',
      platformLabel: '',
      overview: {},
      samples: [],
      selectedCategory: '',
      selectedGrade: '',
      charts: {}
    }
  },
  computed: {
    categories () {
      return (this.overview && this.overview.categories) || []
    },
    grades () {
      const list = (this.overview && this.overview.gradeDistribution) || []
      return GRADE_ORDER
        .map(g => list.find(x => x.grade === g) || { grade: g, count: 0 })
        .filter(g => g.count > 0)
    },
    filteredSamples () {
      return this.samples.filter(s => {
        if (this.selectedCategory && s.videoCategory !== this.selectedCategory) return false
        if (this.selectedGrade && s.grade !== this.selectedGrade) return false
        return Number.isFinite(Number(s.heat)) && Number(s.heat) > 0
      })
    },
    insight () {
      const list = this.filteredSamples
      if (!list.length) {
        return {
          title: '当前筛选下没有样本',
          desc: '抽样样本中不存在满足该组合的视频，请放宽筛选条件或重置后再看。',
          tone: 'warning',
          tag: '空结果'
        }
      }
      const avg = list.reduce((s, x) => s + Number(x.heat), 0) / list.length
      const byCat = {}
      list.forEach(x => { byCat[x.videoCategory] = (byCat[x.videoCategory] || 0) + 1 })
      const top = Object.entries(byCat).sort((a, b) => b[1] - a[1])[0]
      return {
        title: '筛选后的样本洞察',
        desc: `当前条件下共 ${list.length} 条抽样样本，平均热度 ${Math.round(avg).toLocaleString('en-US')}；`
          + `样本量最高的类别为「${top[0]}」（${top[1]} 条）。`
          + (this.selectedGrade ? `等级筛选为「${this.selectedGrade}」，均值只代表该档内的水平。` : ''),
        tone: 'primary',
        tag: this.selectedCategory || this.selectedGrade || '全部样本'
      }
    }
  },
  watch: {
    selectedCategory () { this.refreshCharts() },
    selectedGrade () { this.refreshCharts() }
  },
  mounted () {
    this.load()
    window.addEventListener('resize', this.onResize)
  },
  beforeUnmount () {
    window.removeEventListener('resize', this.onResize)
    Object.values(this.charts).forEach(c => c && c.dispose())
    this.charts = {}
  },
  methods: {
    async load () {
      this.loading = true
      this.error = ''
      try {
        const pRe = await dataApi.platforms()
        const pBody = pRe.response || {}
        const list = pBody.platforms || []
        const def = list.find(x => x.platform === pBody.defaultPlatform && x.available) ||
          list.find(x => x.available)
        if (!def) {
          this.error = '暂无已导入的数据集'
          return
        }
        this.platform = def.platform
        this.platformLabel = def.displayName || def.platform

        const [ovRe, smRe] = await Promise.all([
          dataApi.overview(this.platform),
          dataApi.samples({ platform: this.platform, page: 1, size: 200 })
        ])
        this.overview = ovRe.response || {}
        this.samples = (smRe.response && smRe.response.list) || []
        this.$nextTick(this.renderCharts)
      } catch (e) {
        this.error = '数据加载失败，请检查数据集状态'
      } finally {
        this.loading = false
      }
    },
    ensureCharts () {
      if (!this.charts.cat && this.$refs.catChart) {
        this.charts.cat = createChart(echarts, this.$refs.catChart)
      }
      if (!this.charts.grade && this.$refs.gradeChart) {
        this.charts.grade = createChart(echarts, this.$refs.gradeChart)
      }
      if (!this.charts.scatter && this.$refs.scatterChart) {
        this.charts.scatter = createChart(echarts, this.$refs.scatterChart)
      }
    },
    renderCharts () {
      this.ensureCharts()
      this.renderCategory()
      this.renderGrade()
      this.renderScatter()
    },
    refreshCharts () {
      if (!this.charts.cat) this.renderCharts()
      else {
        this.renderCategory()
        this.renderGrade()
        this.renderScatter()
      }
      this.onResize()
    },
    renderCategory () {
      const chart = this.charts.cat
      if (!chart) return
      const items = this.categories.slice(0, 14).slice().reverse()
      const selected = this.selectedCategory
      setChartOption(chart, {
        grid: { left: 8, right: 26, top: 12, bottom: 8, containLabel: true },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: p => `${p[0].name}：${Number(p[0].value).toLocaleString('en-US')} 条`
        },
        xAxis: { type: 'value' },
        yAxis: {
          type: 'category',
          data: items.map(c => c.name),
          axisLabel: { color: '#64748b', fontSize: 11 }
        },
        series: [{
          type: 'bar',
          barWidth: 12,
          data: items.map(c => ({
            value: c.count,
            itemStyle: {
              borderRadius: [0, 6, 6, 0],
              color: !selected || selected === c.name
                ? {
                    type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
                    colorStops: [{ offset: 0, color: '#8b5cf6' }, { offset: 1, color: '#6366f1' }]
                  }
                : '#dbe1ee'
            }
          })),
          label: { show: true, position: 'right', color: '#94a3b8', fontSize: 10 }
        }]
      }, true)
      chart.off('click')
      chart.on('click', p => {
        this.selectedCategory = this.selectedCategory === p.name ? '' : p.name
      })
    },
    renderGrade () {
      const chart = this.charts.grade
      if (!chart) return
      const list = this.grades
      setChartOption(chart, {
        tooltip: {
          trigger: 'item',
          formatter: p => `${p.name}：${Number(p.value).toLocaleString('en-US')} 条（${p.percent}%）`
        },
        legend: { bottom: 0, itemWidth: 9, itemHeight: 9 },
        series: [{
          type: 'pie',
          radius: ['46%', '70%'],
          center: ['50%', '46%'],
          avoidLabelOverlap: true,
          label: { formatter: '{b}\n{d}%', color: '#64748b', fontSize: 11 },
          data: list.map(g => ({
            name: g.grade,
            value: g.count,
            itemStyle: {
              color: GRADE_COLORS[g.grade] || '#6366f1',
              opacity: !this.selectedGrade || this.selectedGrade === g.grade ? 1 : 0.28
            }
          }))
        }]
      }, true)
      chart.off('click')
      chart.on('click', p => {
        this.selectedGrade = this.selectedGrade === p.name ? '' : p.name
      })
    },
    renderScatter () {
      const chart = this.charts.scatter
      if (!chart) return
      const data = this.filteredSamples.map(s => [
        Math.max(1, Number(s.authorFans) || 0),
        Math.max(1, Number(s.heat)),
        s.videoCategory,
        s.grade
      ])
      setChartOption(chart, {
        grid: { left: 10, right: 24, top: 30, bottom: 10, containLabel: true },
        tooltip: {
          trigger: 'item',
          formatter: p => `${p.data[2]} · ${p.data[3]}<br/>粉丝 ${Number(p.data[0]).toLocaleString('en-US')}`
            + `<br/>热度 ${Number(p.data[1]).toLocaleString('en-US')}`
        },
        xAxis: {
          type: 'log',
          name: '粉丝数',
          nameTextStyle: { color: '#94a3b8', fontSize: 11 },
          min: 1
        },
        yAxis: {
          type: 'log',
          name: '热度',
          nameTextStyle: { color: '#94a3b8', fontSize: 11 },
          min: 1
        },
        series: [{
          type: 'scatter',
          symbolSize: 9,
          data,
          itemStyle: { opacity: 0.62, color: '#6366f1' },
          emphasis: { itemStyle: { opacity: 1, color: '#a855f7' } }
        }]
      }, true)
    },
    reset () {
      this.selectedCategory = ''
      this.selectedGrade = ''
    },
    onResize () {
      Object.values(this.charts).forEach(c => c && c.resize())
    }
  }
}
</script>

<style lang="scss" scoped>
.eda-interactive {
  min-height: 300px;
}

.ei-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.ei-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.ei-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 11.5px;

  &.is-active {
    background: #eef2ff;
    color: #4f46e5;
  }

  i {
    font-style: normal;
    cursor: pointer;
    font-size: 13px;
    line-height: 1;
  }
}

.ei-hint {
  font-size: 11.5px;
  color: #b6bec9;
}

.ei-panel {
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid #eef0f6;
  border-radius: 12px;
  background: #fff;
}

.ei-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 8px;

  em {
    margin-left: 8px;
    font-style: normal;
    font-size: 11px;
    font-weight: 400;
    color: #b6bec9;
  }
}

.ei-chart {
  width: 100%;
  height: 300px;

  &.is-tall {
    height: 340px;
  }
}

.ei-insight {
  margin-bottom: 14px;
}

@media (max-width: 768px) {
  .ei-chart {
    height: 260px;
  }
}
</style>
