<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">热度分级</div>
        <div class="page-desc">
          先对热度（log1p 空间）做 K-Means 聚类，得到「低 / 中 / 高」等级与分级阈值；
          再用与预测相同的先验特征训练分类模型，让视频在发布之初即可判断所属热度等级。
        </div>
      </div>
      <div class="page-head-actions">
        <el-tag v-if="data" type="info" size="large">轮廓系数 {{ fmt(data.silhouette) }}</el-tag>
      </div>
    </div>

    <!-- ============ 聚类参数 ============ -->
    <el-card shadow="never" class="ctrl-card">
      <div class="ctrl-row">
        <div class="ctrl-item">
          <span class="ctrl-label">聚类簇数 k</span>
          <el-radio-group v-model="k" @change="load">
            <el-radio-button :label="3">3 级</el-radio-button>
            <el-radio-button :label="4">4 级</el-radio-button>
            <el-radio-button :label="5">5 级</el-radio-button>
          </el-radio-group>
        </div>
        <div class="ctrl-item">
          <span class="ctrl-label">聚类特征</span>
          <el-tag size="small" type="success" effect="plain">热度 log1p 一维</el-tag>
        </div>
        <div class="ctrl-item">
          <span class="ctrl-label">分类特征</span>
          <el-tag size="small" effect="plain">类别 / 粉丝数 / 发布时段（先验信息）</el-tag>
        </div>
      </div>
      <div class="ctrl-tip">
        轮廓系数衡量聚类紧致程度（越接近 1 越好）。k 越大等级划分越细，但样本量少的等级会更难被分类模型稳定识别。
      </div>
    </el-card>

    <div v-loading="loading" class="loading-host">
      <!-- ============ 分级结果卡片 ============ -->
      <div v-if="data" class="grade-cards">
        <div
          v-for="(n, i) in data.grade_names"
          :key="i"
          class="grade-card"
          :style="{ '--accent': gradeColor(i), '--soft': gradeSoft(i) }">
          <div class="grade-bar" />
          <div class="grade-name">{{ n }}</div>
          <div class="grade-range">热度区间 {{ rangeText(i) }}</div>
          <div class="grade-count">{{ fmtInt(distOf(n).count) }}<span class="unit">条</span></div>
          <div class="grade-share">占比 {{ shareOf(n) }}%</div>
          <div class="grade-mean">区间均值 {{ fmtInt(distOf(n).mean) }}</div>
        </div>
      </div>

      <!-- ============ 占比环形图 + 阈值区间对照 ============ -->
      <el-row :gutter="16" class="chart-row">
        <el-col :xs="24" :lg="10">
          <el-card shadow="never" class="chart-card">
            <div class="card-head">
              <div class="section-title">等级样本占比</div>
              <el-tag size="small" type="info">K = {{ data ? data.k : k }}</el-tag>
            </div>
            <div ref="shareChart" class="chart-box" />
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="14">
          <el-card shadow="never" class="chart-card">
            <div class="card-head">
              <div class="section-title">等级热度区间对照</div>
              <el-tag size="small" type="warning">区间越宽 = 长尾越长</el-tag>
            </div>
            <div ref="rangeChart" class="chart-box" />
          </el-card>
        </el-col>
      </el-row>

      <!-- ============ 分类模型对照 ============ -->
      <el-card shadow="never" class="block-card">
        <div class="card-head">
          <div class="section-title">分级分类模型对照</div>
          <span class="muted">仅使用发布时可见的先验特征，评估分类器还原热度等级的能力</span>
        </div>
        <el-table :data="data ? data.classifier_metrics : []" size="small" stripe>
          <el-table-column type="index" label="#" width="55" />
          <el-table-column label="模型" min-width="200">
            <template #default="{ row }">
              <span class="model-name">{{ modelShort(row.model) }}</span>
              <el-tag v-if="isBest(row)" size="small" type="success" effect="dark" class="best-tag">最优</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="准确率 Accuracy" min-width="200">
            <template #default="{ row }">
              <el-progress
                :percentage="Math.round(row.accuracy * 100)"
                :stroke-width="14"
                :color="isBest(row) ? '#10b981' : '#c7cbf7'"
                :format="() => (row.accuracy * 100).toFixed(2) + '%'" />
            </template>
          </el-table-column>
          <el-table-column label="宏平均 F1" width="130">
            <template #default="{ row }">
              <b :class="{ 'f1-best': isBest(row) }">{{ row.macro_f1.toFixed(4) }}</b>
            </template>
          </el-table-column>
          <el-table-column label="说明" min-width="260">
            <template #default="{ row }">
              <span class="model-desc">{{ modelDesc(row.model) }}</span>
            </template>
          </el-table-column>
        </el-table>
        <div class="table-tip">
          宏平均 F1 对每个等级一视同仁地取平均，能在高/低热度样本不均衡时反映少数类的识别能力，因此作为模型排序依据。
        </div>
      </el-card>

      <!-- ============ 混淆矩阵 ============ -->
      <el-card shadow="never" class="block-card">
        <div class="card-head">
          <div class="section-title">最优分类器混淆矩阵（LightGBM）</div>
          <el-tag size="small" type="success">行 = 真实等级 · 列 = 预测等级</el-tag>
        </div>
        <el-image
          :src="fig('grade_confusion.png')"
          :preview-src-list="[fig('grade_confusion.png')]"
          fit="contain"
          class="fig-img-lg"
          lazy>
          <template #error>
            <div class="fig-fallback">混淆矩阵图未生成，请先在「模型评估」页运行一次分级实验</div>
          </template>
        </el-image>
        <div class="table-tip">
          对角线上的数值表示被正确识别的样本数；相邻等级之间的错分主要来自热度区间连续、边界样本特征高度相似。
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, GraphicComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import gradeApi from '@/api/grade'

echarts.use([BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, GraphicComponent, CanvasRenderer])

/** 与 theme 主色系一致的等级配色 */
const GRADE_COLORS = ['#94a3b8', '#38bdf8', '#f59e0b', '#fb7185', '#a855f7']
const GRADE_SOFT = ['#f1f5f9', '#e0f2fe', '#fef3c7', '#ffe4e6', '#f3e8ff']

export default {
  name: 'GradingIndex',
  data () {
    return {
      k: 3,
      loading: false,
      data: null,
      charts: {}
    }
  },
  created () {
    this.load()
  },
  mounted () {
    window.addEventListener('resize', this.resizeHandler)
    this.sidebarEl = document.querySelector('.sidebar-container')
    if (this.sidebarEl) this.sidebarEl.addEventListener('transitionend', this.sidebarResizeHandler)
  },
  beforeUnmount () {
    window.removeEventListener('resize', this.resizeHandler)
    if (this.sidebarEl) this.sidebarEl.removeEventListener('transitionend', this.sidebarResizeHandler)
    Object.values(this.charts).forEach(c => c && c.dispose())
    this.charts = {}
  },
  methods: {
    fig (name) {
      return '/grading/' + name + '?t=' + Date.now()
    },
    resizeHandler () {
      Object.values(this.charts).forEach(c => c && c.resize())
    },
    sidebarResizeHandler (e) {
      if (e.propertyName === 'width') this.resizeHandler()
    },
    load () {
      this.loading = true
      gradeApi.grade(this.k).then(re => {
        this.data = re.response || null
        this.loading = false
        this.$nextTick(() => {
          this.renderShare()
          this.renderRange()
        })
      }).catch(() => { this.loading = false })
    },
    /* ---------------- 数据辅助 ---------------- */
    distOf (name) {
      return (this.data && this.data.distribution && this.data.distribution[name]) || {}
    },
    totalCount () {
      if (!this.data) return 0
      return this.data.grade_names.reduce((s, n) => s + (this.distOf(n).count || 0), 0)
    },
    shareOf (name) {
      const t = this.totalCount()
      return t ? ((this.distOf(name).count || 0) / t * 100).toFixed(1) : '0.0'
    },
    gradeColor (i) {
      return GRADE_COLORS[i % GRADE_COLORS.length]
    },
    gradeSoft (i) {
      return GRADE_SOFT[i % GRADE_SOFT.length]
    },
    rangeText (i) {
      if (!this.data) return ''
      const d = this.data
      const th = d.thresholds || []
      if (th.length === 0) return '—'
      if (i === 0) return '< ' + fmtNum(th[0])
      if (i === d.grade_names.length - 1) return '≥ ' + fmtNum(th[th.length - 1])
      return fmtNum(th[i - 1]) + ' ~ ' + fmtNum(th[i])
    },
    modelShort (m) {
      return { lgbm: 'LightGBM', rf: '随机森林', lr: '逻辑回归' }[m] || m
    },
    modelDesc (m) {
      return {
        lgbm: '梯度提升树，自动处理非线性与特征交互，通常最优',
        rf: 'Bagging 集成树，抗噪但边界更平滑',
        lr: '线性基线，用于验证先验特征是否近似线性可分'
      }[m] || m
    },
    isBest (row) {
      const list = (this.data && this.data.classifier_metrics) || []
      if (!list.length) return false
      const best = list.reduce((a, b) => (b.macro_f1 > a.macro_f1 ? b : a), list[0])
      return best.model === row.model
    },
    /* ---------------- 图表 ---------------- */
    renderShare () {
      const el = this.$refs.shareChart
      if (!el || !this.data) return
      if (!this.charts.share) this.charts.share = echarts.init(el)
      const list = this.data.grade_names.map((n, i) => ({
        name: n,
        value: this.distOf(n).count || 0,
        itemStyle: { color: this.gradeColor(i) }
      }))
      const total = this.totalCount()
      this.charts.share.setOption({
        tooltip: { trigger: 'item', formatter: p => `${p.name}<br/>${fmtNum(p.value)} 条（${p.percent}%）` },
        legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { color: '#64748b', fontSize: 12 } },
        series: [{
          type: 'pie',
          radius: ['52%', '72%'],
          center: ['50%', '44%'],
          avoidLabelOverlap: true,
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold', formatter: '{b}\n{d}%' } },
          data: list
        }],
        graphic: total ? [{
          type: 'text',
          left: 'center',
          top: '36%',
          style: { text: fmtNum(total) + '\n样本', textAlign: 'center', fill: '#1e293b', fontSize: 15, fontWeight: 700, lineHeight: 20 }
        }] : []
      }, true)
    },
    renderRange () {
      const el = this.$refs.rangeChart
      if (!el || !this.data) return
      if (!this.charts.range) this.charts.range = echarts.init(el)
      const names = this.data.grade_names.slice().reverse()
      const idxList = this.data.grade_names.map((n, i) => i).reverse()
      const base = [], span = [], colors = []
      idxList.forEach(i => {
        const d = this.distOf(this.data.grade_names[i])
        const mn = Number(d.min) || 0
        const mx = Number(d.max) || 0
        base.push(mn)
        span.push(Math.max(mx - mn, 0))
        colors.push(this.gradeColor(i))
      })
      this.charts.range.setOption({
        grid: { left: 10, right: 30, top: 16, bottom: 6, containLabel: true },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: p => {
            const i = idxList[names.indexOf(p[0].name)]
            const d = this.distOf(this.data.grade_names[i])
            return `${p[0].name}<br/>样本数：${fmtNum(d.count)} 条<br/>区间：${fmtNum(d.min)} ~ ${fmtNum(d.max)}<br/>均值：${fmtNum(d.mean)}`
          }
        },
        xAxis: {
          type: 'value',
          splitLine: { lineStyle: { color: '#f1f3f8' } },
          axisLabel: { color: '#94a3b8', formatter: v => shortNum(v) }
        },
        yAxis: {
          type: 'category',
          data: names,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: '#475569', fontSize: 12 }
        },
        series: [
          {
            name: 'base',
            type: 'bar',
            stack: 'range',
            silent: true,
            itemStyle: { color: 'transparent' },
            emphasis: { itemStyle: { color: 'transparent' } },
            data: base
          },
          {
            name: '区间跨度',
            type: 'bar',
            stack: 'range',
            barWidth: 16,
            data: span.map((v, i) => ({
              value: v,
              itemStyle: {
                color: colors[i],
                borderRadius: [0, 7, 7, 0]
              }
            })),
            label: {
              show: true,
              position: 'insideRight',
              color: '#fff',
              fontSize: 11,
              formatter: p => {
                const i = idxList[names.indexOf(p.name)]
                const d = this.distOf(this.data.grade_names[i])
                return shortNum(d.min) + ' ~ ' + shortNum(d.max)
              }
            }
          }
        ]
      }, true)
    },
    fmt (v) {
      return v == null ? '-' : Number(v).toFixed(4)
    },
    fmtInt (v) {
      return fmtNum(v)
    }
  }
}

function fmtNum (v) {
  if (v == null || Number.isNaN(Number(v))) return '-'
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })
}

function shortNum (v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '-'
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(1) + '亿'
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(1) + '万'
  return n.toLocaleString('en-US', { maximumFractionDigits: 0 })
}
</script>

<style lang="scss" scoped>
.app-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ---------------- 参数卡 ---------------- */
.ctrl-card {
  .ctrl-row {
    display: flex;
    align-items: center;
    gap: 28px;
    flex-wrap: wrap;
  }
  .ctrl-item {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .ctrl-label {
    font-size: 13px;
    color: var(--app-text-2);
    font-weight: 600;
  }
  .ctrl-tip {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px dashed var(--app-border);
    font-size: 12.5px;
    color: var(--app-text-3);
    line-height: 1.7;
  }
}

.loading-host {
  min-height: 200px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ---------------- 等级卡片 ---------------- */
.grade-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}
.grade-card {
  position: relative;
  background: #fff;
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  box-shadow: var(--app-shadow-1);
  padding: 18px 20px 16px;
  overflow: hidden;
  transition: box-shadow .22s ease, transform .22s ease;

  &:hover {
    box-shadow: var(--app-shadow-2);
    transform: translateY(-2px);
  }

  .grade-bar {
    position: absolute;
    inset: 0 auto 0 0;
    width: 4px;
    background: var(--accent);
  }
  .grade-name {
    display: inline-block;
    font-size: 13px;
    font-weight: 700;
    color: var(--accent);
    background: var(--soft);
    border-radius: 999px;
    padding: 3px 12px;
  }
  .grade-range {
    font-size: 12.5px;
    color: var(--app-text-2);
    margin: 10px 0 4px;
  }
  .grade-count {
    font-size: 26px;
    font-weight: 750;
    color: var(--app-text);
    line-height: 1.2;
    font-variant-numeric: tabular-nums;
  }
  .unit {
    font-size: 13px;
    font-weight: 500;
    color: var(--app-text-3);
    margin-left: 4px;
  }
  .grade-share {
    font-size: 12.5px;
    color: var(--app-text-3);
    margin-top: 2px;
  }
  .grade-mean {
    font-size: 12.5px;
    color: var(--app-text-3);
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed var(--app-border);
  }
}

/* ---------------- 图表 ---------------- */
.chart-row {
  margin: 0 !important;
}
.chart-card .card-head,
.block-card .card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;

  .section-title {
    margin-bottom: 0;
  }
}
.chart-box {
  width: 100%;
  height: 300px;
}
.el-col {
  margin-bottom: 16px;
}
.muted {
  font-size: 12.5px;
  color: var(--app-text-3);
}

/* ---------------- 模型对照 ---------------- */
.model-name {
  font-weight: 650;
  color: var(--app-text);
}
.best-tag {
  margin-left: 8px;
}
.f1-best {
  color: var(--app-success);
}
.model-desc {
  font-size: 12.5px;
  color: var(--app-text-2);
}
.table-tip {
  margin-top: 12px;
  font-size: 12.5px;
  color: var(--app-text-3);
  line-height: 1.7;
}
.fig-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--app-text-3);
  font-size: 13px;
  background: #fafbfe;
}

/* ---------------- 移动端 ---------------- */
@media (max-width: 640px) {
  .grade-cards {
    grid-template-columns: 1fr;
  }
  .chart-box {
    height: 260px;
  }
}
</style>
