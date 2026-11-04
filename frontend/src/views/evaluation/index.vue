<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">实验中心</div>
        <div class="page-desc">
          17 类可复现实验，按「模型性能 / 特征论证 / 不确定性 / 可解释性 / 结论可信度」五组组织。
          每个实验都有独立脚本、可一键复跑、自动记入台账，结论与图表可回看。
        </div>
      </div>
      <div class="page-head-actions">
        <el-tag type="info" effect="plain">算法引擎：Python + LightGBM + SHAP</el-tag>
        <el-badge :value="runs.length" :hidden="!runs.length" class="ledger-badge">
          <el-button size="small" @click="ledgerVisible = true">实验台账</el-button>
        </el-badge>
      </div>
    </div>

    <!-- ============ 推荐演示路径 ============ -->
    <el-card shadow="never" class="demo-card">
      <div class="demo-head">
        <span class="section-title">推荐演示路径</span>
        <span class="demo-hint">依次点 4 步，即可讲完「模型可测 → 加维度有效 → 区间可信 → 结论可审计」</span>
      </div>
      <div class="demo-steps">
        <div
          v-for="(s, i) in demoSteps"
          :key="s.mode"
          class="demo-step"
          :class="{ active: current === s.mode }"
          @click="selectModeByKey(s.mode)"
        >
          <div class="demo-idx">{{ i + 1 }}</div>
          <div class="demo-body">
            <div class="demo-name">{{ s.name }}</div>
            <div class="demo-desc">{{ s.desc }}</div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- ============ 左目录 + 右内容 ============ -->
    <div class="exp-layout">
      <el-card shadow="never" class="catalog-card">
        <div class="section-title">实验目录</div>
        <el-input
          v-model="keyword"
          size="small"
          placeholder="搜索实验名称或说明"
          prefix-icon="el-icon-search"
          clearable
          class="catalog-search"
        />
        <div v-for="g in filteredGroups" :key="g.key" class="catalog-group">
          <div class="catalog-group-title">
            <span class="catalog-group-name">{{ g.name }}</span>
            <span class="catalog-count">{{ g.items.length }}</span>
          </div>
          <div
            v-for="m in g.items"
            :key="m.mode"
            class="catalog-item"
            :class="{ active: current === m.mode }"
            @click="selectMode(m)"
          >
            <div class="catalog-item-top">
              <span class="catalog-name">{{ m.name }}</span>
              <span class="catalog-tag">{{ m.tag }}</span>
            </div>
            <p class="catalog-desc">{{ m.description }}</p>
          </div>
        </div>
        <app-empty
          v-if="!filteredGroups.length"
          compact
          title="没有匹配的实验"
          description="换个关键词，或点「全部」查看 17 类实验"
        />
      </el-card>

      <div class="exp-main">

    <!-- ============ 运行面板 ============ -->
        <el-card shadow="never" class="run-card">
          <div class="run-head">
            <div class="run-head-text">
              <div class="run-mode-name">
                {{ currentMeta.name || '实验' }}
                <el-tag size="small" effect="plain" class="run-mode-tag">{{ currentMeta.tag }}</el-tag>
              </div>
              <div class="run-mode-desc">{{ currentMeta.description }}</div>
            </div>
            <el-button type="primary" :loading="running" @click="run">开始实验</el-button>
          </div>

      <div class="run-params">
        <span class="param-label">数据集平台</span>
        <el-select v-model="form.platform" style="width: 160px">
          <el-option v-for="p in platforms" :key="p.value" :label="p.label" :value="p.value">
            <span>{{ p.label }}</span>
            <span class="platform-sub" v-if="p.desc">— {{ p.desc }}</span>
          </el-option>
        </el-select>

        <template v-if="current === 'cv'">
          <span class="param-label">交叉验证折数</span>
          <el-radio-group v-model="form.folds">
            <el-radio-button :value="3">3 折</el-radio-button>
            <el-radio-button :value="5">5 折</el-radio-button>
            <el-radio-button :value="10">10 折</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'tuning'">
          <span class="param-label">随机搜索试验次数</span>
          <el-radio-group v-model="form.trials">
            <el-radio-button :value="8">8 次</el-radio-button>
            <el-radio-button :value="12">12 次</el-radio-button>
            <el-radio-button :value="20">20 次</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'importance' || current === 'cross-platform'">
          <span class="param-label">SHAP 采样行数</span>
          <el-radio-group v-model="form.sample">
            <el-radio-button :value="1000">1,000</el-radio-button>
            <el-radio-button :value="2000">2,000</el-radio-button>
            <el-radio-button :value="4000">4,000</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'quantile' || current === 'counterfactual'">
          <span class="param-label">视频类别</span>
          <el-select v-model="form.category" style="width: 130px">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
          <span class="param-label">作者粉丝数</span>
          <el-input-number v-model="form.fans" :min="0" :step="10000" :controls="false" style="width: 130px" />
          <span class="param-label">发布小时</span>
          <el-input-number v-model="form.hour" :min="0" :max="23" style="width: 110px" />
          <span class="param-label">星期</span>
          <el-select v-model="form.weekday" style="width: 100px">
            <el-option v-for="(w, i) in weekdays" :key="i" :label="w" :value="i" />
          </el-select>
          <span class="param-label">月份</span>
          <el-select v-model="form.month" style="width: 90px">
            <el-option v-for="m in 12" :key="m" :label="m + ' 月'" :value="m" />
          </el-select>
        </template>

        <template v-else-if="current === 'growth'">
          <span class="param-label">参与建模视频数</span>
          <el-radio-group v-model="form.sample">
            <el-radio-button :value="5000">5,000</el-radio-button>
            <el-radio-button :value="20000">20,000</el-radio-button>
            <el-radio-button :value="50000">50,000</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'conformal'">
          <span class="param-label">置信水平</span>
          <el-radio-group v-model="form.alpha">
            <el-radio-button :value="0.2">80%</el-radio-button>
            <el-radio-button :value="0.1">90%</el-radio-button>
            <el-radio-button :value="0.05">95%</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'explanation-quality'">
          <span class="param-label">解释样本数</span>
          <el-radio-group v-model="form.sample">
            <el-radio-button :value="1000">1,000</el-radio-button>
            <el-radio-button :value="2000">2,000</el-radio-button>
            <el-radio-button :value="4000">4,000</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'feature-enrichment'">
          <span class="param-label">交叉验证折数</span>
          <el-radio-group v-model="form.folds">
            <el-radio-button :value="3">3 折</el-radio-button>
            <el-radio-button :value="5">5 折</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'two-stage'">
          <span class="param-label">交叉验证折数</span>
          <el-radio-group v-model="form.folds">
            <el-radio-button :value="3">3 折</el-radio-button>
            <el-radio-button :value="5">5 折</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'refutation'">
          <span class="param-label">子集重估次数</span>
          <el-radio-group v-model="form.folds">
            <el-radio-button :value="3">3 次</el-radio-button>
            <el-radio-button :value="5">5 次</el-radio-button>
          </el-radio-group>
        </template>

        <span v-else class="param-hint">该实验无需额外参数，直接点击「开始实验」即可。</span>
      </div>
    </el-card>

    <!-- ============ 结果 ============ -->
    <div v-loading="running"
         :element-loading-text="'实验运行中（已 ' + elapsedSeconds + ' 秒），正在调用 Python 算法引擎…'"
         class="result-wrap">
      <template v-if="result">
        <!-- 结论卡：先讲「所以呢」，再摆依据 -->
        <el-card shadow="never" class="conclusion-card">
          <div class="conclusion-head">
            <span class="conclusion-badge">结论</span>
            <span class="conclusion-title">{{ conclusionHeadline }}</span>
          </div>
          <div class="kv-grid">
            <div v-for="k in summary" :key="k.label" class="kv-item">
              <div class="kv-label">{{ k.label }}</div>
              <div class="kv-value" :class="k.tone">{{ k.value }}</div>
            </div>
          </div>
          <ul v-if="notes.length" class="note-list">
            <li v-for="(n, i) in notes" :key="i">{{ n }}</li>
          </ul>
          <div class="conclusion-foot">
            <span>实验：{{ currentMeta.name }}</span>
            <span v-if="lastRun">耗时 {{ (lastRun.elapsedMs / 1000).toFixed(1) }}s</span>
            <span v-if="lastRun && lastRun.traceId" class="foot-trace">traceId {{ lastRun.traceId }}</span>
            <span v-if="lastRun && lastRun.finishedAt" class="foot-time">{{ lastRun.finishedAt }}</span>
          </div>
        </el-card>

        <!-- 明细表 -->
        <el-card v-for="t in tables" :key="t.title" shadow="never" class="block-card">
          <div class="section-title">{{ t.title }}</div>
          <el-table :data="t.rows" size="small" stripe>
            <el-table-column
              v-for="c in t.columns"
              :key="c.prop"
              :prop="c.prop"
              :label="c.label"
              :width="c.width"
              :min-width="c.minWidth"
            >
              <template v-if="c.format" #default="{ row }">{{ c.format(row) }}</template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 图 -->
        <el-card v-if="figureSrc" shadow="never" class="block-card">
          <div class="section-title">实验图表</div>
          <el-image
            :src="figureSrc"
            :preview-src-list="[figureSrc]"
            fit="contain"
            class="fig-img-lg"
            lazy
          />
        </el-card>
      </template>

      <app-empty
        v-else
        title="还没有运行实验"
        description="从左侧实验目录选一个实验，点击「开始实验」即可得到「一句话结论 + 关键指标 + 图表 + 明细表」"
      >
        <el-button type="primary" plain size="small" @click="runRecommended">
          按推荐路径跑第一个
        </el-button>
      </app-empty>
        </div>
      </div>
    </div>

    <!-- ============ 实验台账抽屉 ============ -->
    <el-drawer :visible.sync="ledgerVisible" title="实验台账（自动记账，可回看与对比）" size="64%" append-to-body>
      <div class="ledger-toolbar">
        <span class="muted">
          共 {{ runs.length }} 条记录 · 勾选两条可对比参数与耗时
        </span>
        <div>
          <el-button size="small" :loading="loadingRuns" @click="loadRuns">刷新</el-button>
          <el-button size="small" type="primary" plain :disabled="compareRows.length !== 2" @click="compareMode = true">
            对比选中（{{ compareRows.length }}/2）
          </el-button>
        </div>
      </div>

      <el-table
        :data="runs"
        size="small"
        v-loading="loadingRuns"
        @selection-change="rows => compareRows = rows.slice(0, 2)"
      >
        <el-table-column type="selection" width="42" />
        <el-table-column prop="finishedAt" label="完成时间" width="165" />
        <el-table-column prop="mode" label="实验模式" width="170" />
        <el-table-column label="状态" width="86">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'DONE' ? 'success' : 'danger'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="platform" label="平台" width="90" />
        <el-table-column label="耗时" width="90">
          <template #default="{ row }">{{ row.elapsedMs ? (row.elapsedMs / 1000).toFixed(1) + 's' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="traceId" label="traceId" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="loadRun(row)">回看结果</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <app-empty
            compact
            title="还没有实验记录"
            description="跑一次实验就会自动记账：参数、耗时、traceId 与结果都会写入台账，可随时回看"
          />
        </template>
      </el-table>

      <el-dialog title="实验对比" :visible.sync="compareMode" width="640px" append-to-body>
        <el-table v-if="compareRows.length === 2" :data="compareView" size="small" border>
          <el-table-column prop="field" label="对比项" width="150" />
          <el-table-column prop="a" label="实验 A" min-width="180" />
          <el-table-column prop="b" label="实验 B" min-width="180" />
          <el-table-column prop="diff" label="差异" width="110" />
        </el-table>
      </el-dialog>
    </el-drawer>
  </div>
</template>

<script>
import evaluationApi from '@/api/evaluation'
import AppSkeleton from '@/components/AppSkeleton'
import AppEmpty from '@/components/AppEmpty'
import { buildSummary } from './renderers/buildSummary'
import { buildNotes } from './renderers/buildNotes'
import { buildTables } from './renderers/buildTables'

const MODE_FIGURE_GROUP = {
  counterfactual: 'attr',
  'cross-platform': 'attr'
}

/** 实验分组：把 17 类实验按「论证主题」归类，避免在页面上平铺成一长串 */
const MODE_GROUPS = [
  { key: 'perf', name: '模型性能与可靠性', modes: ['cv', 'tuning', 'learning-curve', 'residual', 'ablation', 'drift', 'target-compare'] },
  { key: 'feature', name: '特征体系论证', modes: ['importance', 'feature-enrichment', 'cross-platform'] },
  { key: 'interval', name: '不确定性与区间', modes: ['quantile', 'conformal'] },
  { key: 'explain', name: '可解释性与交互', modes: ['interaction', 'explanation-quality'] },
  { key: 'trust', name: '结论可信度与决策', modes: ['counterfactual', 'refutation', 'growth', 'two-stage'] }
]

/** 推荐演示路径：4 步讲完核心叙事 */
const DEMO_STEPS = [
  { mode: 'cv', name: '模型可测', desc: '5 折交叉验证给出基线 R² 与方差' },
  { mode: 'feature-enrichment', name: '加维度有效', desc: '加内容/文本特征 vs 加样本的增益对照' },
  { mode: 'conformal', name: '区间可信', desc: '保形预测给出有限样本覆盖保证' },
  { mode: 'refutation', name: '结论可审计', desc: '安慰剂 / 子集重估 / 跨模型三重检验' }
]

export default {
  name: 'EvaluationIndex',
  components: { AppSkeleton, AppEmpty },
  data () {
    return {
      modes: [],
      current: 'cv',
      running: false,
      result: null,
      // 实验台账（data/logs/experiment_runs.jsonl）
      runs: [],
      loadingRuns: false,
      // 台账抽屉与对比
      ledgerVisible: false,
      compareRows: [],
      compareMode: false,
      // 实验目录搜索
      keyword: '',
      // 异步任务轮询：已耗时秒数 + 轮询定时器句柄
      elapsedSeconds: 0,
      pollTimer: null,
      categories: ['搞笑', '美食', '音乐', '美妆', '穿搭', '舞蹈', '旅行', '宠物', '影视', '健身', '情感', '游戏', '生活', '知识'],
      weekdays: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      platforms: [
        { value: 'douyin',   label: '🎵 抖音',       desc: '45K · 14 类 · 原始预切分' },
        { value: 'youtube',  label: '▶️ YouTube',   desc: '450K · 15 类 · 3 国趋势榜' },
        { value: 'tiktok',   label: '🎶 TikTok',    desc: '210K · 9 类 · 30 天累计' },
        { value: 'bilibili', label: '📺 哔哩哔哩',  desc: '1.6K · 97 类 · 热门排行' }
      ],
      form: {
        platform: 'douyin',
        folds: 5,
        trials: 12,
        sample: 2000,
        alpha: 0.1,
        category: '美食',
        fans: 50000,
        hour: 3,
        weekday: 2,
        month: 9
      }
    }
  },
  computed: {
    currentMeta () {
      return this.modes.find(m => m.mode === this.current) || {}
    },
    figureSrc () {
      const fig = this.result && this.result.figure
      if (!fig) return ''
      const group = MODE_FIGURE_GROUP[this.current] === 'attr' ? '/attribution/' : '/evaluation/'
      return group + fig + '?t=' + Date.now()
    },
    /* ---- 实验目录（按主题分组 + 搜索） ---- */
    modeGroups () {
      const groups = MODE_GROUPS.map(g => ({
        key: g.key,
        name: g.name,
        items: this.modes.filter(m => g.modes.includes(m.mode))
      })).filter(g => g.items.length)
      const rest = this.modes.filter(m => !MODE_GROUPS.some(g => g.modes.includes(m.mode)))
      if (rest.length) groups.push({ key: 'other', name: '其它实验', items: rest })
      return groups
    },
    filteredGroups () {
      const kw = (this.keyword || '').trim().toLowerCase()
      if (!kw) return this.modeGroups
      return this.modeGroups
        .map(g => ({
          key: g.key,
          name: g.name,
          items: g.items.filter(m =>
            (m.name || '').toLowerCase().includes(kw) ||
            (m.description || '').toLowerCase().includes(kw) ||
            (m.tag || '').toLowerCase().includes(kw))
        }))
        .filter(g => g.items.length)
    },
    demoSteps () {
      return DEMO_STEPS
    },
    /* ---- 结论卡：一句话「所以呢」 ---- */
    lastRun () {
      return this.runs && this.runs.length ? this.runs[0] : null
    },
    conclusionHeadline () {
      const best = this.summary.find(k => k.tone === 'tone-best') || this.summary[0]
      if (!best) return (this.currentMeta.name || '实验') + ' 已完成，结果见下方图表'
      return best.label + '：' + best.value
    },
    /* ---- 台账对比视图 ---- */
    compareView () {
      if (!this.compareRows || this.compareRows.length !== 2) return []
      const a = this.compareRows[0]
      const b = this.compareRows[1]
      const fmt = v => (v == null || v === '' ? '-' : String(v))
      const rows = [
        { field: '实验模式', a: fmt(a.mode), b: fmt(b.mode), diff: a.mode === b.mode ? '相同' : '不同' },
        { field: '状态', a: fmt(a.status), b: fmt(b.status), diff: a.status === b.status ? '相同' : '不同' },
        { field: '平台', a: fmt(a.platform), b: fmt(b.platform), diff: a.platform === b.platform ? '相同' : '不同' },
        { field: '耗时', a: fmt(a.elapsedMs), b: fmt(b.elapsedMs), diff: '—' },
        { field: 'traceId', a: fmt(a.traceId), b: fmt(b.traceId), diff: '—' }
      ]
      const pa = a.params || {}
      const pb = b.params || {}
      const keys = Array.from(new Set([...Object.keys(pa), ...Object.keys(pb)]))
        .filter(k => pa[k] != null || pb[k] != null)
        .sort()
      keys.forEach(k => {
        const va = fmt(pa[k])
        const vb = fmt(pb[k])
        rows.push({ field: '参数 ' + k, a: va, b: vb, diff: va === vb ? '相同' : '不同' })
      })
      return rows
    },
    /* ---- 关键指标（按模式抽取） ---- */
    summary () {
      return buildSummary(this.current, this.result)
    },
    notes () {
      return buildNotes(this.current, this.result)
    },
    /* ---- 明细表（按模式抽取） ---- */
    tables () {
      return buildTables(this.current, this.result)
    },
  },
  created () {
    this.loadModes()
    this.loadRuns()
  },
  methods: {
    loadModes () {
      evaluationApi.modes().then(re => {
        this.modes = re.response || []
        if (this.modes.length && !this.modes.some(m => m.mode === this.current)) {
          this.current = this.modes[0].mode
        }
      }).catch(() => {})
    },
    loadRuns () {
      this.loadingRuns = true
      evaluationApi.runs(20).then(re => {
        this.runs = re.response || []
        this.loadingRuns = false
      }).catch(() => { this.loadingRuns = false })
    },
    loadRun (row) {
      if (!row) return
      if (row.mode && this.modes.some(m => m.mode === row.mode)) {
        this.current = row.mode
      }
      if (row.result) {
        this.result = row.result
        this.ledgerVisible = false
        this.$message.success('已载入 ' + row.finishedAt + ' 的实验结果')
      } else {
        this.$message.warning('该记录（' + row.status + '）没有可用结果')
      }
    },
    selectModeByKey (mode) {
      const m = this.modes.find(x => x.mode === mode)
      if (m) this.selectMode(m)
    },
    /** 空态里的「按推荐路径跑第一个」：选中第 1 步并直接开跑 */
    runRecommended () {
      const first = DEMO_STEPS[0]
      if (!first) return
      this.selectModeByKey(first.mode)
      this.run()
    },
    selectMode (m) {
      this.current = m.mode
      this.result = null
      // sample 在「特征重要性/跨平台」与「增长曲线」间共用，切换时对齐到合法取值，避免单选项落空
      if (m.mode === 'growth' && this.form.sample < 5000) {
        this.form.sample = 20000
      } else if ((m.mode === 'importance' || m.mode === 'cross-platform')
        && ![1000, 2000, 4000].includes(this.form.sample)) {
        this.form.sample = 2000
      }
    },
    run () {
      this.running = true
      this.result = null
      this.elapsedSeconds = 0
      this.stopPolling()
      const payload = { mode: this.current, ...this.form }
      // 异步提交：后端立即返回 taskId，实验在线程池跑，避免前端长连接干等
      evaluationApi.submit(payload).then(re => {
        const taskId = (re.response || {}).taskId
        if (!taskId) {
          this.running = false
          this.$message.error('实验提交失败：未返回任务 ID')
          return
        }
        this.pollTask(taskId)
      }).catch(() => {
        this.running = false
        this.$message.error('实验提交失败，请查看后端日志')
      })
    },
    pollTask (taskId) {
      const startedAt = Date.now()
      this.pollTimer = setInterval(() => {
        this.elapsedSeconds = Math.floor((Date.now() - startedAt) / 1000)
        evaluationApi.task(taskId).then(re => {
          const task = re.response || {}
          if (task.status === 'DONE') {
            this.stopPolling()
            this.running = false
            this.result = task.result || null
            const cost = task.elapsedMs
              ? (task.elapsedMs / 1000).toFixed(1) + ' 秒'
              : this.elapsedSeconds + ' 秒'
            this.$message.success('实验完成，耗时 ' + cost)
            this.loadRuns()
          } else if (task.status === 'FAILED') {
            this.stopPolling()
            this.running = false
            this.$message.error('实验失败：' + (task.error || '未知错误'))
          }
        }).catch(() => {
          // 单次轮询失败不打断整体流程，下一轮继续
        })
      }, 2000)
    },
    stopPolling () {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    }
  },
  beforeDestroy () {
    this.stopPolling()
  }
}
</script>

<style lang="scss" scoped>
.exp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(268px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.exp-card {
  background: #fff;
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  box-shadow: var(--app-shadow-1);
  padding: 16px 18px;
  cursor: pointer;
  transition: all .2s ease;

  &:hover {
    box-shadow: var(--app-shadow-2);
    transform: translateY(-2px);
  }

  &.active {
    border-color: #b9bcfb;
    background: linear-gradient(160deg, #f7f8ff 0%, #fdf8ff 100%);
    box-shadow: 0 8px 26px rgba(99, 102, 241, .18);
  }

  .exp-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
  }

  .exp-name {
    font-size: 14.5px;
    font-weight: 700;
    color: #1e293b;
  }

  .exp-tag {
    color: #6b5bd2;
    border-color: #ddd8fb;
    background: #f6f4ff;
  }

  .exp-desc {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.75;
    color: #64748b;
  }
}

.history-card {
  margin-bottom: 16px;

  .run-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }
}

.run-card {
  margin-bottom: 16px;

  .run-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;

    .section-title {
      margin-bottom: 0;
    }
  }

  .run-params {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .param-label {
    font-size: 13px;
    color: #64748b;
    font-weight: 600;
  }

  .param-hint {
    font-size: 13px;
    color: #94a3b8;
  }
}

.platform-sub {
  color: #94a3b8;
  font-size: 12px;
  margin-left: 4px;
}

.result-wrap {
  min-height: 180px;
}

.block-card {
  margin-bottom: 16px;
}

.kv-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 12px;
}

.kv-item {
  background: #fafbfe;
  border: 1px solid #eef0f6;
  border-radius: 12px;
  padding: 13px 16px;

  .kv-label {
    font-size: 12px;
    color: #94a3b8;
  }

  .kv-value {
    font-size: 17px;
    font-weight: 750;
    color: #1e293b;
    margin-top: 5px;
    font-variant-numeric: tabular-nums;

    &.tone-best {
      color: #4f46e5;
    }
    &.tone-good {
      color: #10b981;
    }
    &.tone-flat {
      color: #94a3b8;
    }
  }
}

.note-list {
  margin: 14px 0 0;
  padding-left: 18px;

  li {
    font-size: 12.5px;
    line-height: 1.85;
    color: #64748b;
  }
}

/* ==================== 实验中心：布局与目录 ==================== */
.exp-layout {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.exp-main {
  flex: 1;
  min-width: 0;
}

.catalog-card {
  width: 268px;
  flex: 0 0 268px;
  position: sticky;
  top: 12px;

  .section-title {
    margin-bottom: 10px;
  }
}

.catalog-search {
  margin-bottom: 12px;
}

.catalog-group {
  margin-bottom: 14px;

  &:last-child {
    margin-bottom: 0;
  }
}

.catalog-group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2px 6px;
  font-size: 12px;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: .04em;
}

.catalog-count {
  font-size: 11px;
  font-weight: 600;
  color: #a5b4fc;
  background: #f1f0ff;
  border-radius: 8px;
  padding: 1px 7px;
}

.catalog-item {
  border: 1px solid #e8ecf6;
  border-radius: 8px;
  padding: 9px 10px;
  margin-bottom: 7px;
  cursor: pointer;
  transition: all .18s ease;
  background: #fff;

  &:hover {
    border-color: #c7c9fb;
    background: #fafaff;
  }

  &.active {
    border-color: #b9bcfb;
    background: linear-gradient(160deg, #f7f8ff 0%, #fdf8ff 100%);
    box-shadow: 0 6px 18px rgba(99, 102, 241, .16);
  }
}

.catalog-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 4px;
}

.catalog-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.catalog-tag {
  flex: 0 0 auto;
  font-size: 10.5px;
  color: #6b5bd2;
  background: #f6f4ff;
  border-radius: 4px;
  padding: 1px 6px;
}

.catalog-desc {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.65;
  color: #7c8798;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ==================== 推荐演示路径 ==================== */
.demo-card {
  margin-bottom: 16px;
}

.demo-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 12px;

  .section-title {
    margin-bottom: 0;
  }
}

.demo-hint {
  font-size: 12px;
  color: #94a3b8;
}

.demo-steps {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.demo-step {
  flex: 1 1 190px;
  min-width: 190px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  border: 1px solid #e8ecf6;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all .18s ease;
  background: #fff;

  &:hover {
    border-color: #c7c9fb;
    transform: translateY(-1px);
  }

  &.active {
    border-color: #b9bcfb;
    background: linear-gradient(160deg, #f7f8ff 0%, #fdf8ff 100%);
    box-shadow: 0 8px 22px rgba(99, 102, 241, .18);
  }
}

.demo-idx {
  flex: 0 0 22px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #eef0ff;
  color: #6b5bd2;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.demo-step.active .demo-idx {
  background: #6b5bd2;
  color: #fff;
}

.demo-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 2px;
}

.demo-desc {
  font-size: 11.5px;
  line-height: 1.6;
  color: #7c8798;
}

/* ==================== 结论卡 ==================== */
.conclusion-card {
  border-left: 3px solid #6b5bd2;
}

.conclusion-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 14px;
}

.conclusion-badge {
  flex: 0 0 auto;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: #6b5bd2;
  border-radius: 4px;
  padding: 2px 8px;
  letter-spacing: .08em;
}

.conclusion-title {
  font-size: 16px;
  font-weight: 700;
  line-height: 1.5;
  color: #1e293b;
}

.conclusion-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px dashed #e8ecf6;
  font-size: 11.5px;
  color: #94a3b8;
}

.foot-trace {
  font-family: Consolas, Monaco, monospace;
}

.foot-time {
  margin-left: auto;
}

/* ==================== 运行面板头部 ==================== */
.run-head-text {
  min-width: 0;
}

.run-mode-name {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 4px;
}

.run-mode-tag {
  margin-left: 6px;
  vertical-align: 2px;
}

.run-mode-desc {
  font-size: 12px;
  line-height: 1.7;
  color: #64748b;
  max-width: 720px;
}

/* ==================== 台账抽屉 ==================== */
.ledger-badge {
  margin-left: 10px;
}

.ledger-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
</style>
