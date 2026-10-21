<template>
  <div class="app-container dashboard">
    <!-- ============ Hero ============ -->
    <section class="hero">
      <div class="hero-glow hero-glow-1" />
      <div class="hero-glow hero-glow-2" />
      <div class="hero-content">
        <div class="hero-text">
          <span class="hero-badge">LightGBM · SHAP · K-Means</span>
          <h1>短视频热度预测与归因分析</h1>
          <p>
            输入发布时的先验信息（类别 / 作者粉丝数 / 发布时段），预测视频后续热度，
            并用 SHAP 解释「为什么火」，用聚类给出热度分级。
          </p>
        </div>
        <div class="hero-actions">
          <router-link to="/predict/index">
            <el-button class="hero-btn hero-btn-primary">开始热度预测</el-button>
          </router-link>
          <router-link to="/attribution/index">
            <el-button class="hero-btn hero-btn-ghost">查看归因分析</el-button>
          </router-link>
        </div>
      </div>
    </section>

    <!-- ============ KPI ============ -->
    <div class="stat-grid" v-loading="loadingOverview">
      <div v-for="k in kpis" :key="k.label" class="stat-card">
        <div class="stat-icon" :class="'tone-' + k.tone">
          <svg-icon :icon-class="k.icon" />
        </div>
        <div class="stat-body">
          <div class="stat-label">{{ k.label }}</div>
          <div class="stat-value">
            <count-to v-if="!k.loading" :start-val="0" :end-val="k.num" :duration="1400" :decimals="k.decimals" />
            <span v-else class="stat-loading">加载中…</span>
          </div>
          <div class="stat-sub">{{ k.sub }}</div>
        </div>
      </div>
    </div>

    <!-- ============ 项目关键指标（实验结论） ============ -->
    <el-card shadow="never" class="key-card">
      <div class="card-head">
        <div class="section-title">项目关键指标 · 实验结论速览</div>
        <router-link to="/evaluation/index">
          <el-button link type="primary" size="small">查看完整实验 ›</el-button>
        </router-link>
      </div>

      <div class="key-body">
        <!-- 核心指标 -->
        <div class="key-metrics">
          <div v-for="m in keyMetrics" :key="m.label" class="key-metric">
            <div class="km-label">{{ m.label }}</div>
            <div class="km-value" :class="m.tone">{{ m.value }}</div>
            <div class="km-sub">{{ m.sub }}</div>
          </div>
        </div>

        <!-- 实验清单 -->
        <div class="key-exp">
          <div class="key-exp-head">
            <span class="key-exp-title">9 类离线实验</span>
            <span class="key-exp-hint">点击前往「模型评估」运行</span>
          </div>
          <div class="key-exp-list">
            <div
              v-for="(e, i) in modes"
              :key="e.mode"
              class="key-exp-item"
              @click="$router.push('/evaluation/index')">
              <span class="exp-idx">{{ String(i + 1).padStart(2, '0') }}</span>
              <span class="exp-name">{{ e.name }}</span>
              <span class="exp-tag">{{ e.tag }}</span>
            </div>
            <el-empty v-if="!modes.length" description="实验元信息加载中…" :image-size="60" />
          </div>
        </div>
      </div>

      <div class="key-tip">
        交叉验证与区间覆盖率来自「模型评估」模块的可复现实验结果；消融实验显示周期编码对树模型增益有限（−0.0005），
        说明 LightGBM 已能从日期特征中自行学习时间模式；三方重要性度量的第一名均为「作者粉丝数」，
        印证了先验粉丝规模是短视频热度的最强信号。
      </div>
    </el-card>

    <!-- ============ 图表行 1 ============ -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="chart-card">
          <div class="card-head">
            <div class="section-title">视频类别样本分布</div>
            <el-tag size="small" type="info">{{ categoryCount }} 个类别</el-tag>
          </div>
          <div ref="categoryChart" v-loading="loadingOverview" class="chart-box" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="chart-card">
          <div class="card-head">
            <div class="section-title">热度等级分布</div>
            <el-tag size="small" type="info">K-Means 分级</el-tag>
          </div>
          <div ref="gradeChart" v-loading="loadingOverview" class="chart-box" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ============ 图表行 2 ============ -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="chart-card">
          <div class="card-head">
            <div class="section-title">多模型效果对比（R²·log 空间）</div>
            <el-tag size="small" type="success">LightGBM 最优</el-tag>
          </div>
          <div ref="modelChart" v-loading="loadingMetrics" class="chart-box" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="chart-card">
          <div class="card-head">
            <div class="section-title">最近预测记录</div>
            <router-link to="/predict/index"><el-button link type="primary" size="small">查看全部</el-button></router-link>
          </div>
          <el-table :data="logs" v-loading="loadingLogs" size="small" :show-header="true">
            <el-table-column prop="videoCategory" label="类别" width="90" />
            <el-table-column label="粉丝数" width="110">
              <template #default="{ row }">{{ fmtInt(row.authorFans) }}</template>
            </el-table-column>
            <el-table-column prop="model" label="模型" width="90" />
            <el-table-column label="预测热度" min-width="130">
              <template #default="{ row }"><b class="heat-val">{{ fmtInt(row.prediction) }}</b></template>
            </el-table-column>
            <el-table-column label="等级" width="100">
              <template #default="{ row }">
                <el-tag :type="gradeTag(row.grade)" size="small" effect="light">{{ row.grade }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="createTime" label="时间" width="170" />
            <template #empty>
              <el-empty description="暂无预测记录，去「热度预测」试试" :image-size="72" />
            </template>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import * as echarts from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, GraphicComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import CountTo from '@/components/CountTo'
import dataApi from '@/api/data'
import predictApi from '@/api/predict'
import evaluationApi from '@/api/evaluation'

echarts.use([BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, GraphicComponent, CanvasRenderer])

const PALETTE = ['#6366f1', '#8b5cf6', '#a855f7', '#38bdf8', '#22d3ee', '#34d399', '#fbbf24', '#fb7185']

export default {
  name: 'Dashboard',
  components: { CountTo },
  data () {
    return {
      loadingOverview: false,
      loadingMetrics: false,
      loadingLogs: false,
      total: 0,
      categoryCount: 0,
      medianHeat: 0,
      bestR2: 0,
      bestModel: '-',
      categories: [],
      gradeDistribution: [],
      models: [],
      logs: [],
      modes: [],
      charts: {}
    }
  },
  computed: {
    kpis () {
      return [
        { label: '数据样本总量', num: Number(this.total) || 0, decimals: 0, icon: 'table', tone: 'indigo', sub: '规范化训练数据集' },
        { label: '视频类别数', num: Number(this.categoryCount) || 0, decimals: 0, icon: 'chart', tone: 'violet', sub: '覆盖的短视频内容类目' },
        { label: '热度中位数', num: Number(this.medianHeat) || 0, decimals: 0, icon: 'star', tone: 'blue', sub: '加权互动量 · 全体样本' },
        { label: '最佳模型 R²(log)', num: Number(this.bestR2) || 0, decimals: 3, icon: 'skill', tone: 'green', loading: this.loadingMetrics, sub: this.bestModel === '-' ? '模型指标加载中' : '最优模型：' + this.bestModel }
      ]
    },
    keyMetrics () {
      return [
        { label: '5 折交叉验证 R²', value: '0.8221', tone: 'indigo', sub: '标准差 ±0.0036 · 结果稳定' },
        { label: '分位数区间覆盖率', value: '76.4%', tone: 'blue', sub: 'P10–P90 区间 · 名义 80%' },
        { label: '残差 P50 / P90', value: '176.9 / 14197', tone: 'violet', sub: '中位 / 长尾误差量级' },
        { label: '最优超参数', value: 'lr 0.02', tone: 'green', sub: 'num_leaves 31 · 特征采样 0.8 · bagging 1.0' },
        { label: '消融 ΔR²（周期编码）', value: '−0.0005', tone: 'slate', sub: '树模型无增益 · 线性模型 +0.0024' },
        { label: '最强特征（三方一致）', value: '作者粉丝数', tone: 'amber', small: true, sub: '增益 / 置换 / SHAP 度量均列第一' }
      ]
    }
  },
  created () {
    this.loadOverview()
    this.loadMetrics()
    this.loadLogs()
    this.loadModes()
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
    renderCharts () {
      this.renderCategory()
      this.renderGrade()
      this.renderModels()
    },
    /* ---- 类别分布 ---- */
    renderCategory () {
      const el = this.$refs.categoryChart
      if (!el) return
      if (!this.charts.category) this.charts.category = echarts.init(el)
      const list = (this.categories || []).slice(0, 12).slice().reverse()
      this.charts.category.setOption({
        grid: { left: 10, right: 24, top: 12, bottom: 6, containLabel: true },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        xAxis: { type: 'value', splitLine: { lineStyle: { color: '#f1f3f8' } }, axisLabel: { color: '#94a3b8' } },
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
              colorStops: [
                { offset: 0, color: '#6366f1' },
                { offset: 1, color: '#a855f7' }
              ]
            }
          },
          label: { show: true, position: 'right', color: '#94a3b8', fontSize: 11 }
        }]
      }, true)
    },
    /* ---- 热度等级 ---- */
    renderGrade () {
      const el = this.$refs.gradeChart
      if (!el) return
      if (!this.charts.grade) this.charts.grade = echarts.init(el)
      const colorMap = { 低热度: '#94a3b8', 中热度: '#f59e0b', 高热度: '#ef4444' }
      const data = (this.gradeDistribution || []).map((g, i) => ({
        name: g.grade,
        value: g.count,
        itemStyle: { color: colorMap[g.grade] || PALETTE[i % PALETTE.length] }
      }))
      const totalCnt = data.reduce((s, d) => s + (d.value || 0), 0)
      this.charts.grade.setOption({
        tooltip: { trigger: 'item', formatter: '{b}: {c} 条 ({d}%)' },
        legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { color: '#64748b', fontSize: 12 } },
        series: [{
          type: 'pie',
          radius: ['52%', '72%'],
          center: ['50%', '44%'],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: '#fff', borderWidth: 3, borderRadius: 6 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 15, fontWeight: 'bold', formatter: '{b}\n{d}%' } },
          data
        }],
        graphic: totalCnt ? [{
          type: 'text',
          left: 'center',
          top: '38%',
          style: { text: this.fmtInt(totalCnt) + '\n样本', textAlign: 'center', fill: '#1e293b', fontSize: 15, fontWeight: 700, lineHeight: 20 }
        }] : []
      }, true)
    },
    /* ---- 模型对比 ---- */
    renderModels () {
      const el = this.$refs.modelChart
      if (!el) return
      if (!this.charts.model) this.charts.model = echarts.init(el)
      const nameMap = { lgbm: 'LightGBM', xgb: 'XGBoost', rf: '随机森林', lr: '线性回归', knn: 'K 近邻', dt: '决策树', svm: 'SVR' }
      const list = (this.models || []).filter(m => m.trained)
      this.charts.model.setOption({
        grid: { left: 10, right: 20, top: 16, bottom: 6, containLabel: true },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => `${p[0].name}<br/>R²(log) = ${p[0].value.toFixed(4)}` },
        xAxis: {
          type: 'category',
          data: list.map(m => nameMap[m.model] || m.model),
          axisLine: { lineStyle: { color: '#e6e9f0' } },
          axisTick: { show: false },
          axisLabel: { color: '#64748b', fontSize: 11, interval: 0 }
        },
        yAxis: { type: 'value', max: 1, splitLine: { lineStyle: { color: '#f1f3f8' } }, axisLabel: { color: '#94a3b8' } },
        series: [{
          type: 'bar',
          data: list.map(m => ({
            value: m.r2,
            itemStyle: {
              borderRadius: [8, 8, 0, 0],
              color: m.model === 'lgbm'
                ? {
                    type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                      { offset: 0, color: '#a855f7' },
                      { offset: 1, color: '#6366f1' }
                    ]
                  }
                : '#c7cbf7'
            }
          })),
          barWidth: '46%',
          label: { show: true, position: 'top', color: '#64748b', fontSize: 11, formatter: p => p.value.toFixed(3) }
        }]
      }, true)
    },
    /* ---- 数据加载 ---- */
    loadOverview () {
      this.loadingOverview = true
      dataApi.overview().then(re => {
        const d = re.response || {}
        this.total = d.total || 0
        this.categoryCount = d.categoryCount || 0
        this.medianHeat = (d.heat && d.heat.median) || 0
        this.categories = d.categories || []
        this.gradeDistribution = d.gradeDistribution || []
        this.loadingOverview = false
        this.$nextTick(this.renderCharts)
      }).catch(() => { this.loadingOverview = false })
    },
    loadMetrics () {
      this.loadingMetrics = true
      predictApi.metrics().then(re => {
        const models = (re.response && re.response.models) || []
        this.models = models
        const trained = models.filter(m => m.trained).sort((a, b) => b.r2 - a.r2)
        if (trained.length) {
          this.bestR2 = trained[0].r2
          const nameMap = { lgbm: 'LightGBM', xgb: 'XGBoost', rf: '随机森林', lr: '线性回归', knn: 'K 近邻', dt: '决策树', svm: 'SVR' }
          this.bestModel = nameMap[trained[0].model] || trained[0].model
        }
        this.loadingMetrics = false
        this.$nextTick(this.renderModels)
      }).catch(() => { this.loadingMetrics = false })
    },
    loadLogs () {
      this.loadingLogs = true
      predictApi.logs({ page: 1, size: 8 }).then(re => {
        this.logs = (re.response && re.response.list) || []
        this.loadingLogs = false
      }).catch(() => { this.loadingLogs = false })
    },
    loadModes () {
      evaluationApi.modes().then(re => {
        this.modes = re.response || []
      }).catch(() => { this.modes = [] })
    },
    fmtInt (v) {
      if (v == null || Number.isNaN(Number(v))) return '-'
      return Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })
    },
    gradeTag (g) {
      return { 低热度: 'info', 中热度: 'warning', 高热度: 'danger' }[g] || 'info'
    }
  }
}
</script>

<style lang="scss" scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ---------------- Hero ---------------- */
.hero {
  position: relative;
  border-radius: 18px;
  overflow: hidden;
  padding: 30px 34px;
  background: linear-gradient(120deg, #4f46e5 0%, #6366f1 45%, #8b5cf6 100%);
  box-shadow: 0 14px 34px rgba(79, 70, 229, .28);

  .hero-glow {
    position: absolute;
    border-radius: 50%;
    filter: blur(60px);
    opacity: .45;
    pointer-events: none;
  }
  .hero-glow-1 {
    width: 340px;
    height: 340px;
    background: #c084fc;
    top: -140px;
    right: 40px;
  }
  .hero-glow-2 {
    width: 260px;
    height: 260px;
    background: #38bdf8;
    bottom: -150px;
    left: -40px;
    opacity: .3;
  }

  .hero-content {
    position: relative;
    z-index: 2;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
    flex-wrap: wrap;
  }

  .hero-badge {
    display: inline-block;
    font-size: 11.5px;
    letter-spacing: 1px;
    font-weight: 600;
    color: #fff;
    background: rgba(255, 255, 255, .18);
    border: 1px solid rgba(255, 255, 255, .28);
    border-radius: 999px;
    padding: 4px 12px;
    margin-bottom: 14px;
  }

  h1 {
    font-size: 25px;
    font-weight: 800;
    color: #fff;
    margin: 0 0 10px;
    letter-spacing: .4px;
  }

  p {
    font-size: 13.5px;
    line-height: 1.75;
    color: rgba(255, 255, 255, .84);
    margin: 0;
    max-width: 620px;
  }

  .hero-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .hero-btn {
    height: 42px;
    padding: 0 22px;
    border-radius: 11px;
    font-size: 14px;
    font-weight: 600;
  }
  .hero-btn-primary {
    background: #fff;
    color: #4f46e5;
    border: none;
    box-shadow: 0 8px 20px rgba(0, 0, 0, .16);

    &:hover {
      background: #f5f6ff;
      color: #4338ca;
    }
  }
  .hero-btn-ghost {
    background: rgba(255, 255, 255, .14);
    color: #fff;
    border: 1px solid rgba(255, 255, 255, .42);

    &:hover {
      background: rgba(255, 255, 255, .24);
      color: #fff;
    }
  }
}

/* ---------------- KPI ---------------- */
.stat-card {
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

  .stat-icon {
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

  .stat-body {
    min-width: 0;
    flex: 1;
  }

  .stat-label {
    font-size: 13px;
    color: #94a3b8;
  }

  .stat-value {
    font-size: 25px;
    font-weight: 750;
    color: #1e293b;
    line-height: 1.35;
    margin-top: 4px;
    font-variant-numeric: tabular-nums;
  }

  .stat-loading {
    font-size: 14px;
    font-weight: 400;
    color: #b6bec9;
  }

  .stat-sub {
    font-size: 11.5px;
    color: #b6bec9;
    margin-top: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

/* ---------------- 关键指标 ---------------- */
.key-card {
  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;

    .section-title {
      margin-bottom: 0;
    }
  }
}

.key-body {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(0, 1fr);
  gap: 22px;
}

.key-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 12px;
}

.key-metric {
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius-sm);
  background: linear-gradient(180deg, #fcfcff, #ffffff);
  padding: 13px 15px;
  transition: border-color .2s ease, box-shadow .2s ease;

  &:hover {
    border-color: #d7d9f7;
    box-shadow: 0 6px 16px rgba(99, 102, 241, .08);
  }

  .km-label {
    font-size: 12px;
    color: var(--app-text-3);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .km-value {
    font-size: 22px;
    font-weight: 750;
    line-height: 1.3;
    margin-top: 4px;
    font-variant-numeric: tabular-nums;
    letter-spacing: .2px;

    &.indigo { color: #6366f1; }
    &.blue { color: #0ea5e9; }
    &.violet { color: #8b5cf6; }
    &.green { color: #10b981; }
    &.slate { color: #64748b; }
    &.amber { color: #d97706; }
    &.small {
      font-size: 16px;
      font-weight: 700;
    }
  }
  .km-sub {
    font-size: 11.5px;
    color: #b6bec9;
    margin-top: 4px;
    line-height: 1.5;
  }
}

.key-exp {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-left: 1px solid var(--app-border);
  padding-left: 22px;

  .key-exp-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
  }
  .key-exp-title {
    font-size: 13.5px;
    font-weight: 650;
    color: var(--app-text);
  }
  .key-exp-hint {
    font-size: 11.5px;
    color: var(--app-text-3);
  }
  .key-exp-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .key-exp-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 9px;
    border-radius: 8px;
    cursor: pointer;
    transition: background .18s ease;

    &:hover {
      background: var(--app-primary-soft);

      .exp-name {
        color: var(--app-primary);
      }
    }

    .exp-idx {
      font-size: 11px;
      font-weight: 700;
      color: #aeb5c7;
      font-variant-numeric: tabular-nums;
      flex-shrink: 0;
    }
    .exp-name {
      font-size: 12.8px;
      color: var(--app-text);
      flex: 1;
      min-width: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      transition: color .18s ease;
    }
    .exp-tag {
      font-size: 11px;
      color: var(--app-text-3);
      background: #f4f6fa;
      border-radius: 999px;
      padding: 2px 8px;
      flex-shrink: 0;
    }
  }
}

.key-tip {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed var(--app-border);
  font-size: 12.5px;
  color: var(--app-text-3);
  line-height: 1.8;
}

/* ---------------- 图表卡片 ---------------- */
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

.heat-val {
  color: #6366f1;
}

.el-col {
  margin-bottom: 16px;
}

@media (max-width: 992px) {
  .key-body {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .key-exp {
    border-left: 0;
    padding-left: 0;
    border-top: 1px dashed var(--app-border);
    padding-top: 14px;
  }
}

@media (max-width: 640px) {
  .hero {
    padding: 24px 20px;
  }
  .hero h1 {
    font-size: 20px;
  }
  .stat-grid {
    grid-template-columns: 1fr;
  }
  .chart-box {
    height: 260px;
  }
}
</style>
