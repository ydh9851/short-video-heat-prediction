<template>
  <div class="app-container predict-page">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">热度预测</div>
        <div class="page-desc">
          输入视频<strong>发布时即可获得</strong>的先验信息（类别 / 作者粉丝数 / 发布时段），预测其后续热度，
          并给出「保守—中性—乐观」三档预测区间。
        </div>
      </div>
      <div class="page-head-actions">
        <el-tag type="info" effect="plain">热度 = 播放量 + 3×点赞 + 5×评论 + 8×转发</el-tag>
      </div>
    </div>

    <!-- ==================== ① 单条预测 ==================== -->
    <el-card shadow="never" class="block-card">
      <div class="section-title">单条热度预测</div>

      <el-row :gutter="20">
        <!-- 左：输入 -->
        <el-col :xs="24" :lg="9">
          <div class="form-panel">
            <el-form label-position="top" class="predict-form">
              <el-form-item label="预测模型">
                <el-select v-model="form.model" style="width:100%">
                  <el-option label="LightGBM（推荐，效果最佳）" value="lgbm" />
                  <el-option label="XGBoost" value="xgb" />
                  <el-option label="随机森林 RandomForest" value="rf" />
                  <el-option label="线性回归 LinearRegression" value="lr" />
                  <el-option label="K 近邻回归 KNN" value="knn" />
                  <el-option label="决策树 DecisionTree" value="dt" />
                </el-select>
              </el-form-item>

              <el-form-item label="视频类别">
                <el-select v-model="form.videoCategory" style="width:100%">
                  <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>

              <el-form-item label="作者粉丝数">
                <el-input-number v-model="form.authorFans" :min="0" :step="10000" :controls="false" style="width:100%" />
              </el-form-item>

              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="发布小时（0-23）">
                    <el-input-number v-model="form.publishHour" :min="0" :max="23" style="width:100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="发布星期">
                    <el-select v-model="form.publishWeekday" style="width:100%">
                      <el-option v-for="(w, i) in weekdays" :key="i" :label="w" :value="i" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="发布月份">
                <el-select v-model="form.publishMonth" style="width:100%">
                  <el-option v-for="m in 12" :key="m" :label="m + ' 月'" :value="m" />
                </el-select>
              </el-form-item>

              <el-form-item label="快速填入示例">
                <div class="example-btns">
                  <el-button size="small" @click="fillExample(0)">头部达人 · 晚间</el-button>
                  <el-button size="small" @click="fillExample(1)">腰部作者 · 下午</el-button>
                  <el-button size="small" @click="fillExample(2)">素人 · 凌晨</el-button>
                </div>
              </el-form-item>

              <el-button type="primary" class="predict-btn" :loading="loading" @click="predict">
                开始预测热度
              </el-button>
            </el-form>
          </div>
        </el-col>

        <!-- 右：结果 -->
        <el-col :xs="24" :lg="15">
          <div ref="reportPanel" v-loading="loading || intervalLoading" class="result-panel">
            <template v-if="result">
              <div class="report-head">
                <div>
                  <div class="report-title">热度预测报告</div>
                  <div class="report-meta">{{ reportMeta }}</div>
                </div>
                <div class="report-actions">
                  <el-button size="small" @click="exportReport('png')">导出 PNG</el-button>
                  <el-button size="small" type="primary" plain @click="exportReport('pdf')">导出 PDF</el-button>
                </div>
              </div>
              <div class="kpi-row">
                <div class="kpi">
                  <div class="kpi-label">预测热度（加权互动量）</div>
                  <div class="kpi-value primary">{{ formatNum(result.prediction) }}</div>
                  <div class="kpi-sub">log1p 空间：{{ fmt(result.predictionLog) }}</div>
                </div>
                <div class="kpi">
                  <div class="kpi-label">分级参考</div>
                  <div class="kpi-value" :class="gradeClass(result.prediction)">{{ gradeOf(result.prediction) }}</div>
                  <div class="kpi-sub">低 &lt; 684 ｜ 中 684~15,661 ｜ 高 ≥ 15,661</div>
                </div>
                <div class="kpi">
                  <div class="kpi-label">模型指标（20% 测试集）</div>
                  <div class="kpi-value small">
                    <template v-if="result.metrics">R²(log) = {{ fmt(result.metrics.r2) }}</template>
                    <template v-else>-</template>
                  </div>
                  <div class="kpi-sub">
                    <template v-if="result.metrics">RMSE {{ fmt(result.metrics.rmse) }} ｜ MAE {{ fmt(result.metrics.mae) }}</template>
                    <template v-else>暂无指标</template>
                  </div>
                  <el-tag v-if="result.trainedNow" type="warning" size="small" class="kpi-tag">本次为新训练模型</el-tag>
                  <el-tag v-else type="info" size="small" class="kpi-tag">{{ modelName(result.model) }}</el-tag>
                </div>
              </div>

              <interval-panel :interval="interval" />

              <conformal-panel :conformal="conformal" :loading="conformalLoading" @recalc="loadConformal" />

              <!-- ============ 交互式 what-if ============ -->
              <what-if-panel
                :whatif="whatif"
                :loading="whatifLoading"
                :dimension="whatifDimension"
                @recalc="loadWhatIf"
                @dimension-change="onWhatIfDimensionChange"
              />
            </template>

            <app-empty
              v-else
              title="还没有预测结果"
              description="在左侧填写参数后点击「开始预测热度」，结果将包含：热度值 · 热度等级 · 模型指标 · P10/P50/P90 预测区间 · 90% 保形区间"
            />
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- ==================== ② 批量预测 ==================== -->
    <el-card shadow="never" class="block-card">
      <div class="section-title">批量热度预测</div>
      <el-alert type="success" :closable="false" show-icon class="explain-tip"
                title="每行一条视频，字段用逗号分隔：视频类别, 作者粉丝数, 发布小时(0-23), 发布星期(0-6, 0=周一), 发布月份(1-12)。一次最多 500 条。" />

      <el-row :gutter="20">
        <el-col :xs="24" :lg="10">
          <el-form label-position="top">
            <el-form-item label="预测模型">
              <el-select v-model="batch.model" style="width:100%">
                <el-option label="LightGBM（推荐）" value="lgbm" />
                <el-option label="XGBoost" value="xgb" />
                <el-option label="随机森林 RandomForest" value="rf" />
                <el-option label="线性回归 LinearRegression" value="lr" />
                <el-option label="K 近邻回归 KNN" value="knn" />
                <el-option label="决策树 DecisionTree" value="dt" />
              </el-select>
            </el-form-item>
            <el-form-item label="数据（逗号分隔）">
              <el-input v-model="batch.text" type="textarea" :rows="9"
                        placeholder="美食,50000,20,5,6&#10;音乐,1200,15,2,9&#10;搞笑,80,2,1,3" />
            </el-form-item>
            <el-form-item>
              <el-button @click="fillBatchExample">填入示例</el-button>
              <el-button @click="batch.text = ''">清空</el-button>
              <el-button type="primary" :loading="batchLoading" @click="doBatch">开始批量预测</el-button>
              <span v-if="batchError" class="batch-error">{{ batchError }}</span>
            </el-form-item>
          </el-form>
        </el-col>

        <el-col :xs="24" :lg="14">
          <div class="batch-result">
            <div class="mini-head">
              <span class="mini-title">批量结果</span>
              <span v-if="batchResult" class="muted">共 {{ batchResult.count }} 条 · 模型 {{ modelName(batchResult.model) }}</span>
              <span v-else class="muted">尚未执行</span>
            </div>
            <el-table :data="batchRows" size="small" stripe max-height="330" v-loading="batchLoading"
                      :empty-text="'填写左侧数据后点击「开始批量预测」'">
              <el-table-column type="index" label="#" width="55" />
              <el-table-column prop="video_category" label="类别" width="90" />
              <el-table-column label="粉丝数" width="110">
                <template #default="{ row }">{{ formatNum(row.author_fans) }}</template>
              </el-table-column>
              <el-table-column label="预测热度" min-width="130">
                <template #default="{ row }"><b class="heat-val">{{ formatNum(row.prediction) }}</b></template>
              </el-table-column>
              <el-table-column label="log1p" width="100">
                <template #default="{ row }">{{ fmt(row.prediction_log) }}</template>
              </el-table-column>
              <el-table-column label="热度等级" width="110">
                <template #default="{ row }">
                  <el-tag :type="gradeTag(row.grade)" size="small">{{ row.grade }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- ==================== ③ 模型对比 + ④ 预测记录 ==================== -->
    <el-row :gutter="16">
      <el-col :xs="24" :lg="11">
        <el-card shadow="never" class="block-card">
          <div class="card-head">
            <div class="section-title">多模型效果对比</div>
            <el-button size="small" @click="loadMetrics">刷新</el-button>
          </div>
          <div ref="modelChart" v-loading="metricsLoading" class="model-chart" />
          <el-table :data="metrics" size="small" stripe max-height="260" v-loading="metricsLoading">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column label="模型" min-width="130">
              <template #default="{ row, $index }">
                {{ modelName(row.model) }}
                <el-tag v-if="$index === 0 && row.trained" type="success" size="small">最优</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="RMSE(log)" width="110">
              <template #default="{ row }">{{ fmt(row.rmse) }}</template>
            </el-table-column>
            <el-table-column label="MAE(log)" width="100">
              <template #default="{ row }">{{ fmt(row.mae) }}</template>
            </el-table-column>
            <el-table-column label="R²(log)" width="100">
              <template #default="{ row }">{{ fmt(row.r2) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.trained ? 'info' : 'warning'" size="small">
                  {{ row.trained ? '已训练' : '未训练' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="13">
        <el-card shadow="never" class="block-card">
          <div class="card-head">
            <div class="section-title">预测记录</div>
            <div class="head-actions">
              <span class="muted">共 {{ logTotal }} 条</span>
              <el-button size="small" @click="loadLogs">刷新</el-button>
            </div>
          </div>
          <el-table :data="logs" v-loading="logsLoading" size="small" stripe max-height="330">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="model" label="模型" width="85" />
            <el-table-column prop="videoCategory" label="类别" width="85" />
            <el-table-column label="粉丝数" width="105">
              <template #default="{ row }">{{ fmtInt(row.authorFans) }}</template>
            </el-table-column>
            <el-table-column label="发布信息" min-width="150">
              <template #default="{ row }">{{ period(row) }}</template>
            </el-table-column>
            <el-table-column label="预测热度" min-width="120">
              <template #default="{ row }"><b class="heat-val">{{ fmtInt(row.prediction) }}</b></template>
            </el-table-column>
            <el-table-column label="等级" width="95">
              <template #default="{ row }">
                <el-tag :type="gradeTag(row.grade)" size="small">{{ row.grade }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="来源" width="80">
              <template #default="{ row }">{{ row.source === 'batch' ? '批量' : '单条' }}</template>
            </el-table-column>
            <el-table-column prop="createTime" label="时间" width="165" />
            <template #empty><app-empty compact title="暂无预测记录" /></template>
          </el-table>
          <div class="list-footer">
            <el-pagination
              background
              layout="total, prev, pager, next"
              :total="logTotal"
              :page-size="logSize"
              :current-page="logPage"
              @current-change="onLogPage" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import * as echarts from 'echarts/core'
import { BarChart, ScatterChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, MarkPointComponent, MarkLineComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import predictApi from '@/api/predict'
import { intervalOption, modelOption, whatIfOption } from './charts/options.mjs'
import { parseBatch as parseBatchText } from './batch/parseBatch.mjs'
import IntervalPanel from './panels/IntervalPanel'
import ConformalPanel from './panels/ConformalPanel'
import WhatIfPanel from './panels/WhatIfPanel'
import evaluationApi from '@/api/evaluation'
import AppEmpty from '@/components/AppEmpty'
import { createChart, setChartOption } from '@/utils/chart'
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

echarts.use([BarChart, ScatterChart, LineChart, GridComponent, TooltipComponent, LegendComponent, MarkPointComponent, MarkLineComponent, CanvasRenderer])

export default {
  name: 'PredictIndex',
  components: { AppEmpty, IntervalPanel, ConformalPanel, WhatIfPanel },
  data () {
    return {
      loading: false,
      result: null,
      interval: null,
      intervalLoading: false,
      // 保形预测区间（按需计算，含拟合+校准两段式训练，约 3 秒）
      conformal: null,
      conformalLoading: false,
      // 交互式 what-if（扫描参数取值画响应曲线）
      whatif: null,
      whatifLoading: false,
      whatifDimension: 'publishHour',
      categories: ['搞笑', '美食', '音乐', '美妆', '穿搭', '舞蹈', '旅行', '宠物', '影视', '健身', '情感', '游戏', '生活', '知识'],
      weekdays: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      examples: [
        { videoCategory: '美食', authorFans: 500000, publishHour: 20, publishWeekday: 5, publishMonth: 6 },
        { videoCategory: '旅行', authorFans: 5000, publishHour: 15, publishWeekday: 2, publishMonth: 9 },
        { videoCategory: '搞笑', authorFans: 80, publishHour: 2, publishWeekday: 1, publishMonth: 3 }
      ],
      form: {
        model: 'lgbm',
        videoCategory: '美食',
        authorFans: 50000,
        publishHour: 20,
        publishWeekday: 5,
        publishMonth: 6
      },
      batch: { model: 'lgbm', text: '' },
      batchLoading: false,
      batchError: '',
      batchResult: null,
      batchRows: [],
      metrics: [],
      metricsLoading: false,
      logs: [],
      logsLoading: false,
      logTotal: 0,
      logPage: 1,
      logSize: 10,
      charts: {}
    }
  },
  computed: {
    reportMeta () {
      const r = this.result
      if (!r) return ''
      const d = new Date()
      const pad = n => String(n).padStart(2, '0')
      const date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
      return `类别 ${this.form.videoCategory} · 模型 ${this.modelName(r.model)} · 生成于 ${date}`
    }
  },
  created () {
    this.loadMetrics()
    this.loadLogs()
  },
  mounted () {
    window.addEventListener('resize', this.resizeHandler)
    this.$nextTick(this.renderModelChart)
  },
  beforeUnmount () {
    window.removeEventListener('resize', this.resizeHandler)
    Object.values(this.charts).forEach(c => c && c.dispose())
    this.charts = {}
  },
  methods: {
    /* ---------------- 图表 ---------------- */
    resizeHandler () {
      Object.values(this.charts).forEach(c => c && c.resize())
    },
    /** 预测区间图：P10→P90 浮动条 + P50 标记 */
    renderModelChart () {
      const el = this.$refs.modelChart
      if (!el || !this.metrics.length) return
      if (!this.charts.model) this.charts.model = createChart(echarts, el)
      setChartOption(this.charts.model, modelOption(this.metrics), true)
      this.charts.model.resize()
    },
    /* ---------------- 预测 ---------------- */
    fillExample (idx) {
      Object.assign(this.form, this.examples[idx])
    },
    predict () {
      this.loading = true
      this.interval = null
      predictApi.predict({ ...this.form }).then(re => {
        this.result = re.response || {}
        this.loading = false
        this.logPage = 1
        this.loadLogs()
      }).catch(() => { this.loading = false })
      this.predictInterval()
    },
    /** 预测区间（分位数回归）—— 与点预测并行请求 */
    predictInterval () {
      this.intervalLoading = true
      evaluationApi.run({
        mode: 'quantile',
        category: this.form.videoCategory,
        fans: this.form.authorFans,
        hour: this.form.publishHour,
        weekday: this.form.publishWeekday,
        month: this.form.publishMonth
      }).then(re => {
        this.interval = re.response || null
        this.intervalLoading = false
          }).catch(() => { this.intervalLoading = false })
    },
    /**
     * 90% 保形预测区间：走独立接口（拟合集 + 校准集两段式训练，约 3 秒），
     * 与上面的分位数回归区间形成「有保证 / 无保证」的对照。
     */
    loadConformal () {
      this.conformalLoading = true
      predictApi.interval({ ...this.form }).then(re => {
        this.conformal = re.response || null
        this.conformalLoading = false
        if (this.conformal) {
          this.$message.success('保形区间已生成：' +
            this.formatNum(this.conformal.lo) + ' ~ ' + this.formatNum(this.conformal.hi))
        }
      }).catch(() => { this.conformalLoading = false })
    },
    /* ---------------- 批量 ---------------- */
    /**
     * 交互式 what-if：让用户在预测页直接探索「改哪个参数能提多少」。
     * 后端在同一个已训练模型上扫描该维度的全部候选取值，一次返回完整序列。
     */
    onWhatIfDimensionChange (val) {
      this.whatifDimension = val
      this.loadWhatIf()
    },
    loadWhatIf () {
      this.whatifLoading = true
      predictApi.whatIf({
        dimension: this.whatifDimension,
        videoCategory: this.form.videoCategory,
        authorFans: this.form.authorFans,
        publishHour: this.form.publishHour,
        publishWeekday: this.form.publishWeekday,
        publishMonth: this.form.publishMonth,
        model: this.form.model
      }).then(re => {
        this.whatif = re.response || null
        this.whatifLoading = false
        if (this.whatif) {
          }
      }).catch(() => { this.whatifLoading = false })
    },
    fillBatchExample () {
      this.batch.text = [
        '美食,50000,20,5,6',
        '音乐,1200,15,2,9',
        '搞笑,80,2,1,3',
        '旅行,800000,21,6,10'
      ].join('\n')
    },
    parseBatch () {
      const { items, error } = parseBatchText(this.batch.text)
      this.batchError = error
      return error ? null : items
    },
    doBatch () {
      const items = this.parseBatch()
      if (!items) return
      this.batchLoading = true
      predictApi.predictBatch({ model: this.batch.model, items }).then(re => {
        this.batchResult = re.response || null
        this.batchRows = (this.batchResult && this.batchResult.results) || []
        this.batchLoading = false
        this.logPage = 1
        this.loadLogs()
      }).catch(() => { this.batchLoading = false })
    },
    /* ---------------- 指标 / 记录 ---------------- */
    loadMetrics () {
      this.metricsLoading = true
      predictApi.metrics().then(re => {
        this.metrics = (re.response && re.response.models) || []
        this.metricsLoading = false
        this.$nextTick(this.renderModelChart)
      }).catch(() => { this.metricsLoading = false })
    },
    loadLogs () {
      this.logsLoading = true
      predictApi.logs({ page: this.logPage, size: this.logSize }).then(re => {
        const r = re.response || {}
        this.logs = r.list || []
        this.logTotal = r.total || 0
        this.logsLoading = false
      }).catch(() => { this.logsLoading = false })
    },
    onLogPage (p) {
      this.logPage = p
      this.loadLogs()
    },
    /* ---------------- 报告导出 ---------------- */
    async exportReport (type) {
      const el = this.$refs.reportPanel
      if (!el) return
      this.$message.info('正在生成报告…')
      try {
        const canvas = await html2canvas(el, { backgroundColor: '#ffffff', scale: 2, useCORS: true })
        const date = new Date().toISOString().slice(0, 10)
        const base = `热度预测报告_${this.form.videoCategory}_${date}`
        if (type === 'png') {
          const a = document.createElement('a')
          a.href = canvas.toDataURL('image/png')
          a.download = base + '.png'
          a.click()
        } else {
          const img = canvas.toDataURL('image/png')
          const pdf = new jsPDF({ orientation: 'p', unit: 'pt', format: 'a4' })
          const pageW = pdf.internal.pageSize.getWidth()
          const pageH = pdf.internal.pageSize.getHeight()
          const margin = 24
          const imgW = pageW - margin * 2
          const imgH = canvas.height * imgW / canvas.width
          let heightLeft = imgH
          pdf.addImage(img, 'PNG', margin, margin, imgW, imgH)
          heightLeft -= (pageH - margin * 2)
          while (heightLeft > 0) {
            pdf.addPage()
            pdf.addImage(img, 'PNG', margin, margin - (imgH - heightLeft), imgW, imgH)
            heightLeft -= (pageH - margin * 2)
          }
          pdf.save(base + '.pdf')
        }
        this.$message.success('报告已导出')
      } catch (e) {
        this.$message.error('报告导出失败：' + (e && e.message ? e.message : e))
      }
    },
    /* ---------------- 格式化 ---------------- */
    period (row) {
      if (row.publishHour == null) return '-'
      const wd = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
      return `${row.publishHour} 点 / ${wd[row.publishWeekday] || '-'} / ${row.publishMonth} 月`
    },
    modelName (m) {
      return {
        lgbm: 'LightGBM', xgb: 'XGBoost', rf: '随机森林', lr: '线性回归', knn: 'K 近邻', svm: 'SVR', dt: '决策树'
      }[m] || m
    },
    fmtInt (v) {
      const n = Number(v)
      if (v == null || v === '' || !Number.isFinite(n)) return '-'
      return n.toLocaleString('en-US', { maximumFractionDigits: 0 })
    },
    formatNum (v) {
      return this.fmtInt(v)
    },
    fmt (v) {
      const n = Number(v)
      if (v == null || v === '' || !Number.isFinite(n)) return '-'
      return n.toFixed(3)
    },
    pct (v) {
      const n = Number(v)
      if (v == null || v === '' || !Number.isFinite(n)) return '-'
      return (n * 100).toFixed(1) + '%'
    },
    gradeOf (v) {
      if (v == null) return '-'
      if (v < 684) return '低热度'
      if (v < 15661) return '中热度'
      return '高热度'
    },
    gradeClass (v) {
      if (v == null) return ''
      if (v < 684) return 'grade-low'
      if (v < 15661) return 'grade-mid'
      return 'grade-high'
    },
    gradeTag (g) {
      return { 低热度: 'info', 中热度: 'warning', 高热度: 'danger' }[g] || 'info'
    }
  }
}
</script>

<style lang="scss" scoped>
.predict-page {
  .block-card {
    margin-bottom: 16px;
  }
}

/* ---------------- 单条预测 ---------------- */
.form-panel {
  background: #fafbfe;
  border: 1px solid #eef0f6;
  border-radius: 14px;
  padding: 6px 18px 18px;

  ::v-deep .el-form-item {
    margin-bottom: 15px;
  }
  ::v-deep .el-form-item__label {
    padding-bottom: 4px;
    font-size: 12.5px;
    color: #64748b;
    font-weight: 600;
  }
}

.predict-btn {
  width: 100%;
  height: 42px;
  font-weight: 600;
}

.example-btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.result-panel {
  min-height: 470px;
  border: 1px solid #eef0f6;
  border-radius: 14px;
  padding: 18px 20px;
  background: #fff;
}

.report-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  margin-bottom: 16px;
  border-bottom: 1px solid #eef0f6;

  .report-title {
    font-size: 16px;
    font-weight: 750;
    color: #1e293b;
  }
  .report-meta {
    font-size: 12px;
    color: #94a3b8;
    margin-top: 4px;
  }
  .report-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.kpi {
  position: relative;
  background: #fafbfe;
  border: 1px solid #eef0f6;
  border-radius: 12px;
  padding: 14px 16px;

  .kpi-label {
    font-size: 12px;
    color: #94a3b8;
  }
  .kpi-value {
    font-size: 26px;
    font-weight: 750;
    line-height: 1.3;
    margin-top: 6px;
    font-variant-numeric: tabular-nums;

    &.primary { color: var(--app-primary); }
    &.small { font-size: 19px; }
    &.grade-low { color: #94a3b8; }
    &.grade-mid { color: #f59e0b; }
    &.grade-high { color: #ef4444; }
  }
  .kpi-sub {
    font-size: 11.5px;
    color: #b6bec9;
    margin-top: 5px;
  }
  .kpi-tag {
    position: absolute;
    top: 12px;
    right: 12px;
  }
}




.empty-hint {
  font-size: 12.5px;
  line-height: 1.9;
  color: #94a3b8;
  margin-top: 6px;
}

/* ---------------- 通用 ---------------- */
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;

  .section-title { margin-bottom: 0; }
  .head-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    .muted { font-size: 12.5px; color: #94a3b8; }
  }
}

.explain-tip {
  margin-bottom: 16px;
}

.batch-error {
  color: #ef4444;
  font-size: 12.5px;
  margin-left: 10px;
}

.batch-result {
  .mini-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;

    .mini-title {
      font-size: 13.5px;
      font-weight: 650;
      color: #1e293b;
    }
    .muted { font-size: 12.5px; color: #94a3b8; }
  }
}

.model-chart {
  width: 100%;
  height: 190px;
}

.heat-val {
  color: var(--app-primary);
}

.list-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 10px;
}

/* ============ 保形区间区块 ============ */





/* ============ 交互式 what-if ============ */






</style>
