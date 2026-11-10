<template>
  <div v-if="explain" class="explain-report">
    <div class="er-head">
      <div>
        <div class="er-eyebrow">解释报告 · EXPLANATION</div>
        <div class="er-title">这条视频为什么是「{{ grade }}」</div>
      </div>
      <el-tag :type="gradeTag" effect="dark" size="small">{{ grade }}</el-tag>
    </div>

    <!-- ============ 一、结论 ============ -->
    <section class="er-section">
      <div class="er-sec-title"><span class="er-idx">1</span>结论</div>
      <p class="er-conclusion">{{ conclusion }}</p>
      <div class="er-facts">
        <div class="er-fact">
          <span>预测热度</span>
          <b>{{ formatNum(explain.prediction) }}</b>
        </div>
        <div class="er-fact">
          <span>模型基线</span>
          <b>{{ formatNum(baseHeat) }}</b>
        </div>
        <div class="er-fact">
          <span>相对基线</span>
          <b :class="deltaPct >= 0 ? 'up' : 'down'">{{ signedPct }}</b>
        </div>
        <div class="er-fact">
          <span>log 空间偏离</span>
          <b :class="deltaLog >= 0 ? 'up' : 'down'">{{ signedLog }}</b>
        </div>
      </div>
      <div v-if="form" class="er-params">
        分析前提：{{ form.videoCategory }} · 粉丝 {{ fansText }} · {{ form.publishHour }} 点发布 ·
        {{ weekdayText }} · {{ form.publishMonth }} 月
      </div>
    </section>

    <!-- ============ 二、证据 ============ -->
    <section class="er-section">
      <div class="er-sec-title"><span class="er-idx">2</span>证据</div>
      <div class="er-evidence">
        <div class="er-col pos">
          <div class="er-col-title">拉高热度</div>
          <div v-for="c in positives" :key="c.feature" class="er-ev-item">
            <span class="er-ev-name">{{ c.feature_cn }}</span>
            <span class="er-ev-val">= {{ fmt(c.value, 2) }}</span>
            <b>+{{ Number(c.shap).toFixed(3) }}</b>
          </div>
          <div v-if="!positives.length" class="er-muted">无显著正贡献特征</div>
        </div>
        <div class="er-col neg">
          <div class="er-col-title">拖累热度</div>
          <div v-for="c in negatives" :key="c.feature" class="er-ev-item">
            <span class="er-ev-name">{{ c.feature_cn }}</span>
            <span class="er-ev-val">= {{ fmt(c.value, 2) }}</span>
            <b>{{ Number(c.shap).toFixed(3) }}</b>
          </div>
          <div v-if="!negatives.length" class="er-muted">无显著负贡献特征</div>
        </div>
      </div>
      <div class="er-sums">
        <span>正贡献合计 <b class="pos-text">+{{ posSum.toFixed(3) }}</b></span>
        <span>负贡献合计 <b class="neg-text">{{ negSum.toFixed(3) }}</b></span>
        <span>净效应 <b :class="net >= 0 ? 'pos-text' : 'neg-text'">{{ signed(net) }}</b></span>
        <span v-if="concentration != null">Top2 正贡献占正贡献 {{ concentration }}%</span>
      </div>
      <div class="er-trust">
        <template v-if="quality">
          <span class="er-trust-label">解释可信度</span>
          <span>紧凑性 k80 = <b>{{ (quality.compacity && quality.compacity.k80) || '-' }}</b></span>
          <span>一致性 τ = <b>{{ fmt(quality.consistency && quality.consistency.kendall_shap_vs_gain, 2) }}</b></span>
          <span>稳定性 Jaccard = <b>{{ fmt(quality.stability && quality.stability.jaccard_mean, 3) }}</b></span>
        </template>
        <span v-else class="er-muted">尚未运行「解释质量评估」实验，可信度指标暂缺</span>
      </div>
    </section>

    <!-- ============ 三、建议 ============ -->
    <section class="er-section">
      <div class="er-sec-title"><span class="er-idx">3</span>建议</div>
      <ul class="er-advice">
        <li v-for="(a, i) in advice" :key="i">{{ a }}</li>
      </ul>
      <div v-if="bestSuggestion" class="er-cf">
        <span class="er-chip">最大提升空间</span>
        {{ bestSuggestion.dimension }}：{{ bestSuggestion.from }} → <b>{{ bestSuggestion.to }}</b>，
        预计热度 {{ formatNum(bestSuggestion.heat) }}（{{ signedPctOf(bestSuggestion.delta_pct) }}）
      </div>
      <div v-else-if="cf" class="er-cf muted">当前条件下未发现可单条调整的显著提升项。</div>
    </section>

    <!-- ============ 四、局限 ============ -->
    <section class="er-section er-limits">
      <div class="er-sec-title"><span class="er-idx">4</span>局限</div>
      <ul>
        <li>SHAP 是<b>模型内</b>归因，反映当前 active 模型版本的决策依据，不等于真实因果效应。</li>
        <li>反事实建议来自模型内插值点估计{{ refutationText }}，请按「方向 + 区间」理解，不要当作精确收益承诺。</li>
        <li>贡献明细只展示 Top-K 特征，其余未展示；全局特征结论请以下方「全局归因」区块为准。</li>
      </ul>
    </section>
  </div>
</template>

<script>
/**
 * 解释报告：把单条 SHAP 归因、解释质量与反事实结果组织成
 * 「结论 → 证据 → 建议 → 局限」四段，图表仍由父页面作为证据展示。
 */
export default {
  name: 'ExplanationReport',
  props: {
    explain: { type: Object, default: null },
    quality: { type: Object, default: null },
    cf: { type: Object, default: null },
    refutation: { type: Object, default: null },
    form: { type: Object, default: null }
  },
  computed: {
    grade () {
      const p = Number(this.explain && this.explain.prediction)
      if (!Number.isFinite(p)) return '-'
      if (p < 684) return '低热度'
      if (p < 15661) return '中热度'
      return '高热度'
    },
    gradeTag () {
      return { 低热度: 'info', 中热度: 'warning', 高热度: 'danger' }[this.grade] || 'info'
    },
    /** 按 |shap| 从大到小取正贡献 Top2 */
    positives () {
      const list = (this.explain && this.explain.top_positive) ||
        ((this.explain && this.explain.contributions) || []).filter(c => Number(c.shap) > 0)
      return list.filter(c => Number(c.shap) > 0)
        .slice().sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap)).slice(0, 2)
    },
    /** 按 |shap| 从大到小取负贡献 Top2 */
    negatives () {
      const list = (this.explain && this.explain.top_negative) ||
        ((this.explain && this.explain.contributions) || []).filter(c => Number(c.shap) < 0)
      return list.filter(c => Number(c.shap) < 0)
        .slice().sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap)).slice(0, 2)
    },
    posSum () {
      return ((this.explain && this.explain.contributions) || [])
        .reduce((s, c) => s + (Number(c.shap) > 0 ? Number(c.shap) : 0), 0)
    },
    negSum () {
      return ((this.explain && this.explain.contributions) || [])
        .reduce((s, c) => s + (Number(c.shap) < 0 ? Number(c.shap) : 0), 0)
    },
    net () {
      return this.posSum + this.negSum
    },
    concentration () {
      if (this.posSum <= 0 || !this.positives.length) return null
      const top = this.positives.reduce((s, c) => s + Math.abs(Number(c.shap)), 0)
      return Math.round(top / this.posSum * 100)
    },
    baseHeat () {
      const b = Number(this.explain && this.explain.base_value)
      return Number.isFinite(b) ? Math.expm1(b) : null
    },
    deltaLog () {
      const p = Number(this.explain && this.explain.prediction_log)
      const b = Number(this.explain && this.explain.base_value)
      return Number.isFinite(p) && Number.isFinite(b) ? p - b : 0
    },
    deltaPct () {
      if (this.baseHeat == null || this.baseHeat <= 0) return null
      return (Number(this.explain.prediction) - this.baseHeat) / this.baseHeat * 100
    },
    signedPct () {
      if (this.deltaPct == null) return '-'
      return (this.deltaPct >= 0 ? '+' : '') + this.deltaPct.toFixed(1) + '%'
    },
    signedLog () {
      return this.signed(this.deltaLog)
    },
    conclusion () {
      const pos = this.positives.map(c => `「${c.feature_cn}」`).join('、')
      const neg = this.negatives.map(c => `「${c.feature_cn}」`).join('、')
      let s = `这条视频预计热度 ${this.formatNum(this.explain.prediction)}，属于「${this.grade}」`
      if (pos) s += `，主要被${pos}拉高`
      if (neg) s += `，同时被${neg}拖累`
      return s + '。'
    },
    advice () {
      const list = (this.explain && this.explain.advice) || []
      return list.length ? list : ['暂无自动建议，请结合下方特征贡献明细人工判断。']
    },
    /** 反事实中提升幅度最大的一条建议 */
    bestSuggestion () {
      const list = (this.cf && this.cf.suggestions) || []
      if (!list.length) return null
      return list.reduce((a, b) => (Number(b.delta_pct) > Number(a.delta_pct) ? b : a))
    },
    refutationText () {
      const hg = this.refutation && this.refutation.stability && this.refutation.stability.hour_gain
      if (!hg) return ''
      return `；子集重估显示发布小时增益 CV = ${hg.cv}（区间 ${Math.round(hg.min * 100)}% ~ ${Math.round(hg.max * 100)}%），最优取值在重训之间会漂移`
    },
    fansText () {
      const n = Number(this.form && this.form.authorFans) || 0
      if (n >= 10000) return (n / 10000).toFixed(n % 10000 === 0 ? 0 : 1) + ' 万'
      return this.formatNum(n)
    },
    weekdayText () {
      const list = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
      return list[this.form && this.form.publishWeekday] || '-'
    }
  },
  methods: {
    formatNum (v) {
      const n = Number(v)
      if (v == null || !Number.isFinite(n)) return '-'
      return Math.round(n).toLocaleString('en-US')
    },
    fmt (v, digits) {
      const n = Number(v)
      if (v == null || v === '' || !Number.isFinite(n)) return '-'
      return n.toFixed(digits == null ? 3 : digits)
    },
    signed (v) {
      const n = Number(v)
      if (!Number.isFinite(n)) return '-'
      return (n >= 0 ? '+' : '') + n.toFixed(3)
    },
    signedPctOf (v) {
      const n = Number(v)
      if (!Number.isFinite(n)) return '-'
      return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
    }
  }
}
</script>

<style lang="scss" scoped>
.explain-report {
  margin-bottom: 18px;
  padding: 16px 18px;
  border: 1px solid #e6e2fb;
  border-radius: 14px;
  background: linear-gradient(160deg, #fafaff 0%, #ffffff 60%);
}

.er-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed #e6e2fb;
}

.er-eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .08em;
  color: #94a3b8;
}

.er-title {
  margin-top: 4px;
  font-size: 16px;
  font-weight: 750;
  color: #1e293b;
}

.er-section {
  padding-top: 14px;
}

.er-sec-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 8px;
}

.er-idx {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 11px;
  font-weight: 700;
}

.er-conclusion {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.85;
  color: #334155;
}

.er-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.er-fact {
  padding: 8px 10px;
  border: 1px solid #eceafc;
  border-radius: 8px;
  background: #fff;

  span {
    display: block;
    font-size: 11.5px;
    color: #94a3b8;
  }

  b {
    display: block;
    margin-top: 3px;
    font-size: 15px;
    color: #1e293b;
    font-variant-numeric: tabular-nums;
  }

  b.up { color: #10b981; }
  b.down { color: #ef4444; }
}

.er-params {
  margin-top: 8px;
  font-size: 12px;
  color: #94a3b8;
}

.er-evidence {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.er-col {
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff;

  &.pos { border: 1px solid #d1fae5; }
  &.neg { border: 1px solid #fee2e2; }

  .er-col-title {
    font-size: 12px;
    font-weight: 700;
    margin-bottom: 6px;
  }

  &.pos .er-col-title { color: #059669; }
  &.neg .er-col-title { color: #dc2626; }
}

.er-ev-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 3px 0;
  font-size: 12.5px;
  color: #475569;

  .er-ev-name { font-weight: 600; color: #334155; }
  .er-ev-val { color: #94a3b8; font-size: 11.5px; }

  b {
    margin-left: auto;
    font-variant-numeric: tabular-nums;
  }

  .pos & b { color: #10b981; }
  .neg & b { color: #ef4444; }
}

.er-sums {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 18px;
  margin-top: 10px;
  font-size: 12px;
  color: #64748b;

  b { font-variant-numeric: tabular-nums; }
}

.er-trust {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f8fafc;
  font-size: 12px;
  color: #475569;

  .er-trust-label {
    font-weight: 700;
    color: #4f46e5;
  }

  b { color: #1e293b; }
}

.er-advice {
  margin: 0;
  padding-left: 18px;
  font-size: 12.5px;
  line-height: 1.9;
  color: #334155;

  li { margin-bottom: 2px; }
}

.er-cf {
  margin-top: 8px;
  padding: 8px 12px;
  border: 1px dashed #fde68a;
  border-radius: 8px;
  background: #fffbeb;
  font-size: 12.5px;
  line-height: 1.8;
  color: #92400e;

  &.muted {
    border-color: #e2e8f0;
    background: #f8fafc;
    color: #94a3b8;
  }
}

.er-chip {
  display: inline-block;
  margin-right: 6px;
  padding: 1px 8px;
  border-radius: 999px;
  background: #fef3c7;
  color: #b45309;
  font-size: 11px;
  font-weight: 700;
}

.er-limits {
  ul {
    margin: 0;
    padding-left: 18px;
    font-size: 12px;
    line-height: 1.9;
    color: #94a3b8;
  }
}

.er-muted {
  font-size: 12px;
  color: #b6bec9;
}

.pos-text { color: #10b981; }
.neg-text { color: #ef4444; }
</style>
