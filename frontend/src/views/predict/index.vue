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

              <div class="interval-block">
                <div class="interval-head">
                  <div class="section-title">预测区间（LightGBM 分位数回归）</div>
                  <span v-if="interval" class="coverage-tip">
                    测试集区间覆盖率 {{ pct(interval.coverage_report && interval.coverage_report.coverage) }}
                  </span>
                </div>
                <div v-if="interval" ref="intervalChart" class="interval-chart" />
                <el-empty v-else description="区间模型加载中…" :image-size="60" />
                <div v-if="interval" class="interval-legend">
                  <span><i class="dot p10" />P10 保守 {{ formatNum(interval.interval.p10) }}</span>
                  <span><i class="dot p50" />P50 中性 {{ formatNum(interval.interval.p50) }}</span>
                  <span><i class="dot p90" />P90 乐观 {{ formatNum(interval.interval.p90) }}</span>
                  <span class="muted">区间宽度 {{ formatNum(interval.width) }}</span>
                </div>
              </div>
            </template>

            <el-empty v-else description="在左侧填写参数后点击「开始预测热度」" :image-size="110">
              <div class="empty-hint">
                预测结果将包含：热度值 · 热度等级 · 模型指标 ·<br />P10/P50/P90 三档预测区间
              </div>
            </el-empty>
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
            <template #empty><el-empty description="暂无预测记录" :image-size="70" /></template>
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
import { BarChart, ScatterChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import predictApi from '@/api/predict'
import evaluationApi from '@/api/evaluation'
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

echarts.use([BarChart, ScatterChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

export default {
  name: 'PredictIndex',
  data () {
    return {
      loading: false,
      result: null,
      interval: null,
      intervalLoading: false,
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
    renderIntervalChart () {
      const el = this.$refs.intervalChart
      if (!el || !this.interval) return
      if (!this.charts.interval) this.charts.interval = echarts.init(el)
      const iv = this.interval.interval
      const lower = Math.max(iv.p10, 0)
      const span = Math.max(iv.p90 - lower, 1)
      this.charts.interval.setOption({
        grid: { left: 10, right: 30, top: 26, bottom: 8, containLabel: true },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: () => `P10（保守）：${this.formatNum(iv.p10)}<br/>P50（中性）：${this.formatNum(iv.p50)}<br/>P90（乐观）：${this.formatNum(iv.p90)}`
        },
        xAxis: {
          type: 'value',
          splitLine: { lineStyle: { color: '#f1f3f8' } },
          axisLabel: { color: '#94a3b8', formatter: v => this.fmtInt(v) }
        },
        yAxis: {
          type: 'category',
          data: ['预测区间'],
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: '#475569', fontSize: 12 }
        },
        series: [
          { name: '下限占位', type: 'bar', stack: 'range', data: [lower], itemStyle: { color: 'transparent' }, silent: true, barWidth: 26 },
          {
            name: '区间',
            type: 'bar',
            stack: 'range',
            data: [span],
            barWidth: 26,
            itemStyle: {
              borderRadius: 8,
              color: {
                type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
                colorStops: [{ offset: 0, color: '#c7cbf7' }, { offset: 1, color: '#8b5cf6' }]
              }
            },
            label: {
              show: true,
              position: 'inside',
              color: '#fff',
              fontWeight: 600,
              formatter: () => `P10 ${this.fmtInt(iv.p10)}`
            },
            markLine: {
              silent: true,
              symbol: 'none',
              lineStyle: { color: '#1e293b', width: 2, type: 'solid' },
              label: { formatter: () => `P50 ${this.fmtInt(iv.p50)}`, position: 'end', color: '#1e293b', fontWeight: 600, fontSize: 11 },
              data: [{ xAxis: iv.p50 }]
            }
          }
        ]
      }, true)
      this.charts.interval.resize()
    },
    renderModelChart () {
      const el = this.$refs.modelChart
      if (!el || !this.metrics.length) return
      if (!this.charts.model) this.charts.model = echarts.init(el)
      const nameMap = { lgbm: 'LightGBM', xgb: 'XGBoost', rf: '随机森林', lr: '线性回归', knn: 'K 近邻', dt: '决策树', svm: 'SVR' }
      const list = this.metrics.filter(m => m.trained)
      this.charts.model.setOption({
        grid: { left: 6, right: 16, top: 20, bottom: 6, containLabel: true },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: p => `${p[0].name}<br/>R²(log) = ${Number(p[0].value).toFixed(4)}`
        },
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
              borderRadius: [7, 7, 0, 0],
              color: m.model === 'lgbm'
                ? { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#a855f7' }, { offset: 1, color: '#6366f1' }] }
                : '#c7cbf7'
            }
          })),
          barWidth: '42%',
          label: { show: true, position: 'top', color: '#64748b', fontSize: 11, formatter: p => Number(p.value).toFixed(3) }
        }]
      }, true)
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
        this.$nextTick(this.renderIntervalChart)
      }).catch(() => { this.intervalLoading = false })
    },
    /* ---------------- 批量 ---------------- */
    fillBatchExample () {
      this.batch.text = [
        '美食,50000,20,5,6',
        '音乐,1200,15,2,9',
        '搞笑,80,2,1,3',
        '旅行,800000,21,6,10'
      ].join('\n')
    },
    parseBatch () {
      const lines = (this.batch.text || '').split(/\r?\n/).map(l => l.trim()).filter(l => l)
      if (!lines.length) {
        this.batchError = '请至少输入一行数据'
        return null
      }
      const items = []
      for (let i = 0; i < lines.length; i++) {
        const p = lines[i].split(/[,，]/).map(s => s.trim())
        if (p.length < 5) {
          this.batchError = `第 ${i + 1} 行格式不对，应为：类别,粉丝数,小时,星期,月份`
          return null
        }
        const fans = Number(p[1])
        const hour = Number(p[2])
        const weekday = Number(p[3])
        const month = Number(p[4])
        if ([fans, hour, weekday, month].some(v => Number.isNaN(v))) {
          this.batchError = `第 ${i + 1} 行含非数字字段`
          return null
        }
        if (hour < 0 || hour > 23 || weekday < 0 || weekday > 6 || month < 1 || month > 12) {
          this.batchError = `第 ${i + 1} 行取值超出范围（小时 0-23，星期 0-6，月份 1-12）`
          return null
        }
        items.push({
          videoCategory: p[0],
          authorFans: fans,
          publishHour: hour,
          publishWeekday: weekday,
          publishMonth: month
        })
      }
      if (items.length > 500) {
        this.batchError = '一次最多 500 条'
        return null
      }
      this.batchError = ''
      return items
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

.interval-block {
  .interval-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;

    .section-title { margin-bottom: 0; }
  }
  .coverage-tip {
    font-size: 12px;
    color: #10b981;
    font-weight: 600;
  }
}

.interval-chart {
  width: 100%;
  height: 130px;
}

.interval-legend {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  align-items: center;
  font-size: 12.5px;
  color: #475569;
  padding-top: 4px;

  .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;

    &.p10 { background: #c7cbf7; }
    &.p50 { background: #1e293b; }
    &.p90 { background: #8b5cf6; }
  }
  .muted { color: #94a3b8; }
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
</style>
