/**
 * buildSummary —— 按实验模式构造结果区的展示内容。
 *
 * 纯函数：只依赖模式名与该次实验的返回结果，便于单独测试与复用。
 */

export function buildSummary (mode, r) {
  if (!r) return []
    const out = []
    const pct = v => {
      const n = Number(v)
      return (v == null || v === '' || !Number.isFinite(n)) ? '-' : (n * 100).toFixed(2) + '%'
    }
    if (mode === 'cv') {
      Object.keys(r.models || {}).forEach(m => {
        out.push({
          label: m.toUpperCase() + ' R²(log)',
          value: r.models[m].r2_mean.toFixed(4) + ' ± ' + r.models[m].r2_std.toFixed(4),
          tone: m === r.best ? 'tone-best' : ''
        })
      })
    } else if (mode === 'tuning') {
      out.push({ label: '最优 3 折 CV RMSE', value: r.best_rmse.toFixed(4), tone: 'tone-best' })
      out.push({ label: '试验次数', value: r.trials + ' 组参数' })
      Object.keys(r.best_params || {}).forEach(k => {
        out.push({ label: k, value: String(r.best_params[k]) })
      })
    } else if (mode === 'learning-curve') {
      const pts = r.points || []
      out.push({ label: '最终测试集 RMSE', value: pts.length ? pts[pts.length - 1].test_rmse.toFixed(4) : '-' })
      out.push({ label: '首点测试集 RMSE', value: pts.length ? pts[0].test_rmse.toFixed(4) : '-' })
      out.push({ label: '训练/验证间隙', value: r.final_gap.toFixed(4) })
      out.push({ label: '数据量是否饱和', value: r.saturated ? '已饱和（继续加数据收益极小）' : '未饱和' })
    } else if (mode === 'importance') {
      out.push({ label: '首位特征', value: (r.top3 && r.top3[0]) || '-', tone: 'tone-best' })
      out.push({ label: '三种度量首位一致', value: r.top1_consistent ? '一致' : '不一致' })
      out.push({ label: '前 3 名重合特征数', value: r.top3_overlap + ' / 3' })
    } else if (mode === 'residual') {
      out.push({ label: 'P50 绝对误差', value: r.abs_err_quantiles_raw.p50.toFixed(1) })
      out.push({ label: 'P90 绝对误差', value: r.abs_err_quantiles_raw.p90.toFixed(1) })
      out.push({ label: 'P99 绝对误差', value: r.abs_err_quantiles_raw.p99.toFixed(1) })
      out.push({ label: 'P50 相对误差', value: pct(r.rel_err_quantiles.p50) })
    } else if (mode === 'ablation') {
      Object.keys(r.r2_delta || {}).forEach(m => {
        const d = r.r2_delta[m]
        out.push({
          label: m.toUpperCase() + ' R² 变化（增强 - 基础）',
          value: (d > 0 ? '+' : '') + d.toFixed(4),
          tone: d > 0 ? 'tone-good' : 'tone-flat'
        })
      })
    } else if (mode === 'quantile') {
      const iv = r.interval || {}
      out.push({ label: 'P10（保守）', value: Math.round(iv.p10).toLocaleString() })
      out.push({ label: 'P50（中性）', value: Math.round(iv.p50).toLocaleString(), tone: 'tone-best' })
      out.push({ label: 'P90（乐观）', value: Math.round(iv.p90).toLocaleString() })
      out.push({ label: '区间宽度', value: Math.round(r.width).toLocaleString() })
      out.push({ label: '分级参考', value: r.grade })
      if (r.coverage_report) {
        out.push({ label: '区间覆盖率（测试集）', value: pct(r.coverage_report.coverage) })
      }
    } else if (mode === 'interaction') {
      out.push({ label: '最强交互组合', value: r.strongest_pair ? (r.strongest_pair.feature_a_cn + ' × ' + r.strongest_pair.feature_b_cn) : '-', tone: 'tone-best' })
      out.push({ label: '最强交互强度', value: r.strongest_pair ? r.strongest_pair.interaction.toFixed(4) : '-' })
      out.push({ label: '首位特征主效应', value: r.main_effects.length ? r.main_effects[0].main_effect.toFixed(4) : '-' })
    } else if (mode === 'counterfactual') {
      out.push({ label: '当前预测热度', value: Math.round(r.base_heat).toLocaleString(), tone: 'tone-best' })
      out.push({ label: '当前热度等级', value: r.base_grade })
      const best = (r.suggestions || [])[0]
      out.push({ label: '最优可调整项', value: best ? (best.dimension + ' → ' + best.to) : '当前已是最优' })
      out.push({ label: '预计最大提升', value: best ? ('+' + best.delta_pct.toFixed(1) + '%') : '-' })
    } else if (mode === 'cross-platform') {
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
    } else if (mode === 'drift') {
      out.push({ label: '基准平台', value: r.reference_cn })
      out.push({ label: '最大 PSI', value: (r.max_psi == null ? '-' : r.max_psi.toFixed(3)), tone: 'tone-best' })
      out.push({ label: '漂移最显著平台', value: r.worst_platform })
      out.push({ label: '漂移最显著特征', value: r.worst_feature })
      out.push({ label: '稳定（PSI<0.1）占比', value: ((r.stable_ratio || 0) * 100).toFixed(0) + '%' })
    } else if (mode === 'growth') {
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
    } else if (mode === 'conformal') {
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
    } else if (mode === 'explanation-quality') {
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
    } else if (mode === 'feature-enrichment') {
      const t = r.table || []
      const s = r.summary || {}
      out.push({ label: '参与视频数', value: Number(r.rows || 0).toLocaleString() })
      out.push({ label: '基础先验 R²(log)', value: s.base_r2 == null ? '-' : s.base_r2.toFixed(4) })
      out.push({ label: '+内容属性 R²(log)', value: s.content_r2 == null ? '-' : s.content_r2.toFixed(4), tone: 'tone-best' })
      out.push({ label: '+标题文本 R²(log)', value: s.text_r2 == null ? '-' : s.text_r2.toFixed(4), tone: 'tone-best' })
      out.push({ label: '内容增益', value: (s.content_gain == null ? '-' : '+' + s.content_gain.toFixed(4)) })
      out.push({ label: '文本增益', value: (s.text_gain == null ? '-' : '+' + s.text_gain.toFixed(4)) })
      if (t.length) out.push({ label: '目标口径', value: r.target || '-' })
    } else if (mode === 'target-compare') {
      const rows = r.rows || []
      const heat = rows.find(x => x.target === 'heat') || {}
      const play = rows.find(x => x.target === 'play') || {}
      const shifts = r.feature_shift || []
      const moved = shifts.filter(s => s.delta !== 0)
      out.push({ label: '两目标相关性 corr(log)', value: r.target_corr == null ? '-' : r.target_corr.toFixed(4) })
      out.push({ label: '加权热度 R²', value: heat.r2 == null ? '-' : heat.r2.toFixed(4), tone: 'tone-best' })
      out.push({ label: '播放量 R²', value: play.r2 == null ? '-' : play.r2.toFixed(4) })
      out.push({ label: 'R² 差值', value: (heat.r2 != null && play.r2 != null) ? (play.r2 - heat.r2).toFixed(4) : '-' })
      out.push({ label: '归因排名变化特征数', value: moved.length + ' / ' + shifts.length })
      out.push({ label: '首位特征贡献占比', value: heat.top_features && heat.top_features[0]
        ? (heat.top_features[0].feature + ' ' + (heat.top_features[0].share * 100).toFixed(2) + '%') : '-' })
    } else if (mode === 'refutation') {
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
    } else if (mode === 'two-stage') {
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
}
