<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">平台对比</div>
        <div class="page-desc">
          多平台短视频数据集横向对比：样本规模、热度分布、作者粉丝规模与类目集中度。
          各平台原始数据经 <code>algorithm/datasets/ingest.py</code> 归一化到同一套字段后参与对比，
          用于论证「热度驱动因素是否跨平台可迁移」。
        </div>
      </div>
      <div class="page-head-actions">
        <el-tag type="info" effect="plain">统一热度口径：播放 + 3×点赞 + 5×评论 + 8×转发</el-tag>
      </div>
    </div>

    <!-- ============ 平台状态卡 ============ -->
    <div class="plat-grid" v-loading="loading">
      <div
        v-for="p in platforms"
        :key="p.platform"
        class="plat-card"
        :class="{ off: !p.available }">
        <div class="plat-head">
          <span class="plat-name">{{ p.displayName || p.platform }}</span>
          <el-tag :type="p.available ? 'success' : 'info'" size="small" effect="light">
            {{ p.available ? '已导入' : '未导入' }}
          </el-tag>
          <el-tag v-if="p.isDefault" size="small" effect="plain">默认训练集</el-tag>
        </div>
        <template v-if="p.available">
          <div class="plat-rows">{{ fmtInt(p.rows) }}<span class="unit">条视频</span></div>
          <div class="plat-meta">
            <span>{{ p.categoryCount || 0 }} 个类别</span>
            <span class="dot">·</span>
            <span>{{ (p.timeStart || '').slice(0, 10) }} ~ {{ (p.timeEnd || '').slice(0, 10) }}</span>
          </div>
          <div class="plat-stats">
            <div><em>热度中位数</em><b>{{ fmtInt(p.heat && p.heat.median) }}</b></div>
            <div><em>热度 P90</em><b>{{ fmtInt(p.heat && p.heat.p90) }}</b></div>
            <div><em>粉丝中位数</em><b>{{ fmtInt(p.fans && p.fans.median) }}</b></div>
          </div>
        </template>
        <div v-else class="plat-empty">
          尚未导入。把该平台数据文件放到 <code>data/raw</code>（文件名含平台关键字），
          再到「数据管理」页选择该平台点击「导入数据集」。
        </div>
      </div>
    </div>

    <!-- ============ 对比图表 ============ -->
    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :lg="13">
        <el-card shadow="never" class="chart-card">
          <div class="card-head">
            <div class="section-title">热度分位数对比</div>
            <el-tag size="small" type="warning">纵轴为对数刻度</el-tag>
          </div>
          <div v-if="availablePlatforms.length" ref="heatChart" class="chart-box" />
          <el-empty v-else description="暂无已导入的平台数据，请先在「数据管理」页导入数据集" :image-size="80" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="11">
        <el-card shadow="never" class="chart-card">
          <div class="card-head">
            <div class="section-title">类目集中度对比</div>
            <el-tag size="small" type="info">Top1 / Top3 / Top10 占比</el-tag>
          </div>
          <div v-if="availablePlatforms.length" ref="concentrationChart" class="chart-box" />
          <el-empty v-else description="暂无已导入的平台数据" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ============ 元信息对照表 ============ -->
    <el-card shadow="never" class="block-card">
      <div class="card-head">
        <div class="section-title">数据集元信息对照</div>
        <span class="muted">字段映射与口径差异如实记录，便于论文中说明</span>
      </div>
      <el-table :data="platforms" size="small" stripe>
        <el-table-column prop="displayName" label="平台" width="110" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.available ? 'success' : 'info'" size="small" effect="light">
              {{ row.available ? '已导入' : '未导入' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="样本量" width="110">
          <template #default="{ row }">{{ row.available ? fmtInt(row.rows) : '-' }}</template>
        </el-table-column>
        <el-table-column label="类别数" width="90">
          <template #default="{ row }">{{ row.available ? row.categoryCount : '-' }}</template>
        </el-table-column>
        <el-table-column label="时间跨度" min-width="200">
          <template #default="{ row }">
            {{ row.available ? (row.timeStart || '').slice(0, 10) + ' ~ ' + (row.timeEnd || '').slice(0, 10) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="热度中位数" width="120">
          <template #default="{ row }">{{ row.available ? fmtInt(row.heat && row.heat.median) : '-' }}</template>
        </el-table-column>
        <el-table-column label="粉丝数口径" min-width="150">
          <template #default="{ row }">{{ fansLabel(row.platform) }}</template>
        </el-table-column>
        <el-table-column label="转发字段" width="110">
          <template #default="{ row }">
            <span v-if="!row.available">-</span>
            <el-tag v-else :type="row.shareAvailable ? 'success' : 'warning'" size="small" effect="light">
              {{ row.shareAvailable ? '有' : '缺失记 0' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="原始文件" min-width="240">
          <template #default="{ row }">
            <span class="mono">{{ row.rawFile || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ============ 类目覆盖 ============ -->
    <el-row v-if="availablePlatforms.length" :gutter="16" class="chart-row">
      <el-col v-for="p in availablePlatforms" :key="p.platform" :xs="24" :lg="8">
        <el-card shadow="never" class="block-card">
          <div class="section-title">{{ p.displayName }} · Top 类别</div>
          <div class="cat-list">
            <div v-for="(c, i) in topCats(p)" :key="c.name" class="cat-item">
              <span class="cat-idx">{{ i + 1 }}</span>
              <span class="cat-name">{{ c.name }}</span>
              <span class="cat-count">{{ fmtInt(c.count) }}</span>
              <span class="cat-bar"><i :style="{ width: catPct(p, c.count) + '%' }" /></span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ============ 结论 ============ -->
    <el-card shadow="never" class="block-card">
      <div class="section-title">跨平台对比结论与口径说明</div>
      <ul class="conclusion-list">
        <li>
          <b>热度口径</b>：统一为「播放量 + 3×点赞 + 5×评论 + 8×转发」。YouTube 公开数据无转发字段，
          该平台转发项按 0 计入——这会在对比表中标注，论文中需作为 limitation 说明。
        </li>
        <li>
          <b>作者规模口径</b>：抖音 = 作者粉丝数；YouTube = 频道订阅数；B 站 = UP 主粉丝数。
          三者语义一致，均可作为「作者先验影响力」的代理变量，正是本系统最重要的特征。
        </li>
        <li>
          <b>可用性差异</b>：各平台发布时间、类别体系、样本量与采集时间窗口不同，
          因此跨平台结论应聚焦「特征的相对重要性排序是否一致」，而非绝对数值可比。
        </li>
        <li>
          <b>下一步</b>：在「模型评估」页对每个平台分别训练 LightGBM 并输出 SHAP 特征贡献，
          即可得到跨平台的特征重要性排名对照。
        </li>
      </ul>
    </el-card>
  </div>
</template>

<script>
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import dataApi from '@/api/data'

echarts.use([BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const PLAT_COLORS = ['#6366f1', '#ef4444', '#0ea5e9', '#10b981']

export default {
  name: 'PlatformComparison',
  data () {
    return {
      loading: false,
      platforms: [],
      charts: {}
    }
  },
  computed: {
    availablePlatforms () {
      return this.platforms.filter(p => p.available && p.heat)
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
    resizeHandler () {
      Object.values(this.charts).forEach(c => c && c.resize())
    },
    sidebarResizeHandler (e) {
      if (e.propertyName === 'width') this.resizeHandler()
    },
    load () {
      this.loading = true
      dataApi.platforms().then(re => {
        this.platforms = (re.response && re.response.platforms) || []
        this.loading = false
        this.$nextTick(() => {
          this.renderHeat()
          this.renderConcentration()
        })
      }).catch(() => { this.loading = false })
    },
    fansLabel (platform) {
      return { douyin: '作者粉丝数', youtube: '频道订阅数', tiktok: '作者粉丝数', bilibili: 'UP 主粉丝数' }[platform] || '作者粉丝数'
    },
    topCats (p) {
      const cats = (p.categories || {})
      return Object.keys(cats).map(k => ({ name: k, count: cats[k] }))
        .sort((a, b) => b.count - a.count).slice(0, 8)
    },
    catPct (p, count) {
      const list = this.topCats(p)
      const max = list.length ? list[0].count : 0
      return max ? Math.round(count / max * 100) : 0
    },
    concentration (p) {
      const cats = (p.categories || {})
      const vals = Object.keys(cats).map(k => cats[k]).sort((a, b) => b - a)
      const total = vals.reduce((s, v) => s + v, 0) || 1
      const sum = n => vals.slice(0, n).reduce((s, v) => s + v, 0)
      return {
        top1: +(sum(1) / total * 100).toFixed(1),
        top3: +(sum(3) / total * 100).toFixed(1),
        top10: +(sum(10) / total * 100).toFixed(1)
      }
    },
    /* ---------------- 热度分位对比 ---------------- */
    renderHeat () {
      const el = this.$refs.heatChart
      if (!el) return
      if (!this.charts.heat) this.charts.heat = echarts.init(el)
      const list = this.availablePlatforms
      const pos = v => (v == null || Number(v) <= 0 ? null : Number(v))
      const mk = (name, key) => ({
        name,
        type: 'bar',
        barGap: '12%',
        data: list.map(p => pos(p.heat && p.heat[key])),
        itemStyle: { borderRadius: [6, 6, 0, 0] }
      })
      this.charts.heat.setOption({
        grid: { left: 10, right: 16, top: 34, bottom: 6, containLabel: true },
        legend: { top: 0, icon: 'roundRect', itemWidth: 9, itemHeight: 9, textStyle: { color: '#64748b', fontSize: 12 } },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: p => p.map(x => `${x.seriesName}：${x.value == null ? '-' : this.fmtInt(x.value)}`).join('<br/>')
            .replace(/^/, p[0].axisValue + '<br/>')
        },
        xAxis: {
          type: 'category',
          data: list.map(p => p.displayName),
          axisLine: { lineStyle: { color: '#e6e9f0' } },
          axisTick: { show: false },
          axisLabel: { color: '#475569', fontSize: 12 }
        },
        yAxis: {
          type: 'log',
          logBase: 10,
          splitLine: { lineStyle: { color: '#f1f3f8' } },
          axisLabel: { color: '#94a3b8', formatter: v => this.fmtShort(v) }
        },
        series: [
          mk('P25', 'q25'),
          mk('中位数', 'median'),
          mk('P75', 'q75'),
          mk('P90', 'p90')
        ]
      }, true)
    },
    /* ---------------- 类目集中度 ---------------- */
    renderConcentration () {
      const el = this.$refs.concentrationChart
      if (!el) return
      if (!this.charts.conc) this.charts.conc = echarts.init(el)
      const list = this.availablePlatforms.map(p => p.displayName)
      const data = this.availablePlatforms.map(p => this.concentration(p))
      this.charts.conc.setOption({
        grid: { left: 10, right: 20, top: 34, bottom: 6, containLabel: true },
        legend: { top: 0, icon: 'roundRect', itemWidth: 9, itemHeight: 9, textStyle: { color: '#64748b', fontSize: 12 } },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: p => p.map(x => `${x.seriesName}：${x.value}%`).join('<br/>').replace(/^/, p[0].axisValue + '<br/>') },
        xAxis: {
          type: 'category', data: list,
          axisLine: { lineStyle: { color: '#e6e9f0' } },
          axisTick: { show: false },
          axisLabel: { color: '#475569', fontSize: 12 }
        },
        yAxis: {
          type: 'value', max: 100,
          splitLine: { lineStyle: { color: '#f1f3f8' } },
          axisLabel: { color: '#94a3b8', formatter: '{value}%' }
        },
        series: ['top1', 'top3', 'top10'].map((k, i) => ({
          name: ['Top1 占比', 'Top3 占比', 'Top10 占比'][i],
          type: 'bar',
          data: data.map(d => d[k]),
          barWidth: '20%',
          itemStyle: {
            borderRadius: [6, 6, 0, 0],
            color: PLAT_COLORS[i]
          },
          label: { show: true, position: 'top', color: '#64748b', fontSize: 10, formatter: '{c}%' }
        }))
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
      if (n >= 1e8) return (n / 1e8).toFixed(1) + '亿'
      if (n >= 1e4) return (n / 1e4).toFixed(1) + '万'
      return String(Math.round(n))
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

.plat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}
.plat-card {
  background: #fff;
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  box-shadow: var(--app-shadow-1);
  padding: 18px 20px;
  transition: box-shadow .22s ease, transform .22s ease;

  &:hover {
    box-shadow: var(--app-shadow-2);
    transform: translateY(-2px);
  }
  &.off {
    background: linear-gradient(180deg, #fcfcff, #fafbfe);
  }

  .plat-head {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 10px;
  }
  .plat-name {
    font-size: 15px;
    font-weight: 700;
    color: var(--app-text);
  }
  .plat-rows {
    font-size: 26px;
    font-weight: 750;
    color: var(--app-primary);
    line-height: 1.2;
    font-variant-numeric: tabular-nums;

    .unit {
      font-size: 13px;
      font-weight: 500;
      color: var(--app-text-3);
      margin-left: 4px;
    }
  }
  .plat-meta {
    font-size: 12.5px;
    color: var(--app-text-2);
    margin-top: 4px;

    .dot {
      margin: 0 6px;
      color: var(--app-text-3);
    }
  }
  .plat-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px dashed var(--app-border);

    div {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }
    em {
      font-style: normal;
      font-size: 11px;
      color: var(--app-text-3);
      white-space: nowrap;
    }
    b {
      font-size: 13.5px;
      color: var(--app-text);
      font-variant-numeric: tabular-nums;
    }
  }
  .plat-empty {
    font-size: 12.5px;
    color: var(--app-text-3);
    line-height: 1.75;
  }
  code {
    background: #f2f4fa;
    border-radius: 4px;
    padding: 1px 5px;
    font-size: 12px;
  }
}

.chart-row {
  margin: 0 !important;
}
.chart-card,
.block-card {
  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
    flex-wrap: wrap;

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
.muted {
  font-size: 12.5px;
  color: var(--app-text-3);
}
.mono {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  color: var(--app-text-2);
}

.cat-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.cat-item {
  display: grid;
  grid-template-columns: 18px 74px 1fr 76px;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;

  .cat-idx {
    color: #aeb5c7;
    font-weight: 700;
    font-size: 11px;
  }
  .cat-name {
    color: var(--app-text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cat-count {
    color: var(--app-text-2);
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .cat-bar {
    height: 6px;
    border-radius: 999px;
    background: #eef1f7;
    overflow: hidden;

    i {
      display: block;
      height: 100%;
      border-radius: 999px;
      background: var(--app-primary-gradient);
    }
  }
}

.conclusion-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.9;
  color: var(--app-text-2);

  li {
    margin-bottom: 6px;
  }
  b {
    color: var(--app-text);
  }
}

@media (max-width: 640px) {
  .plat-grid {
    grid-template-columns: 1fr;
  }
  .chart-box {
    height: 260px;
  }
}
</style>
