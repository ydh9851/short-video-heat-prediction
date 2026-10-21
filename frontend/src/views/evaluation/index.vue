<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">模型评估与实验分析</div>
        <div class="page-desc">
          面向论文实验章节的可复现实验平台：交叉验证、超参数搜索、学习曲线、特征重要性对照、
          残差与分位数误差、特征消融、预测区间、SHAP 交互效应与反事实分析。
        </div>
      </div>
      <div class="page-head-actions">
        <el-tag type="info" effect="plain">算法引擎：Python + LightGBM + SHAP</el-tag>
      </div>
    </div>

    <!-- ============ 实验选择 ============ -->
    <div class="exp-grid">
      <div
        v-for="m in modes"
        :key="m.mode"
        class="exp-card"
        :class="{ active: current === m.mode }"
        @click="selectMode(m)"
      >
        <div class="exp-head">
          <span class="exp-name">{{ m.name }}</span>
          <el-tag size="small" effect="plain" class="exp-tag">{{ m.tag }}</el-tag>
        </div>
        <p class="exp-desc">{{ m.description }}</p>
      </div>
    </div>

    <!-- ============ 运行面板 ============ -->
    <el-card shadow="never" class="run-card">
      <div class="run-head">
        <div class="section-title">实验参数</div>
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

        <span v-else class="param-hint">该实验无需额外参数，直接点击「开始实验」即可。</span>
      </div>
    </el-card>

    <!-- ============ 结果 ============ -->
    <div v-loading="running" element-loading-text="实验运行中，正在调用 Python 算法引擎…" class="result-wrap">
      <template v-if="result">
        <!-- 关键指标 -->
        <el-card shadow="never" class="block-card">
          <div class="section-title">关键结论</div>
          <div class="kv-grid">
            <div v-for="k in summary" :key="k.label" class="kv-item">
              <div class="kv-label">{{ k.label }}</div>
              <div class="kv-value" :class="k.tone">{{ k.value }}</div>
            </div>
          </div>
          <ul v-if="notes.length" class="note-list">
            <li v-for="(n, i) in notes" :key="i">{{ n }}</li>
          </ul>
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

      <el-empty v-else description="选择上方任一实验并点击「开始实验」，结果与图表会显示在这里" />
    </div>
  </div>
</template>

<script>
import evaluationApi from '@/api/evaluation'

const MODE_FIGURE_GROUP = {
  counterfactual: 'attr',
  'cross-platform': 'attr'
}

export default {
  name: 'EvaluationIndex',
  data () {
    return {
      modes: [],
      current: 'cv',
      running: false,
      result: null,
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
      return []
    }
  },
  created () {
    this.loadModes()
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
      const payload = { mode: this.current, ...this.form }
      evaluationApi.run(payload).then(re => {
        this.result = re.response || null
        this.running = false
        this.$message.success('实验完成')
      }).catch(() => { this.running = false })
    }
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
</style>
