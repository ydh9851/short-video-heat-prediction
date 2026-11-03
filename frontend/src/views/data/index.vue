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

    <!-- ============ 质量门禁速览 ============ -->
    <div v-if="quality" class="quality-strip">
      <div class="strip-head">
        <span class="strip-title">数据质量门禁</span>
        <el-tag size="mini" :type="qualityTag(quality.status)" effect="dark">{{ quality.status }}</el-tag>
        <span class="muted">
          通过 {{ quality.passed }} / {{ quality.summary.total }} 项
          <template v-if="quality.stats && quality.stats.psi != null">
            · 热度分布 PSI {{ quality.stats.psi.toFixed(4) }}
          </template>
          <template v-if="quality.stats && quality.stats.rows">
            · {{ Number(quality.stats.rows).toLocaleString() }} 行
          </template>
        </span>
      </div>
      <div class="strip-chips">
        <el-tooltip
          v-for="c in quality.checks"
          :key="c.name"
          :content="c.detail"
          placement="top"
        >
          <span class="chip" :class="chipClass(c.status)">
            <i class="dot" />{{ c.name }}
          </span>
        </el-tooltip>
      </div>
    </div>

    <el-alert
      v-if="platforms.length && !currentPlatformMeta.available"
      type="warning"
      :closable="false"
      show-icon
      class="import-tip"
      title="该平台数据集尚未导入：请把原始数据文件放入 data/raw 目录（文件名需含平台关键字，如 youtube/tiktok/bilibili），然后点击「导入数据集」；算法引擎会自动识别列名并归一化为统一字段。" />

    <!-- ============ 原始数据文件 ============ -->
    <el-card shadow="never" class="raw-card">
      <div class="list-toolbar">
        <div class="section-title">原始数据文件（data/raw）</div>
        <div class="raw-actions">
          <el-select v-model="uploadPlatform" size="small" style="width:120px">
            <el-option v-for="p in uploadPlatforms" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            :on-change="onFileChange"
            accept=".csv,.tsv,.xlsx,.xls,.parquet,.json">
            <el-button size="small">选择文件</el-button>
          </el-upload>
          <span class="muted file-name">{{ uploadFile ? uploadFile.name : '未选择文件' }}</span>
          <el-button size="small" type="primary" :loading="uploading" :disabled="!uploadFile" @click="doUpload">上传</el-button>
          <el-button size="small" :loading="loadingRaw" @click="loadRawFiles">刷新</el-button>
        </div>
      </div>
      <div class="muted raw-hint">
        支持 CSV / TSV / XLSX / Parquet / JSON；上传后自动补平台前缀落到 <code>data/raw/</code>，
        再点顶部「导入数据集」即可完成归一化生效。
      </div>
      <el-table :data="rawFiles" size="small" v-loading="loadingRaw">
        <el-table-column prop="name" label="文件名" min-width="260" show-overflow-tooltip />
        <el-table-column label="可识别平台" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="row.platform ? 'success' : 'info'" effect="light">
              {{ row.platform || '未识别' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sizeMB" label="体积(MB)" width="110" />
        <el-table-column prop="modifiedAt" label="更新时间" width="175" />
      </el-table>
    </el-card>

    <!-- ============ 模型治理入口 ============ -->
    <el-card shadow="never" class="raw-card">
      <div class="list-toolbar">
        <div class="section-title">模型治理</div>
        <div class="raw-actions">
          <el-tag v-if="shadow && shadow.count" size="small" type="info" effect="plain">
            影子：{{ shadow.primaryModel || '线上' }} vs {{ shadow.shadowModel }} · 平均偏差 {{ shadow.meanAbsDiffPct }}%
          </el-tag>
          <el-button size="small" type="primary" plain @click="$router.push('/model/index')">
            前往模型治理页
          </el-button>
        </div>
      </div>
      <el-table :data="models" size="small" v-loading="loadingModels">
        <el-table-column prop="model" label="模型" width="90" />
        <el-table-column prop="activeVersion" label="线上版本" min-width="190" />
        <el-table-column label="阶段" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.stage === 'production' ? 'success' : 'warning'" effect="light">
              {{ row.stage }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="R²(log)" width="110">
          <template #default="{ row }">{{ row.r2 == null ? '-' : row.r2.toFixed(4) }}</template>
        </el-table-column>
        <el-table-column label="版本数" width="90" prop="versionCount" />
        <el-table-column prop="trainedAt" label="训练时间" width="170" />
      </el-table>
    </el-card>

    <!-- ============ 数据质量门禁 ============ -->
    <el-card shadow="never" class="raw-card">
      <div class="list-toolbar">
        <div class="section-title">
          数据质量门禁
          <el-tag v-if="quality" size="small" :type="qualityTag(quality.status)" effect="dark" style="margin-left:8px">
            {{ quality.status }}
          </el-tag>
        </div>
        <div class="raw-actions">
          <span v-if="quality" class="muted">通过 {{ quality.passed }} / {{ quality.summary.total }} 项</span>
          <el-button size="small" type="primary" :loading="checkingQuality" @click="runQuality">运行质检</el-button>
        </div>
      </div>
      <div class="muted raw-hint">
        硬性检查（schema 完整性 / 关键字段缺失率 / 互动量非负 / 时间区间）失败即判 FAIL，应阻断该平台进入建模；
        软性检查（主键重复率 / 类别覆盖 / 热度分布 PSI）仅提示，不阻断。
      </div>
      <el-table v-if="quality" :data="quality.checks" size="small">
        <el-table-column prop="name" label="检查项" min-width="220" />
        <el-table-column label="级别" width="86">
          <template #default="{ row }">
            <el-tag size="small" :type="row.level === 'HARD' ? 'info' : 'warning'" effect="plain">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="88">
          <template #default="{ row }">
            <el-tag size="small" :type="qualityTag(row.status)" effect="light">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="明细" min-width="360" />
      </el-table>
    </el-card>

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
          <app-empty
                compact
                title="没有符合条件的样本"
                description="试试调整筛选条件，或切换到其它平台查看"
              />
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
import modelApi from '@/api/model'
import AppEmpty from '@/components/AppEmpty'

echarts.use([BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, MarkLineComponent, GraphicComponent, CanvasRenderer])

const PALETTE = ['#6366f1', '#8b5cf6', '#a855f7', '#38bdf8', '#22d3ee', '#34d399', '#fbbf24', '#fb7185']

export default {
  name: 'DataManage',
  components: { AppEmpty },
  data () {
    return {
      loadingOverview: false,
      loadingSamples: false,
      importing: false,
      uploading: false,
      loadingRaw: false,
      rawFiles: [],
      uploadFile: null,
      uploadPlatform: 'douyin',
      // 数据质量门禁结果
      quality: null,
      checkingQuality: false,
      // 模型注册表与影子对比
      models: [],
      loadingModels: false,
      syncingModels: false,
      shadow: null,
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
    uploadPlatforms () {
      return [
        { value: 'douyin', label: '抖音' },
        { value: 'youtube', label: 'YouTube' },
        { value: 'tiktok', label: 'TikTok' },
        { value: 'bilibili', label: '哔哩哔哩' }
      ]
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
    this.loadRawFiles()
    this.runQuality()
    this.loadModels()
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
      this.runQuality()
    },
    loadModels () {
      this.loadingModels = true
      modelApi.list().then(re => {
        this.models = (re.response || {}).models || []
        this.loadingModels = false
      }).catch(() => { this.loadingModels = false })
      modelApi.shadow(5).then(re => { this.shadow = re.response || null }).catch(() => {})
    },
    syncModels () {
      this.syncingModels = true
      modelApi.sync().then(() => {
        this.syncingModels = false
        this.$message.success('注册表已同步')
        this.loadModels()
      }).catch(() => { this.syncingModels = false })
    },
    qualityTag (status) {
      if (status === 'PASS') return 'success'
      if (status === 'WARN') return 'warning'
      return 'danger'
    },
    chipClass (status) {
      if (status === 'PASS') return 'chip-pass'
      if (status === 'WARN') return 'chip-warn'
      return 'chip-fail'
    },
    runQuality () {
      this.checkingQuality = true
      dataApi.quality(this.platform).then(re => {
        this.quality = re.response || null
        this.checkingQuality = false
        const st = (this.quality || {}).status
        if (st === 'PASS') this.$message.success('质量检查通过：8 项全部达标')
        else if (st === 'WARN') this.$message.warning('质量检查有提示项，可继续使用')
        else this.$message.error('质量检查未通过，建议先修复数据再建模')
      }).catch(() => { this.checkingQuality = false })
    },
    loadRawFiles () {
      this.loadingRaw = true
      dataApi.rawFiles().then(re => {
        this.rawFiles = (re.response || {}).list || []
        this.loadingRaw = false
      }).catch(() => { this.loadingRaw = false })
    },
    onFileChange (file) {
      this.uploadFile = file.raw || null
    },
    doUpload () {
      if (!this.uploadFile) {
        this.$message.warning('请先选择文件')
        return
      }
      const fd = new FormData()
      fd.append('file', this.uploadFile)
      this.uploading = true
      dataApi.upload(this.uploadPlatform, fd).then(re => {
        const d = re.response || {}
        this.uploading = false
        this.uploadFile = null
        this.$message.success(`上传完成：${d.file}（${d.sizeMB} MB）`)
        this.loadRawFiles()
      }).catch(() => {
        this.uploading = false
        this.$message.error('上传失败，请确认平台与文件格式')
      })
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
      const vals = [h.min, h.q25, h.median, h.q75, h.max]
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

/* ---------------- 原始数据文件 ---------------- */
.raw-card {
  margin-bottom: 16px;

  .raw-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .file-name {
    max-width: 220px;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .raw-hint {
    margin: 4px 0 10px;
    font-size: 12px;
  }
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

/* ============ 质量门禁速览条 ============ */
.quality-strip {
  border: 1px solid #e8ecf6;
  border-radius: 10px;
  background: #fff;
  padding: 12px 14px;
  margin-bottom: 16px;
}

.strip-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.strip-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.strip-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 1;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid transparent;
  cursor: default;

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
  }
}

.chip-pass {
  color: #16a34a;
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.chip-warn {
  color: #d97706;
  background: #fffbeb;
  border-color: #fde68a;
}

.chip-fail {
  color: #dc2626;
  background: #fef2f2;
  border-color: #fecaca;
}
</style>
