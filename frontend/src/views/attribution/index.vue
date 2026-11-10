<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">归因分析</div>
        <div class="page-desc">
          基于 SHAP（Shapley 值）解释<strong>「为什么这条视频会火 / 不火」</strong>：
          全局特征重要性、单条贡献拆解、特征依赖关系、交互效应，并把归因结论转化为可执行的运营建议。
        </div>
      </div>
      <div class="page-head-actions">
        <el-tag type="info" effect="plain">SHAP 值在 log1p(热度) 空间计算</el-tag>
      </div>
    </div>

    <!-- ==================== 解释可信度徽章（引用实验结论） ==================== -->
    <div v-if="quality" class="trust-strip">
      <span class="trust-label">本次解释可信度</span>
      <el-tooltip content="紧凑性：解释 80% 平均绝对贡献所需特征数，越小越可概括" placement="top">
        <span class="trust-chip">紧凑性 k80 = <b>{{ quality.compacity.k80 }}</b></span>
      </el-tooltip>
      <el-tooltip content="一致性：SHAP 排序与增益重要性的 Kendall τ，越接近 1 越一致" placement="top">
        <span class="trust-chip">一致性 τ = <b>{{ fmt(quality.consistency.kendall_shap_vs_gain, 2) }}</b></span>
      </el-tooltip>
      <el-tooltip content="稳定性：bootstrap 重训后 Top-K 特征集合的 Jaccard，1 表示完全一致" placement="top">
        <span class="trust-chip">稳定性 Jaccard = <b>{{ fmt(quality.stability.jaccard_mean, 3) }}</b></span>
      </el-tooltip>
      <span class="trust-note">来自最近一次「解释质量评估」实验</span>
      <router-link to="/evaluation/index">
        <el-button link type="primary" size="small">重跑该实验 ›</el-button>
      </router-link>
    </div>

    <!-- ==================== ① 全局归因 ==================== -->
    <el-card shadow="never" class="block-card" v-loading="globalLoading">
      <div class="card-head">
        <div class="section-title">全局归因</div>
        <el-button size="small" @click="loadGlobal">刷新</el-button>
      </div>

      <el-row :gutter="16">
        <el-col :xs="24" :md="12">
          <div class="fig-title">全局特征重要性（SHAP 平均绝对贡献）</div>
          <el-image :src="fig('/attribution/', 'global_importance.png')" :preview-src-list="[fig('/attribution/', 'global_importance.png')]"
                    fit="contain" class="fig-img" lazy />
        </el-col>
        <el-col :xs="24" :md="12">
          <div class="fig-title">SHAP 汇总图（特征取值与贡献方向）</div>
          <el-image :src="fig('/attribution/', 'shap_summary.png')" :preview-src-list="[fig('/attribution/', 'shap_summary.png')]"
                    fit="contain" class="fig-img" lazy />
        </el-col>
      </el-row>

      <div class="fig-title" style="margin-top:18px">特征重要性排行</div>
      <el-table :data="globalTop" stripe size="small">
        <el-table-column type="index" label="#" width="60" />
        <el-table-column prop="feature_cn" label="特征" min-width="160" />
        <el-table-column prop="feature" label="字段名" min-width="150" />
        <el-table-column label="重要性（平均 |SHAP|）" min-width="200">
          <template #default="{ row }">
            <el-progress :percentage="pct(row.importance)" :stroke-width="14"
                         :format="() => row.importance.toFixed(3)" />
          </template>
        </el-table-column>
        <template #empty><app-empty compact title="暂无全局归因结果" /></template>
      </el-table>
    </el-card>

    <!-- ==================== ② 单条视频归因 + ④ 反事实 ==================== -->
    <el-card shadow="never" class="block-card">
      <div class="card-head">
        <div class="section-title">单条视频归因与反事实分析</div>
        <el-button size="small" @click="useExample">填入示例</el-button>
      </div>

      <!-- 输入 -->
      <div v-if="currentCase" class="case-banner">
        <span>已应用场景「{{ currentCase.name }}」的参数，可直接归因或微调</span>
        <el-button link type="primary" size="small" @click="clearCase">清除</el-button>
      </div>
      <div class="input-bar">
        <div class="field">
          <span class="field-label">视频类别</span>
          <el-select v-model="form.videoCategory" style="width:120px">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </div>
        <div class="field">
          <span class="field-label">作者粉丝数</span>
          <el-input-number v-model="form.authorFans" :min="0" :step="10000" :controls="false" style="width:130px" />
        </div>
        <div class="field">
          <span class="field-label">发布小时</span>
          <el-input-number v-model="form.publishHour" :min="0" :max="23" style="width:120px" />
        </div>
        <div class="field">
          <span class="field-label">星期</span>
          <el-select v-model="form.publishWeekday" style="width:100px">
            <el-option v-for="(w, i) in weekdays" :key="i" :label="w" :value="i" />
          </el-select>
        </div>
        <div class="field">
          <span class="field-label">月份</span>
          <el-select v-model="form.publishMonth" style="width:92px">
            <el-option v-for="m in 12" :key="m" :label="m + ' 月'" :value="m" />
          </el-select>
        </div>
        <div class="field-actions">
          <el-button type="primary" :loading="explainLoading" @click="doExplain">归因分析</el-button>
          <el-button :loading="cfLoading" @click="doCounterfactual">反事实分析</el-button>
        </div>
      </div>

      <!-- 单条归因结果 -->
      <template v-if="explain">
        <explanation-report
          :explain="explain"
          :quality="quality"
          :cf="cf"
          :refutation="refutation"
          :form="form" />

        <el-row :gutter="16" class="explain-row">
          <el-col :xs="24" :lg="13">
            <div class="fig-title">
              特征贡献（交互式）· 预测 {{ fmt(explain.prediction) }} · 基线 {{ fmt(explain.base_value) }}
            </div>
            <div ref="contribChart" class="contrib-chart" />
            <div class="contrib-legend">
              <span><i class="dot pos" />正贡献（拉高热度）</span>
              <span><i class="dot neg" />负贡献（拉低热度）</span>
              <span class="muted">单位：log1p 空间</span>
            </div>
          </el-col>
          <el-col :xs="24" :lg="11">
            <div class="fig-title">单样本 SHAP 瀑布图</div>
            <el-image :src="fig('/attribution/', 'shap_waterfall.png', true)"
                      :preview-src-list="[fig('/attribution/', 'shap_waterfall.png', true)]"
                      fit="contain" class="fig-img-lg" lazy />
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :xs="24" :lg="11">
            <div class="fig-title">特征贡献明细（log 空间）</div>
            <el-table :data="explain.contributions" size="small" stripe max-height="300">
              <el-table-column prop="feature_cn" label="特征" min-width="130" />
              <el-table-column label="贡献" width="110">
                <template #default="{ row }">
                  <span :class="row.shap >= 0 ? 'pos-text' : 'neg-text'">
                    {{ row.shap >= 0 ? '+' : '' }}{{ row.shap.toFixed(3) }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </el-col>
          <el-col :xs="24" :lg="13">
            <div class="fig-title">
              运营建议（归因 → 决策）
              <el-button size="small" style="float:right" @click="exportReport">导出 CSV</el-button>
              <el-button size="small" type="primary" style="float:right;margin-right:8px"
                         :loading="reportLoading" @click="doReport">生成报告(HTML)</el-button>
              <router-link to="/report/index" style="float:right;margin-right:10px">
                <el-button link type="primary" size="small">报告中心 ›</el-button>
              </router-link>
            </div>
            <ul class="advice-list">
              <li v-for="(a, i) in explain.advice" :key="i">{{ a }}</li>
            </ul>
          </el-col>
        </el-row>
      </template>
      <app-empty v-else title="还没有归因结果" description="填写上方参数后点击「归因分析」" />
    </el-card>

    <!-- ==================== ④ 反事实结果 ==================== -->
    <el-card v-if="cf" shadow="never" class="block-card">
      <div class="card-head">
        <div class="section-title">反事实分析（可调整维度的提升空间）</div>
        <el-tag size="small" type="info">当前预测 {{ formatNum(cf.base_heat) }} · {{ cf.base_grade }}</el-tag>
      </div>
      <el-row :gutter="16">
        <el-col :xs="24" :lg="14">
          <el-table :data="cf.suggestions" size="small" stripe>
            <el-table-column prop="dimension" label="可调整维度" width="120" />
            <el-table-column prop="from" label="当前" width="110" />
            <el-table-column prop="to" label="建议" width="110" />
            <el-table-column label="预计热度" min-width="130">
              <template #default="{ row }"><b class="heat-val">{{ formatNum(row.heat) }}</b></template>
            </el-table-column>
            <el-table-column label="提升幅度" width="120">
              <template #default="{ row }">
                <span :class="row.delta_pct > 0 ? 'pos-text' : 'neg-text'">
                  {{ row.delta_pct > 0 ? '+' : '' }}{{ row.delta_pct.toFixed(1) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="grade" label="预计等级" width="110" />
            <template #empty><app-empty compact title="当前条件已是最优，无可调整提升项" /></template>
          </el-table>
          <div class="non-mutable" v-if="cf.non_mutable">
            <el-icon><svg-icon icon-class="lock" /></el-icon>
            <span v-for="n in cf.non_mutable" :key="n.dimension">
              <b>{{ n.dimension }}</b>（{{ formatNum(n.value) }}）不可单条调整：{{ n.note }}
            </span>
          </div>
        </el-col>
        <el-col :xs="24" :lg="10">
          <div class="fig-title">提升空间对比</div>
          <el-image v-if="cf.figure" :src="fig('/attribution/', cf.figure, true)"
                    :preview-src-list="[fig('/attribution/', cf.figure, true)]"
                    fit="contain" class="fig-img" lazy />
          <app-empty v-else compact title="无可视化（已是最优）" />
        </el-col>
      </el-row>
      <div v-if="refutation" class="stability-warn">
        <b>稳定性提示</b>：上表是模型内插值的点估计，不是真实因果效应。
        <template v-if="refutation.stability && refutation.stability.hour_gain">
          子集重估显示发布小时增益的变异系数 CV = {{ refutation.stability.hour_gain.cv }}
          （区间 {{ Math.round(refutation.stability.hour_gain.min * 100) }}% ~
          {{ Math.round(refutation.stability.hour_gain.max * 100) }}%），最优取值在重训之间会漂移；
        </template>
        请按「<b>方向 + 区间</b>」理解这些建议，不要当作精确的收益承诺。
        <router-link to="/evaluation/index">
          <el-button link type="primary" size="small">查看稳健性检验 ›</el-button>
        </router-link>
      </div>
    </el-card>

    <!-- ==================== ③ 特征依赖关系 PDP ==================== -->
    <el-card shadow="never" class="block-card">
      <div class="card-head">
        <div class="section-title">特征依赖关系（PDP）</div>
        <div class="head-actions">
          <el-select v-model="pdpFeature" style="width:210px" size="small">
            <el-option v-for="f in pdpOptions" :key="f.value" :label="f.label" :value="f.value" />
          </el-select>
          <el-button type="primary" size="small" :loading="pdpLoading" @click="doPdp">生成图</el-button>
        </div>
      </div>
      <el-alert v-if="pdp" type="success" :closable="false" show-icon class="explain-tip"
                :title="`最优取值点：${pdpFeatureLabel} = ${fmt(pdp.best_point.x)}，平均热度 ≈ ${formatNum(pdp.best_point.avg_heat)}`" />
      <div v-loading="pdpLoading">
        <el-image v-if="pdp" :src="fig('/attribution/', pdp.figure, true)"
                  :preview-src-list="[fig('/attribution/', pdp.figure, true)]"
                  fit="contain" class="fig-img-lg" lazy />
        <app-empty v-else title="还没有 PDP 图" description="选择特征后点击「生成图」" />
      </div>
    </el-card>

    <!-- ==================== ⑤ 特征交互效应 ==================== -->
    <el-card shadow="never" class="block-card">
      <div class="card-head">
        <div class="section-title">特征交互效应（SHAP Interaction）</div>
        <el-button type="primary" size="small" :loading="interLoading" @click="doInteraction">计算交互效应</el-button>
      </div>
      <el-alert type="success" :closable="false" show-icon class="explain-tip"
                title="量化「两个特征共同作用」带来的额外贡献：若交互值远小于主效应，说明模型以单特征效应为主，特征作用基本可加。" />

      <template v-if="interaction">
        <el-row :gutter="16">
          <el-col :xs="24" :lg="12">
            <el-table :data="interaction.top_pairs" size="small" stripe>
              <el-table-column type="index" label="#" width="55" />
              <el-table-column prop="feature_a_cn" label="特征 A" min-width="130" />
              <el-table-column prop="feature_b_cn" label="特征 B" min-width="130" />
              <el-table-column label="平均 |交互值|" min-width="140">
                <template #default="{ row }">{{ row.interaction.toFixed(4) }}</template>
              </el-table-column>
            </el-table>
            <div class="main-effect" v-if="interaction.main_effects">
              <div class="main-effect-title">主效应强度对照</div>
              <div v-for="m in interaction.main_effects.slice(0, 4)" :key="m.feature" class="main-effect-row">
                <span class="me-name">{{ m.feature_cn }}</span>
                <el-progress :percentage="Math.min(100, Math.round(m.main_effect / interaction.main_effects[0].main_effect * 100))"
                             :stroke-width="12" :format="() => m.main_effect.toFixed(4)" />
              </div>
            </div>
          </el-col>
          <el-col :xs="24" :lg="12">
            <div class="fig-title">交互效应 Top 组合</div>
            <el-image v-if="interaction.figure" :src="fig('/attribution/', interaction.figure, true)"
                      :preview-src-list="[fig('/attribution/', interaction.figure, true)]"
                      fit="contain" class="fig-img" lazy />
          </el-col>
        </el-row>
      </template>
      <app-empty v-else title="还没有交互效应结果" description="点击「计算交互效应」运行（首次约需 20-40 秒）" />
    </el-card>
  </div>
</template>

<script>
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import attributionApi from '@/api/attribution'
import reportApi from '@/api/report'
import AppEmpty from '@/components/AppEmpty'
import ExplanationReport from './panels/ExplanationReport'
import evaluationApi from '@/api/evaluation'
import { mapGetters } from 'vuex'

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

export default {
  name: 'AttributionIndex',
  components: { AppEmpty, ExplanationReport },
  data () {
    return {
      globalLoading: false,
      globalTop: [],
      categories: ['搞笑', '美食', '音乐', '美妆', '穿搭', '舞蹈', '旅行', '宠物', '影视', '健身', '情感', '游戏', '生活', '知识'],
      weekdays: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      form: {
        videoCategory: '美食',
        authorFans: 50000,
        publishHour: 3,
        publishWeekday: 2,
        publishMonth: 9
      },
      explain: null,
      explainLoading: false,
      reportLoading: false,
      cf: null,
      cfLoading: false,
      // 引用实验台账中的结论：解释质量三指标 + 反事实稳健性
      quality: null,
      refutation: null,
      pdpFeature: 'author_fans_log',
      pdp: null,
      pdpLoading: false,
      pdpOptions: [
        { value: 'author_fans_log', label: '作者粉丝数(log)' },
        { value: 'publish_hour', label: '发布小时' },
        { value: 'publish_weekday', label: '发布星期' },
        { value: 'publish_month', label: '发布月份' },
        { value: 'video_category', label: '视频类别' },
        { value: 'hour_bucket', label: '发布时段' }
      ],
      interaction: null,
      interLoading: false,
      charts: {}
    }
  },
  computed: {
    ...mapGetters(['currentCase']),
    pdpFeatureLabel () {
      const o = this.pdpOptions.find(x => x.value === this.pdpFeature)
      return o ? o.label : this.pdpFeature
    }
  },
  created () {
    this.applyCurrentCase(this.currentCase)
    this.loadGlobal()
    this.doPdp()
    this.loadTrust()
  },
  watch: {
    currentCase (val) {
      this.applyCurrentCase(val)
    }
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
    // 读取实验台账中最近一次的「解释质量评估」与「反事实稳健性检验」结论
    loadTrust () {
      evaluationApi.latest('explanation-quality').then(re => {
        this.quality = re.response || null
      }).catch(() => { this.quality = null })
      evaluationApi.latest('refutation').then(re => {
        this.refutation = re.response || null
      }).catch(() => { this.refutation = null })
    },
    fmt (v, digits) {
      if (v == null) return '-'
      return Number(v).toFixed(digits == null ? 3 : digits)
    },
    resizeHandler () {
      Object.values(this.charts).forEach(c => c && c.resize())
    },
    sidebarResizeHandler (e) {
      if (e.propertyName === 'width') this.resizeHandler()
    },
    fig (prefix, name, bust) {
      return prefix + name + (bust ? ('?t=' + Date.now()) : '')
    },
    loadGlobal () {
      this.globalLoading = true
      attributionApi.global().then(re => {
        this.globalTop = (re.response && re.response.top_features) || []
        this.globalLoading = false
      }).catch(() => { this.globalLoading = false })
    },
    pct (v) {
      if (!this.globalTop.length || !this.globalTop[0].importance) return 0
      return Math.round(v / this.globalTop[0].importance * 100)
    },
    useExample () {
      Object.assign(this.form, { videoCategory: '美食', authorFans: 50000, publishHour: 3, publishWeekday: 2, publishMonth: 9 })
    },
    /** 填充当前分析场景的先验参数（归因页不涉及模型选择，模型由后端 active 版本决定） */
    applyCurrentCase (c) {
      if (!c) return
      Object.assign(this.form, {
        videoCategory: c.videoCategory,
        authorFans: c.authorFans,
        publishHour: c.publishHour,
        publishWeekday: c.publishWeekday,
        publishMonth: c.publishMonth
      })
    },
    clearCase () {
      this.$store.dispatch('caseStudy/clearCurrent')
    },
    doExplain () {
      this.explainLoading = true
      attributionApi.explain({ ...this.form }).then(re => {
        this.explain = re.response || null
        this.explainLoading = false
        this.$nextTick(this.renderContribChart)
      }).catch(() => { this.explainLoading = false })
    },
    /** SHAP 贡献横向条形图：正贡献绿、负贡献红 */
    renderContribChart () {
      const el = this.$refs.contribChart
      if (!el || !this.explain) return
      if (!this.charts.contrib) this.charts.contrib = echarts.init(el)
      const list = (this.explain.contributions || []).slice().reverse()
      this.charts.contrib.setOption({
        grid: { left: 10, right: 46, top: 10, bottom: 10, containLabel: true },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: p => {
            const v = Number(p[0].value)
            return `${p[0].name}<br/>SHAP = ${v >= 0 ? '+' : ''}${v.toFixed(4)}<br/>${v >= 0 ? '拉高预测热度' : '拉低预测热度'}`
          }
        },
        xAxis: {
          type: 'value',
          splitLine: { lineStyle: { color: '#f1f3f8' } },
          axisLabel: { color: '#94a3b8' }
        },
        yAxis: {
          type: 'category',
          data: list.map(c => c.feature_cn),
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: { color: '#475569', fontSize: 11.5 }
        },
        series: [{
          type: 'bar',
          data: list.map(c => ({
            value: c.shap,
            itemStyle: { color: c.shap >= 0 ? '#10b981' : '#ef4444', borderRadius: 5 }
          })),
          barWidth: 14,
          label: {
            show: true,
            position: 'right',
            color: '#64748b',
            fontSize: 11,
            formatter: p => (Number(p.value) >= 0 ? '+' : '') + Number(p.value).toFixed(3)
          }
        }]
      }, true)
      this.charts.contrib.resize()
    },
    doCounterfactual () {
      this.cfLoading = true
      evaluationApi.run({
        mode: 'counterfactual',
        category: this.form.videoCategory,
        fans: this.form.authorFans,
        hour: this.form.publishHour,
        weekday: this.form.publishWeekday,
        month: this.form.publishMonth
      }).then(re => {
        this.cf = re.response || null
        this.cfLoading = false
      }).catch(() => { this.cfLoading = false })
    },
    doInteraction () {
      this.interLoading = true
      evaluationApi.run({ mode: 'interaction' }).then(re => {
        this.interaction = re.response || null
        this.interLoading = false
        if (this.interaction && this.interaction.note) {
          this.$message.success('交互效应计算完成')
        }
      }).catch(() => { this.interLoading = false })
    },
    doPdp () {
      this.pdpLoading = true
      attributionApi.pdp(this.pdpFeature).then(re => {
        this.pdp = re.response || null
        this.pdpLoading = false
      }).catch(() => { this.pdpLoading = false })
    },
    doReport () {
      this.reportLoading = true
      const payload = { ...this.form }
      // 有当前场景时携带 caseId：报告与场景联动，记录场景名称快照
      if (this.currentCase && this.currentCase.id) {
        payload.caseId = this.currentCase.id
        payload.name = '归因报告 · ' + this.currentCase.name
      } else {
        payload.name = '归因报告 · ' + this.form.videoCategory
      }
      reportApi.generate(payload).then(re => {
        const reportId = re.response.reportId
        this.$message.success('已提交生成（异步），完成后将自动打开；也可在报告中心查看')
        this.pollReport(reportId)
      }).catch(() => {
        this.reportLoading = false
      })
    },
    // 递归轮询报告状态：DONE 自动打开，FAILED 提示原因
    pollReport (reportId) {
      reportApi.get(reportId).then(re => {
        const r = re.response
        if (!r) {
          this.reportLoading = false
          return
        }
        if (r.status === 'DONE') {
          this.reportLoading = false
          window.open('/api/report/' + r.id + '/content', '_blank')
          this.$message.success('报告已生成（' + (r.sizeKb || '-') + ' KB），已在新标签页打开；可在「报告中心」管理/分享')
        } else if (r.status === 'FAILED') {
          this.reportLoading = false
          this.$message.error('报告生成失败：' + (r.errorMsg || '请查看后端日志'))
        } else {
          setTimeout(() => this.pollReport(reportId), 4000)
        }
      }).catch(() => {
        this.reportLoading = false
      })
    },
    exportReport () {
      const e = this.explain
      if (!e) return
      const f = this.form
      const lines = []
      lines.push('短视频热度归因分析报告')
      lines.push('分析参数,' + ['视频类别=' + f.videoCategory, '作者粉丝数=' + f.authorFans,
        '发布小时=' + f.publishHour, '发布星期=' + f.publishWeekday, '发布月份=' + f.publishMonth].join(' '))
      lines.push('预测热度,' + e.prediction + ',log1p,' + e.prediction_log + ',基线,' + e.base_value)
      lines.push('')
      lines.push('特征,取值,SHAP贡献(log空间)')
      ;(e.contributions || []).forEach(c => {
        lines.push([c.feature_cn, c.value, c.shap].join(','))
      })
      lines.push('')
      lines.push('运营建议')
      ;(e.advice || []).forEach((a, i) => {
        lines.push((i + 1) + ',' + String(a).replace(/,/g, '，'))
      })
      if (this.cf) {
        lines.push('')
        lines.push('反事实分析（可调整维度提升空间）')
        lines.push('维度,当前,建议,预计热度,提升幅度')
        ;(this.cf.suggestions || []).forEach(s => {
          lines.push([s.dimension, s.from, s.to, Math.round(s.heat), s.delta_pct.toFixed(1) + '%'].join(','))
        })
      }
      const blob = new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = '归因报告_' + f.videoCategory + '_' + new Date().toISOString().slice(0, 10) + '.csv'
      link.click()
      URL.revokeObjectURL(url)
      this.$message.success('归因报告已导出')
    },
    fmt (v) {
      const n = Number(v)
      return (v == null || v === '' || !Number.isFinite(n)) ? '-' : n.toFixed(3)
    },
    formatNum (v) {
      if (v == null || Number.isNaN(Number(v))) return '-'
      return Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })
    }
  }
}
</script>

<style lang="scss" scoped>
.block-card {
  margin-bottom: 16px;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;

  .section-title { margin-bottom: 0; }
  .head-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }
}

.fig-title {
  font-size: 14px;
  font-weight: 650;
  color: var(--app-text);
  margin-bottom: 10px;
}

.input-bar {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  flex-wrap: wrap;
  padding: 14px 16px;
  background: #fafbfe;
  border: 1px solid #eef0f6;
  border-radius: 12px;
  margin-bottom: 18px;

  .field {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .field-label {
    font-size: 12px;
    color: #94a3b8;
    font-weight: 600;
  }
  .field-actions {
    display: flex;
    gap: 10px;
    margin-left: auto;
  }
}

.explain-row {
  margin-bottom: 16px;
}

.contrib-chart {
  width: 100%;
  height: 300px;
}

.contrib-legend {
  display: flex;
  gap: 18px;
  align-items: center;
  font-size: 12.5px;
  color: #475569;

  .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;

    &.pos { background: #10b981; }
    &.neg { background: #ef4444; }
  }
  .muted { color: #94a3b8; }
}

.pos-text {
  color: #ef4444;
  font-weight: 600;
}
.neg-text {
  color: #409eff;
  font-weight: 600;
}

.advice-list {
  margin: 0;
  padding-left: 18px;
  color: #475569;
  font-size: 12.5px;
  line-height: 1.95;
}

.non-mutable {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #f8f9fc;
  border: 1px dashed #dfe3ee;
  font-size: 12.5px;
  color: #64748b;
}

.main-effect {
  margin-top: 16px;

  .main-effect-title {
    font-size: 13px;
    font-weight: 650;
    color: var(--app-text);
    margin-bottom: 10px;
  }
  .main-effect-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;

    .me-name {
      width: 120px;
      font-size: 12.5px;
      color: #64748b;
      flex-shrink: 0;
    }
    ::v-deep .el-progress {
      flex: 1;
    }
  }
}

.heat-val {
  color: var(--app-primary);
}

.explain-tip {
  margin-bottom: 14px;
}

/* ============ 解释可信度徽章条 ============ */
.trust-strip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  border: 1px solid #e8ecf6;
  border-left: 3px solid #6b5bd2;
  border-radius: 10px;
  background: #fff;
  padding: 10px 14px;
  margin-bottom: 16px;
}

.trust-label {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.trust-chip {
  font-size: 12px;
  color: #64748b;
  background: #f6f4ff;
  border: 1px solid #e6e2fb;
  border-radius: 6px;
  padding: 4px 9px;

  b {
    color: #4f46e5;
    font-size: 13px;
  }
}

.trust-note {
  font-size: 11.5px;
  color: #94a3b8;
  margin-left: auto;
}

/* ============ 稳定性警示 ============ */
.stability-warn {
  margin-top: 12px;
  font-size: 12.5px;
  line-height: 1.85;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 10px 12px;

  b {
    color: #b45309;
  }
}

/* 当前分析场景提示条 */
.case-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
  border-radius: 10px;
  background: rgba(99, 102, 241, .08);
  border: 1px solid rgba(99, 102, 241, .25);
  color: #4f46e5;
  font-size: 12.5px;
}
</style>
