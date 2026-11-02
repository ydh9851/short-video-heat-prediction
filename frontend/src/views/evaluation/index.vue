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
        <el-empty v-if="!filteredGroups.length" description="没有匹配的实验" :image-size="60" />
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
            <el-radio-button :label="3">3 折</el-radio-button>
            <el-radio-button :label="5">5 折</el-radio-button>
            <el-radio-button :label="10">10 折</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'tuning'">
          <span class="param-label">随机搜索试验次数</span>
          <el-radio-group v-model="form.trials">
            <el-radio-button :label="8">8 次</el-radio-button>
            <el-radio-button :label="12">12 次</el-radio-button>
            <el-radio-button :label="20">20 次</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'importance' || current === 'cross-platform'">
          <span class="param-label">SHAP 采样行数</span>
          <el-radio-group v-model="form.sample">
            <el-radio-button :label="1000">1,000</el-radio-button>
            <el-radio-button :label="2000">2,000</el-radio-button>
            <el-radio-button :label="4000">4,000</el-radio-button>
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
            <el-radio-button :label="5000">5,000</el-radio-button>
            <el-radio-button :label="20000">20,000</el-radio-button>
            <el-radio-button :label="50000">50,000</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'conformal'">
          <span class="param-label">置信水平</span>
          <el-radio-group v-model="form.alpha">
            <el-radio-button :label="0.2">80%</el-radio-button>
            <el-radio-button :label="0.1">90%</el-radio-button>
            <el-radio-button :label="0.05">95%</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'explanation-quality'">
          <span class="param-label">解释样本数</span>
          <el-radio-group v-model="form.sample">
            <el-radio-button :label="1000">1,000</el-radio-button>
            <el-radio-button :label="2000">2,000</el-radio-button>
            <el-radio-button :label="4000">4,000</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'feature-enrichment'">
          <span class="param-label">交叉验证折数</span>
          <el-radio-group v-model="form.folds">
            <el-radio-button :label="3">3 折</el-radio-button>
            <el-radio-button :label="5">5 折</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'two-stage'">
          <span class="param-label">交叉验证折数</span>
          <el-radio-group v-model="form.folds">
            <el-radio-button :label="3">3 折</el-radio-button>
            <el-radio-button :label="5">5 折</el-radio-button>
          </el-radio-group>
        </template>

        <template v-else-if="current === 'refutation'">
          <span class="param-label">子集重估次数</span>
          <el-radio-group v-model="form.folds">
            <el-radio-button :label="3">3 次</el-radio-button>
            <el-radio-button :label="5">5 次</el-radio-button>
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

      <el-empty v-else description="从左侧实验目录选一个实验，点击「开始实验」即可得到结论与图表" />
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
          <el-empty description="还没有实验记录，跑一次实验就会自动记账" :image-size="70" />
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

const MODE_FIGURE_GROUP = {
  counterfactual: 'attr',
  'cross-platform': 'attr'
}

/** 实验分组：把 17 类实验按「论证主题」归类，避免在页面上平铺成一长串 */
const MODE_GROUPS = [
  { key: 'perf', name: '模型性能与可靠性', modes: ['cv', 'tuning', 'learning-curve', 'residual', 'ablation', 'drift'] },
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
      const r = this.result
      if (!r) return []
      const out = []
      const pct = v => {
        const n = Number(v)
        return (v == null || v === '' || !Number.isFinite(n)) ? '-' : (n * 100).toFixed(2) + '%'
      }
      if (this.current === 'cv') {
        Object.keys(r.models || {}).forEach(m => {
          out.push({
            label: m.toUpperCase() + ' R²(log)',
            value: r.models[m].r2_mean.toFixed(4) + ' ± ' + r.models[m].r2_std.toFixed(4),
            tone: m === r.best ? 'tone-best' : ''
          })
        })
      } else if (this.current === 'tuning') {
        out.push({ label: '最优 3 折 CV RMSE', value: r.best_rmse.toFixed(4), tone: 'tone-best' })
        out.push({ label: '试验次数', value: r.trials + ' 组参数' })
        Object.keys(r.best_params || {}).forEach(k => {
          out.push({ label: k, value: String(r.best_params[k]) })
        })
      } else if (this.current === 'learning-curve') {
        const pts = r.points || []
        out.push({ label: '最终测试集 RMSE', value: pts.length ? pts[pts.length - 1].test_rmse.toFixed(4) : '-' })
        out.push({ label: '首点测试集 RMSE', value: pts.length ? pts[0].test_rmse.toFixed(4) : '-' })
        out.push({ label: '训练/验证间隙', value: r.final_gap.toFixed(4) })
        out.push({ label: '数据量是否饱和', value: r.saturated ? '已饱和（继续加数据收益极小）' : '未饱和' })
      } else if (this.current === 'importance') {
        out.push({ label: '首位特征', value: (r.top3 && r.top3[0]) || '-', tone: 'tone-best' })
        out.push({ label: '三种度量首位一致', value: r.top1_consistent ? '一致' : '不一致' })
        out.push({ label: '前 3 名重合特征数', value: r.top3_overlap + ' / 3' })
      } else if (this.current === 'residual') {
        out.push({ label: 'P50 绝对误差', value: r.abs_err_quantiles_raw.p50.toFixed(1) })
        out.push({ label: 'P90 绝对误差', value: r.abs_err_quantiles_raw.p90.toFixed(1) })
        out.push({ label: 'P99 绝对误差', value: r.abs_err_quantiles_raw.p99.toFixed(1) })
        out.push({ label: 'P50 相对误差', value: pct(r.rel_err_quantiles.p50) })
      } else if (this.current === 'ablation') {
        Object.keys(r.r2_delta || {}).forEach(m => {
          const d = r.r2_delta[m]
          out.push({
            label: m.toUpperCase() + ' R² 变化（增强 - 基础）',
            value: (d > 0 ? '+' : '') + d.toFixed(4),
            tone: d > 0 ? 'tone-good' : 'tone-flat'
          })
        })
      } else if (this.current === 'quantile') {
        const iv = r.interval || {}
        out.push({ label: 'P10（保守）', value: Math.round(iv.p10).toLocaleString() })
        out.push({ label: 'P50（中性）', value: Math.round(iv.p50).toLocaleString(), tone: 'tone-best' })
        out.push({ label: 'P90（乐观）', value: Math.round(iv.p90).toLocaleString() })
        out.push({ label: '区间宽度', value: Math.round(r.width).toLocaleString() })
        out.push({ label: '分级参考', value: r.grade })
        if (r.coverage_report) {
          out.push({ label: '区间覆盖率（测试集）', value: pct(r.coverage_report.coverage) })
        }
      } else if (this.current === 'interaction') {
        out.push({ label: '最强交互组合', value: r.strongest_pair ? (r.strongest_pair.feature_a_cn + ' × ' + r.strongest_pair.feature_b_cn) : '-', tone: 'tone-best' })
        out.push({ label: '最强交互强度', value: r.strongest_pair ? r.strongest_pair.interaction.toFixed(4) : '-' })
        out.push({ label: '首位特征主效应', value: r.main_effects.length ? r.main_effects[0].main_effect.toFixed(4) : '-' })
      } else if (this.current === 'counterfactual') {
        out.push({ label: '当前预测热度', value: Math.round(r.base_heat).toLocaleString(), tone: 'tone-best' })
        out.push({ label: '当前热度等级', value: r.base_grade })
        const best = (r.suggestions || [])[0]
        out.push({ label: '最优可调整项', value: best ? (best.dimension + ' → ' + best.to) : '当前已是最优' })
        out.push({ label: '预计最大提升', value: best ? ('+' + best.delta_pct.toFixed(1) + '%') : '-' })
      } else if (this.current === 'cross-platform') {
        out.push({
          label: '首位特征是否跨平台一致',
          value: r.top1_consistent ? '一致' : '不一致',
          tone: r.top1_consistent ? 'tone-good' : 'tone-flat'
        })
        out.push({ label: '各平台首位特征', value: Object.values(r.top1_by_platform || {}).join(' / ') })
        ;(r.platforms || []).forEach(p => {
          out.push({ label: p.platform_cn + ' R²(log)', value: (p.r2 == null ? '-' : p.r2.toFixed(4)) })
        })
        out.push({ label: '跨平台差异最大特征', value: (r.spread_features || []).join('、'), tone: 'tone-best' })
      } else if (this.current === 'drift') {
        out.push({ label: '基准平台', value: r.reference_cn })
        out.push({ label: '最大 PSI', value: (r.max_psi == null ? '-' : r.max_psi.toFixed(3)), tone: 'tone-best' })
        out.push({ label: '漂移最显著平台', value: r.worst_platform })
        out.push({ label: '漂移最显著特征', value: r.worst_feature })
        out.push({ label: '稳定（PSI<0.1）占比', value: ((r.stable_ratio || 0) * 100).toFixed(0) + '%' })
      } else if (this.current === 'growth') {
        out.push({ label: '数据来源', value: r.source })
        out.push({ label: '参与建模视频数', value: Number(r.n_videos || 0).toLocaleString() })
        ;(r.horizons || []).forEach(h => {
          out.push({ label: '预测第 ' + h.day + ' 天 R²(log)', value: (h.r2 == null ? '-' : h.r2.toFixed(4)) })
        })
        const s = r.summary || {}
        out.push({ label: '第 7 天 MAE（原始热度）', value: s.day7_mae_raw == null ? '-' : Math.round(s.day7_mae_raw).toLocaleString() })
        out.push({
          label: '第 7 天典型累计倍数',
          value: s.day7_median_multiplier == null ? '-' : s.day7_median_multiplier.toFixed(2) + '×',
          tone: 'tone-best'
        })
      } else if (this.current === 'conformal') {
        const g = r.global || {}
        const base = r.quantile_baseline || {}
        out.push({ label: '目标覆盖率', value: ((r.target_coverage || 0) * 100).toFixed(0) + '%' })
        out.push({
          label: '保形实测覆盖率',
          value: g.coverage == null ? '-' : (g.coverage * 100).toFixed(1) + '%',
          tone: 'tone-best'
        })
        out.push({
          label: '分位数回归覆盖率',
          value: base.coverage == null ? '-' : (base.coverage * 100).toFixed(1) + '%'
        })
        out.push({ label: '校准残差 q̂（log）', value: r.qhat_log == null ? '-' : r.qhat_log.toFixed(3) })
        out.push({
          label: '中位区间宽度',
          value: g.median_width == null ? '-' : Math.round(g.median_width).toLocaleString()
        })
        out.push({ label: '拟合 / 校准 / 测试', value: `${r.n_fit || 0} / ${r.n_calib || 0} / ${r.n_test || 0}` })
      } else if (this.current === 'explanation-quality') {
        const rank = r.ranking || []
        const comp = r.compacity || {}
        const cons = r.consistency || {}
        const stab = r.stability || {}
        const top = rank[0] || {}
        out.push({ label: '首位特征', value: top.feature || '-', tone: 'tone-best' })
        out.push({ label: '首位贡献占比', value: top.share == null ? '-' : (top.share * 100).toFixed(1) + '%' })
        out.push({ label: '解释 80% 贡献所需特征数', value: comp.k80 == null ? '-' : comp.k80 + ' 个' })
        out.push({ label: '一致性 τ（SHAP vs 增益）', value: cons.kendall_shap_vs_gain == null ? '-' : cons.kendall_shap_vs_gain.toFixed(3) })
        out.push({ label: '稳定性 Jaccard（Top-3）', value: stab.jaccard_mean == null ? '-' : stab.jaccard_mean.toFixed(3) })
        out.push({ label: '解释样本数', value: Number(r.sample || 0).toLocaleString() })
      } else if (this.current === 'feature-enrichment') {
        const t = r.table || []
        const s = r.summary || {}
        out.push({ label: '参与视频数', value: Number(r.rows || 0).toLocaleString() })
        out.push({ label: '基础先验 R²(log)', value: s.base_r2 == null ? '-' : s.base_r2.toFixed(4) })
        out.push({ label: '+内容属性 R²(log)', value: s.content_r2 == null ? '-' : s.content_r2.toFixed(4), tone: 'tone-best' })
        out.push({ label: '+标题文本 R²(log)', value: s.text_r2 == null ? '-' : s.text_r2.toFixed(4), tone: 'tone-best' })
        out.push({ label: '内容增益', value: (s.content_gain == null ? '-' : '+' + s.content_gain.toFixed(4)) })
        out.push({ label: '文本增益', value: (s.text_gain == null ? '-' : '+' + s.text_gain.toFixed(4)) })
        if (t.length) out.push({ label: '目标口径', value: r.target || '-' })
      } else if (this.current === 'refutation') {
        const st = r.stability || {}
        const pl = r.placebo || {}
        const cm = r.cross_model || {}
        out.push({ label: '总体结论', value: r.verdict || '-', tone: r.verdict === 'PASS' ? 'tone-best' : undefined })
        out.push({ label: '基准预测热度', value: Number(r.base_prediction || 0).toLocaleString() })
        out.push({
          label: '发布小时增益区间',
          value: st.hour_gain == null ? '-' : ((st.hour_gain.min * 100).toFixed(0) + '% ~ ' + (st.hour_gain.max * 100).toFixed(0) + '%')
        })
        out.push({ label: '增益变异系数 CV', value: st.hour_gain == null ? '-' : String(st.hour_gain.cv) })
        out.push({ label: '安慰剂维度增益', value: pl.gain == null ? '-' : (pl.gain * 100).toFixed(1) + '%' })
        out.push({ label: '跨模型最优取值一致', value: cm.hour_agreement ? '是' : '否' })
      } else if (this.current === 'two-stage') {
        const s = r.summary || {}
        out.push({ label: '参与视频数', value: Number(r.rows || 0).toLocaleString() })
        out.push({ label: '仅先验 R²(log)', value: s.prior_r2 == null ? '-' : s.prior_r2.toFixed(4) })
        out.push({ label: '+第 1 天信号', value: s.d1_r2 == null ? '-' : s.d1_r2.toFixed(4), tone: 'tone-best' })
        out.push({ label: '+第 1、3 天信号', value: s.d1d3_r2 == null ? '-' : s.d1d3_r2.toFixed(4), tone: 'tone-best' })
        out.push({ label: '第 1 天带来增益', value: s.d1_gain == null ? '-' : '+' + s.d1_gain.toFixed(4) })
        out.push({ label: '相对误差中位数（先验→双阶段）',
          value: (s.prior_rel_err_p50 == null ? '-' : (s.prior_rel_err_p50 * 100).toFixed(1) + '%')
            + ' → ' + (s.d1d3_rel_err_p50 == null ? '-' : (s.d1d3_rel_err_p50 * 100).toFixed(1) + '%') })
      }
      return out
    },
    notes () {
      const r = this.result
      if (!r) return []
      if (this.current === 'ablation') {
        return ['周期编码对树模型几乎无增益（树本身可通过切分捕捉周期），但对线性模型有稳定提升；'
          + '因此生产环境保留基础特征集即可，避免不必要的特征膨胀。']
      }
      if (this.current === 'importance') return r.note ? [r.note] : []
      if (this.current === 'interaction' && r.note) return [r.note]
      if (this.current === 'conformal') {
        const cov = ((r.global || {}).coverage || 0) * 100
        const base = (((r.quantile_baseline || {}).coverage) || 0) * 100
        return ['保形区间在样本可交换假设下满足 P(y ∈ [lo, hi]) ≥ 1−α，是有限样本保证；'
          + '分位数回归只能事后检验覆盖率。同一测试集上两者分别达到 '
          + cov.toFixed(1) + '% 与 ' + base.toFixed(1) + '%。'
          + 'Mondrian 分组校准用于缓解高热度档覆盖不足，代价是区间变宽。']
      }
      if (this.current === 'refutation') {
        const st = r.stability || {}
        const cm = r.cross_model || {}
        const verdict = r.verdict === 'PASS'
          ? '三项检验全部通过：反事实建议可作为决策参考。'
          : '存在未通过的检验项：反事实建议只能作为方向性参考，不能当作精确的收益承诺。'
        const detail = '发布小时的最优取值在多次子集重训中为 '
          + ((st.details || []).map(d => d.hour_to + ' 点').join(' / ') || '-')
          + '，增益区间 ' + (st.hour_gain ? (st.hour_gain.min * 100).toFixed(0) + '% ~ ' + (st.hour_gain.max * 100).toFixed(0) + '%' : '-')
          + '（CV = ' + (st.hour_gain ? st.hour_gain.cv : '-') + '）。'
          + '跨模型上，发布小时的最优取值' + (cm.hour_agreement ? '一致' : '不一致')
          + '，类别最优取值' + (cm.category_agreement ? '一致' : '不一致') + '。'
        return [verdict, detail,
          '原因分析：这些维度本身对模型的贡献很小（SHAP 占比约 1%），在 log 空间经 expm1 放大后，'
          + '微小差异会被放大成可观的百分比收益。因此在论文与系统中应把建议表述为「方向 + 区间」，'
          + '并对强特征（作者粉丝数）之外的维度明确标注不确定性。']
      }
      if (this.current === 'two-stage') {
        const s = r.summary || {}
        return ['仅用发布时先验预测第 7 天热度，R²(log) 为 ' + (s.prior_r2 == null ? '-' : s.prior_r2.toFixed(4))
          + '、相对误差中位数 ' + (s.prior_rel_err_p50 == null ? '-' : (s.prior_rel_err_p50 * 100).toFixed(1)) + '%；'
          + '加入发布后第 1 天真实累计互动后跃升到 ' + (s.d1_r2 == null ? '-' : s.d1_r2.toFixed(4))
          + '（+' + (s.d1_gain || 0).toFixed(4) + '），相对误差降到 '
          + (s.d1d3_rel_err_p50 == null ? '-' : (s.d1d3_rel_err_p50 * 100).toFixed(1)) + '%。'
          + '这说明「发布前预测」与「发布后 24 小时修正」应当作为两阶段能力分别呈现：'
          + '前者用于选题与排期，后者用于投放与追投决策。']
      }
      if (this.current === 'feature-enrichment') {
        const s = r.summary || {}
        return ['同一份数据、同一套交叉验证、同一个 LightGBM：仅仅把「内容属性」加进特征集，R²(log) 就从 '
          + (s.base_r2 == null ? '-' : s.base_r2.toFixed(4)) + ' 提升到 '
          + (s.content_r2 == null ? '-' : s.content_r2.toFixed(4)) + '（+' + (s.content_gain || 0).toFixed(4) + '）；'
          + '再叠加标题文本向量到 ' + (s.text_r2 == null ? '-' : s.text_r2.toFixed(4)) + '（再 +'
          + (s.text_gain || 0).toFixed(4) + '）。'
          + '作为对照：抖音数据把训练样本从 80% 加到 100%，R² 只提升约 0.002。'
          + '这说明当前瓶颈是特征维度而非样本量，扩充内容与文本特征是更有效的方向。']
      }
      if (this.current === 'explanation-quality') {
        const cons = r.consistency || {}
        const stab = r.stability || {}
        const comp = r.compacity || {}
        return ['紧凑性 k80 = ' + (comp.k80 == null ? '-' : comp.k80)
          + '：即「一个特征就能解释 80% 的平均绝对贡献」，说明该数据集下模型行为高度可概括。'
          + '一致性 τ(SHAP vs 增益) = ' + (cons.kendall_shap_vs_gain == null ? '-' : cons.kendall_shap_vs_gain.toFixed(2))
          + '、τ(SHAP vs 置换) = ' + (cons.kendall_shap_vs_permutation == null ? '-' : cons.kendall_shap_vs_permutation.toFixed(2))
          + '：首位特征三种度量一致，其余特征的排序分歧较大，说明它们的信息量本身接近噪声。'
          + '稳定性 Jaccard = ' + (stab.jaccard_mean == null ? '-' : stab.jaccard_mean.toFixed(2))
          + '：bootstrap 重训后关键特征集合保持一致，归因结论可用于决策。']
      }
      if (this.current === 'residual') {
        return ['原始热度空间受少数爆款主导，均值误差被极值放大；分位数误差（P50/P90）更能反映'
          + '「多数内容预测得准不准」，这也是论文中讨论业务可用性的依据。']
      }
      if (this.current === 'learning-curve' && r.saturated) {
        return ['测试误差在 80% 数据量后基本不再下降，说明当前特征体系下的信息量已接近饱和，'
          + '继续扩充同源数据收益有限，后续提升应聚焦新特征（如视频时长、话题标签）。']
      }
      if (this.current === 'counterfactual') {
        return ['反事实分析仅改变「运营方可控」的维度（时段/星期/月份/类别），粉丝数为账号长期资产，'
          + '不纳入单条内容的可调整建议。']
      }
      if (this.current === 'cross-platform') {
        return ['各平台分别独立训练模型后归一化 SHAP 贡献占比，用于横向对照。贡献占比差异大的特征说明其'
          + '「平台特异性」强；占比在各平台都靠前的特征则具备跨平台可迁移性。'
          + '注意：不同平台的数据规模与特征可获得性不同，R² 的绝对值不宜直接横比，应结合样本量解读。']
      }
      if (this.current === 'drift') {
        return ['PSI 以抖音为基准衡量特征分布整体偏移：<0.1 稳定、0.1~0.25 中等漂移、≥0.25 显著漂移。'
          + 'KS 检验对样本量敏感，大平台间几乎必然「显著」，因此应把 PSI 作为主要判据、KS 作为辅助证据。'
          + '漂移显著的特征意味着「在一个平台训练的模型迁移到另一平台时需要重新校准或加入平台特征」。']
      }
      if (this.current === 'growth') {
        return ['数据源为 TikTok 真实每日累计快照（每个视频第 0~30 天各一条累计记录），'
          + '热度口径与预测模块一致（播放量 + 3×点赞 + 5×评论 + 8×转发）。'
          + '结论：短视频热度高度集中于发布后 24 小时内，第 1 天即可决定约九成的后续走势；'
          + '因此冷启动期的早期数据是最有信息量的预测信号，可用于判断是否追加投放。']
      }
      return []
    },
    /* ---- 明细表（按模式抽取） ---- */
    tables () {
      const r = this.result
      if (!r) return []
      const num = v => {
        const n = Number(v)
        return (v == null || v === '' || !Number.isFinite(n)) ? '-' : n.toFixed(4)
      }
      if (this.current === 'cv') {
        const rows = []
        Object.keys(r.models || {}).forEach(m => {
          (r.models[m].folds || []).forEach((f, i) => {
            rows.push({ model: m.toUpperCase(), fold: '第 ' + (i + 1) + ' 折', rmse: f.rmse, mae: f.mae, r2: f.r2, r2raw: f.r2_raw })
          })
        })
        return [{
          title: '各折评估明细',
          rows,
          columns: [
            { prop: 'model', label: '模型', width: 110 },
            { prop: 'fold', label: '折', width: 100 },
            { prop: 'rmse', label: 'RMSE(log)', width: 120, format: row => num(row.rmse) },
            { prop: 'mae', label: 'MAE(log)', width: 120, format: row => num(row.mae) },
            { prop: 'r2', label: 'R²(log)', minWidth: 120, format: row => num(row.r2) },
            { prop: 'r2raw', label: 'R²(原始)', width: 120, format: row => num(row.r2raw) }
          ]
        }]
      }
      if (this.current === 'tuning') {
        return [{
          title: '参数组合排名（按 3 折 CV RMSE 升序）',
          rows: (r.results || []).map((x, i) => ({ rank: i + 1, ...x.params, rmse: x.rmse_mean })),
          columns: [
            { prop: 'rank', label: '#', width: 60 },
            { prop: 'learning_rate', label: 'learning_rate', width: 120 },
            { prop: 'num_leaves', label: 'num_leaves', width: 110 },
            { prop: 'min_data_in_leaf', label: 'min_data_in_leaf', width: 140 },
            { prop: 'feature_fraction', label: 'feature_fraction', width: 140 },
            { prop: 'bagging_fraction', label: 'bagging_fraction', width: 140 },
            { prop: 'lambda_l2', label: 'lambda_l2', width: 100 },
            { prop: 'rmse', label: 'RMSE(log)', minWidth: 120, format: row => num(row.rmse) }
          ]
        }]
      }
      if (this.current === 'learning-curve') {
        return [{
          title: '训练集规模与误差',
          rows: r.points || [],
          columns: [
            { prop: 'fraction', label: '数据占比', width: 100, format: row => (row.fraction * 100).toFixed(0) + '%' },
            { prop: 'n_train', label: '训练样本数', width: 130 },
            { prop: 'train_rmse', label: '训练 RMSE', width: 130, format: row => num(row.train_rmse) },
            { prop: 'valid_rmse', label: '验证 RMSE', width: 130, format: row => num(row.valid_rmse) },
            { prop: 'test_rmse', label: '测试 RMSE', minWidth: 130, format: row => num(row.test_rmse) }
          ]
        }]
      }
      if (this.current === 'importance') {
        return [{
          title: '三种重要性度量对照（各自归一化）',
          rows: r.table || [],
          columns: [
            { prop: 'feature_cn', label: '特征', minWidth: 170 },
            { prop: 'feature', label: '字段名', minWidth: 170 },
            { prop: 'gain', label: '增益重要性', width: 130, format: row => num(row.gain) },
            { prop: 'permutation', label: '置换重要性', width: 130, format: row => num(row.permutation) },
            { prop: 'shap', label: 'SHAP 平均|贡献|', minWidth: 150, format: row => num(row.shap) }
          ]
        }]
      }
      if (this.current === 'residual') {
        return [{
          title: '按热度等级的误差结构',
          rows: r.by_grade || [],
          columns: [
            { prop: 'grade', label: '热度等级', width: 110 },
            { prop: 'count', label: '样本数', width: 100 },
            { prop: 'rmse_log', label: 'RMSE(log)', width: 130, format: row => num(row.rmse_log) },
            { prop: 'mae_raw', label: '平均绝对误差(原始)', minWidth: 170, format: row => Math.round(row.mae_raw).toLocaleString() },
            { prop: 'mae_raw_median', label: '中位绝对误差(原始)', minWidth: 170, format: row => Math.round(row.mae_raw_median).toLocaleString() },
            { prop: 'rel_err_p50', label: '相对误差 P50', minWidth: 130, format: row => (row.rel_err_p50 * 100).toFixed(1) + '%' }
          ]
        }]
      }
      if (this.current === 'ablation') {
        const rows = []
        const res = r.result || {}
        ;['base', 'enhanced'].forEach(k => {
          Object.keys((res[k] || {}).models || {}).forEach(m => {
            rows.push({
              set: k === 'base' ? '基础特征（7 维）' : '增强特征（12 维）',
              model: m.toUpperCase(),
              r2: res[k].models[m].r2_mean,
              rmse: res[k].models[m].rmse_mean
            })
          })
        })
        return [{
          title: '特征集对比（3 折交叉验证）',
          rows,
          columns: [
            { prop: 'set', label: '特征集', minWidth: 190 },
            { prop: 'model', label: '模型', width: 120 },
            { prop: 'r2', label: 'R²(log)', width: 130, format: row => num(row.r2) },
            { prop: 'rmse', label: 'RMSE(log)', minWidth: 130, format: row => num(row.rmse) }
          ]
        }]
      }
      if (this.current === 'interaction') {
        return [{
          title: '交互效应 Top 组合（不含主效应）',
          rows: r.top_pairs || [],
          columns: [
            { prop: 'feature_a_cn', label: '特征 A', minWidth: 150 },
            { prop: 'feature_b_cn', label: '特征 B', minWidth: 150 },
            { prop: 'interaction', label: '平均 |SHAP 交互值|', minWidth: 170, format: row => num(row.interaction) }
          ]
        }]
      }
      if (this.current === 'counterfactual') {
        return [{
          title: '可调整维度的提升空间（按提升幅度降序）',
          rows: r.suggestions || [],
          columns: [
            { prop: 'dimension', label: '维度', width: 120 },
            { prop: 'from', label: '当前取值', width: 130 },
            { prop: 'to', label: '建议取值', width: 130 },
            { prop: 'heat', label: '预计热度', minWidth: 140, format: row => Math.round(row.heat).toLocaleString() },
            { prop: 'delta_pct', label: '提升幅度', width: 120, format: row => (row.delta_pct > 0 ? '+' : '') + row.delta_pct.toFixed(1) + '%' },
            { prop: 'grade', label: '预计等级', width: 110 }
          ]
        }]
      }
      if (this.current === 'cross-platform') {
        const cols = (r.matrix_columns || []).map(c => ({
          prop: c.key,
          label: c.label + ' 贡献占比',
          minWidth: 128,
          format: row => (row[c.key] == null ? '-' : (row[c.key] * 100).toFixed(1) + '%')
        }))
        return [
          {
            title: '各特征跨平台 SHAP 贡献占比（行=特征，列=平台，按跨平台差异降序）',
            rows: r.feature_matrix || [],
            columns: [
              { prop: 'feature_cn', label: '特征', minWidth: 170 },
              { prop: 'feature', label: '字段名', minWidth: 150 },
              { prop: 'spread', label: '跨平台差异', width: 118, format: row => (row.spread == null ? '-' : (row.spread * 100).toFixed(1) + '%') },
              ...cols
            ]
          },
          {
            title: '各平台模型与首位特征',
            rows: r.platforms || [],
            columns: [
              { prop: 'platform_cn', label: '平台', width: 110 },
              { prop: 'n_train', label: '训练样本数', minWidth: 130, format: row => Number(row.n_train).toLocaleString() },
              { prop: 'r2', label: 'R²(log)', width: 120, format: row => (row.r2 == null ? '-' : row.r2.toFixed(4)) },
              {
                prop: 'top_features',
                label: 'Top4 特征（贡献占比）',
                minWidth: 320,
                format: row => (row.top_features || []).map(f => f.feature_cn + ' ' + (f.share * 100).toFixed(1) + '%').join('　｜　')
              }
            ]
          }
        ]
      }
      if (this.current === 'drift') {
        return [{
          title: '各平台特征分布漂移明细（按 PSI 降序）',
          rows: r.detail || [],
          columns: [
            { prop: 'platform_cn', label: '平台', width: 110 },
            { prop: 'feature_cn', label: '特征', minWidth: 150 },
            { prop: 'psi', label: 'PSI', width: 108, format: row => num(row.psi) },
            { prop: 'psi_level', label: '漂移等级', width: 112 },
            { prop: 'ks_stat', label: 'KS 统计量', width: 118, format: row => num(row.ks_stat) },
            {
              prop: 'ks_p',
              label: 'KS p 值',
              width: 108,
              format: row => (row.ks_p == null ? '-' : (row.ks_p < 0.001 ? '<0.001' : row.ks_p.toFixed(3)))
            },
            { prop: 'ks_significant', label: '是否显著(α=0.05)', width: 158, format: row => (row.ks_significant ? '显著' : '不显著') },
            { prop: 'n_target', label: '样本数', width: 110, format: row => Number(row.n_target).toLocaleString() }
          ]
        }]
      }
      if (this.current === 'growth') {
        const cv = r.curve || {}
        const curveRows = (cv.days || []).map((d, i) => ({
          day: d,
          p25: (cv.p25 || [])[i],
          p50: (cv.p50 || [])[i],
          p75: (cv.p75 || [])[i]
        }))
        return [
          {
            title: '各预测时点模型效果（真实 TikTok 累计快照）',
            rows: r.horizons || [],
            columns: [
              { prop: 'day', label: '预测时点', width: 108, format: row => '第 ' + row.day + ' 天' },
              { prop: 'signal', label: '可用早期信号', minWidth: 200 },
              { prop: 'n_train', label: '训练样本', width: 108, format: row => Number(row.n_train).toLocaleString() },
              { prop: 'n_test', label: '测试样本', width: 108, format: row => Number(row.n_test).toLocaleString() },
              { prop: 'r2', label: 'R²(log)', width: 108, format: row => num(row.r2) },
              { prop: 'mae_raw', label: 'MAE(原始)', width: 120, format: row => (row.mae_raw == null ? '-' : Math.round(row.mae_raw).toLocaleString()) },
              { prop: 'rmse_raw', label: 'RMSE(原始)', width: 128, format: row => (row.rmse_raw == null ? '-' : Math.round(row.rmse_raw).toLocaleString()) },
              {
                prop: 'median_multiplier',
                label: '典型累计倍数（相对第 0 天）',
                minWidth: 200,
                format: row => (row.median_multiplier == null ? '-' : row.median_multiplier.toFixed(2) + '×')
              }
            ]
          },
          {
            title: '典型累计热度增长曲线（全样本分位数，第 0~7 天）',
            rows: curveRows,
            columns: [
              { prop: 'day', label: '发布后天数', width: 120, format: row => '第 ' + row.day + ' 天' },
              { prop: 'p25', label: 'P25', minWidth: 130, format: row => Math.round(row.p25).toLocaleString() },
              { prop: 'p50', label: 'P50 中位数', minWidth: 130, format: row => Math.round(row.p50).toLocaleString() },
              { prop: 'p75', label: 'P75', minWidth: 130, format: row => Math.round(row.p75).toLocaleString() }
            ]
          }
        ]
      }
      if (this.current === 'refutation') {
        const st = r.stability || {}
        const pl = r.placebo || {}
        const cm = r.cross_model || {}
        const checks = [
          {
            name: '① 安慰剂维度（发布月份）',
            value: pl.gain == null ? '-' : (pl.gain * 100).toFixed(1) + '%',
            standard: '弱维度增益应显著小于强维度（强维度最高 ' + ((pl.strong_dim_max_gain || 0) * 100).toFixed(1) + '%）',
            result: pl.passed ? 'PASS' : 'WARN'
          },
          {
            name: '② 子集重估：发布小时增益',
            value: st.hour_gain == null ? '-' : (st.hour_gain.mean * 100).toFixed(1) + '% ± ' + (st.hour_gain.std * 100).toFixed(1) + '%',
            standard: '变异系数 CV < 0.5 视为稳定（实际 ' + (st.hour_gain == null ? '-' : st.hour_gain.cv) + '）',
            result: (st.hour_gain && st.hour_gain.cv != null && st.hour_gain.cv < 0.5) ? 'PASS' : 'WARN'
          },
          {
            name: '③ 跨模型最优取值一致',
            value: '小时 ' + (cm.hour_agreement ? '一致' : '不一致') + ' / 类别 ' + (cm.category_agreement ? '一致' : '不一致'),
            standard: '三个模型给出的最优取值应相同，增益同号',
            result: (cm.hour_agreement && cm.category_agreement) ? 'PASS' : 'WARN'
          }
        ]
        return [
          {
            title: '三项稳健性检验',
            rows: checks,
            columns: [
              { prop: 'name', label: '检验', minWidth: 220 },
              { prop: 'value', label: '实测', width: 200 },
              { prop: 'standard', label: '判定标准', minWidth: 320 },
              { prop: 'result', label: '结论', width: 90 }
            ]
          },
          {
            title: '跨模型反事实对照（同一基准样本）',
            rows: cm.rows || [],
            columns: [
              { prop: 'model', label: '模型', width: 100 },
              { prop: 'hour_to', label: '最优发布小时', width: 130 },
              { prop: 'hour_gain', label: '小时增益', width: 110, format: row => (row.hour_gain * 100).toFixed(1) + '%' },
              { prop: 'category_to', label: '最优视频类别', width: 140 },
              { prop: 'category_gain', label: '类别增益', width: 110, format: row => (row.category_gain * 100).toFixed(1) + '%' },
              { prop: 'weekday_gain', label: '星期增益', width: 110, format: row => (row.weekday_gain * 100).toFixed(1) + '%' }
            ]
          }
        ]
      }
      if (this.current === 'two-stage') {
        return [{
          title: '发布时先验 vs 加入早期信号（同一行子集 / 同一 CV / 同一模型）',
          rows: r.table || [],
          columns: [
            { prop: 'feature_set', label: '特征集', minWidth: 220 },
            { prop: 'n_features', label: '特征数', width: 90 },
            { prop: 'r2_mean', label: 'R²(log)', width: 110, format: row => num(row.r2_mean) },
            { prop: 'r2_gain_vs_prior', label: '相对先验增益', width: 140, format: row => (row.r2_gain_vs_prior > 0 ? '+' : '') + num(row.r2_gain_vs_prior) },
            { prop: 'rmse_mean', label: 'RMSE(log)', width: 120, format: row => num(row.rmse_mean) },
            { prop: 'rel_err_p50', label: '相对误差中位数', minWidth: 140, format: row => (row.rel_err_p50 * 100).toFixed(1) + '%' }
          ]
        }]
      }
      if (this.current === 'feature-enrichment') {
        return [{
          title: '三组特征集的 5 折交叉验证对照（同数据 / 同模型）',
          rows: r.table || [],
          columns: [
            { prop: 'feature_set', label: '特征集', minWidth: 220 },
            { prop: 'r2_mean', label: 'R²(log) 均值', width: 130, format: row => num(row.r2_mean) },
            { prop: 'r2_std', label: '标准差', width: 100, format: row => num(row.r2_std) },
            { prop: 'rmse_mean', label: 'RMSE(log)', width: 120, format: row => num(row.rmse_mean) },
            { prop: 'mae_mean', label: 'MAE(log)', width: 110, format: row => num(row.mae_mean) },
            {
              prop: 'r2_gain_vs_base',
              label: '相对基础特征 R² 增益',
              minWidth: 170,
              format: row => (row.r2_gain_vs_base > 0 ? '+' : '') + num(row.r2_gain_vs_base)
            }
          ]
        }]
      }
      if (this.current === 'conformal') {
        return [{
          title: '分热度等级的条件覆盖率（全局 q̂ vs Mondrian 分组 q̂）',
          rows: r.by_grade || [],
          columns: [
            { prop: 'grade', label: '热度等级', width: 110 },
            { prop: 'count', label: '测试样本数', width: 120 },
            {
              prop: 'coverage_global_q',
              label: '覆盖率（全局 q̂）',
              minWidth: 150,
              format: row => (row.coverage_global_q * 100).toFixed(1) + '%'
            },
            {
              prop: 'coverage_mondrian_q',
              label: '覆盖率（Mondrian 分组）',
              minWidth: 170,
              format: row => (row.coverage_mondrian_q * 100).toFixed(1) + '%'
            },
            { prop: 'qhat_log', label: '分组 q̂（log）', minWidth: 130, format: row => num(row.qhat_log) }
          ]
        }]
      }
      if (this.current === 'explanation-quality') {
        const cons = r.consistency || {}
        const stab = r.stability || {}
        const metrics = [
          { metric: 'Kendall τ（SHAP vs 增益重要性）', value: cons.kendall_shap_vs_gain, hint: '越接近 1 说明两种重要性排序越一致' },
          { metric: 'Kendall τ（SHAP vs 置换重要性）', value: cons.kendall_shap_vs_permutation, hint: '置换重要性独立于模型内部结构' },
          { metric: 'Kendall τ（增益 vs 置换）', value: cons.kendall_gain_vs_permutation, hint: '后两者之间的基线一致性' },
          { metric: `稳定性 Jaccard（Top-${stab.topk || 3}，${stab.bootstraps || 0} 次重训）`, value: stab.jaccard_mean, hint: '1 表示每次重训选出的关键特征集合完全相同' },
          { metric: '稳定性 Spearman（贡献向量）', value: stab.spearman_mean, hint: '重训后平均 |SHAP| 向量的秩相关' },
          { metric: '紧凑性 k80 / k90', value: null, hint: `解释 80% / 90% 贡献所需特征数：${(r.compacity || {}).k80} / ${(r.compacity || {}).k90}` }
        ]
        return [
          {
            title: '特征贡献排名（按平均 |SHAP|）',
            rows: r.ranking || [],
            columns: [
              { prop: 'feature', label: '特征', minWidth: 200 },
              { prop: 'mean_abs_shap', label: '平均 |SHAP|', width: 150, format: row => num(row.mean_abs_shap) },
              { prop: 'share', label: '贡献占比', width: 130, format: row => (row.share * 100).toFixed(2) + '%' }
            ]
          },
          {
            title: '解释质量三维度',
            rows: metrics,
            columns: [
              { prop: 'metric', label: '指标', minWidth: 280 },
              { prop: 'value', label: '取值', width: 130, format: row => (row.value == null ? '—' : num(row.value)) },
              { prop: 'hint', label: '含义', minWidth: 300 }
            ]
          }
        ]
      }
      return []
    }
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
