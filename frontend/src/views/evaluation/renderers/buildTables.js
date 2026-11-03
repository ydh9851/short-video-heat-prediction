/**
 * buildTables —— 按实验模式构造结果区的展示内容。
 *
 * 纯函数：只依赖模式名与该次实验的返回结果，便于单独测试与复用。
 */

export function buildTables (mode, r) {
  if (!r) return []
    const num = v => {
      const n = Number(v)
      return (v == null || v === '' || !Number.isFinite(n)) ? '-' : n.toFixed(4)
    }
    if (mode === 'cv') {
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
    if (mode === 'tuning') {
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
    if (mode === 'learning-curve') {
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
    if (mode === 'importance') {
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
    if (mode === 'residual') {
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
    if (mode === 'ablation') {
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
    if (mode === 'interaction') {
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
    if (mode === 'counterfactual') {
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
    if (mode === 'cross-platform') {
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
    if (mode === 'drift') {
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
    if (mode === 'growth') {
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
    if (mode === 'target-compare') {
      const rows = r.rows || []
      const heat = rows.find(x => x.target === 'heat') || {}
      const play = rows.find(x => x.target === 'play') || {}
      const shifts = r.feature_shift || []
      const featRows = []
      const names = []
      ;(heat.top_features || []).forEach(f => names.push(f.feature))
      ;(play.top_features || []).forEach(f => { if (!names.includes(f.feature)) names.push(f.feature) })
      names.forEach(name => {
        const h = (heat.top_features || []).find(f => f.feature === name)
        const p = (play.top_features || []).find(f => f.feature === name)
        const s = shifts.find(x => x.feature === name)
        featRows.push({
          feature: name,
          heat_share: h ? h.share : null,
          play_share: p ? p.share : null,
          rank_heat: s ? s.rank_heat : null,
          rank_play: s ? s.rank_play : null,
          delta: s ? s.delta : null
        })
      })
      return [
        {
          title: '两种目标口径的拟合结果（同一数据 / 同一特征 / 同一模型 / 同一测试集）',
          rows: rows.map(x => ({
            target_desc: x.target_desc,
            r2: x.r2,
            rmse: x.rmse,
            mae: x.mae,
            rel: x.rel_err_p50
          })),
          columns: [
            { prop: 'target_desc', label: '预测目标', minWidth: 260 },
            { prop: 'r2', label: 'R²(log)', width: 110, format: row => row.r2 == null ? '-' : row.r2.toFixed(4) },
            { prop: 'rmse', label: 'RMSE(log)', width: 110, format: row => row.rmse == null ? '-' : row.rmse.toFixed(4) },
            { prop: 'mae', label: 'MAE(log)', width: 105, format: row => row.mae == null ? '-' : row.mae.toFixed(4) },
            { prop: 'rel', label: '相对误差中位数', width: 135, format: row => row.rel == null ? '-' : (row.rel * 100).toFixed(1) + '%' }
          ]
        },
        {
          title: '特征贡献对照（SHAP 平均 |贡献| 占比与排名位移）',
          rows: featRows,
          columns: [
            { prop: 'feature', label: '特征', minWidth: 200 },
            { prop: 'heat_share', label: '热度口径占比', width: 130, format: row => row.heat_share == null ? '-' : (row.heat_share * 100).toFixed(2) + '%' },
            { prop: 'play_share', label: '播放量口径占比', width: 140, format: row => row.play_share == null ? '-' : (row.play_share * 100).toFixed(2) + '%' },
            { prop: 'rank_heat', label: '热度排名', width: 95, format: row => row.rank_heat == null ? '-' : '#' + row.rank_heat },
            { prop: 'rank_play', label: '播放量排名', width: 105, format: row => row.rank_play == null ? '-' : '#' + row.rank_play },
            { prop: 'delta', label: '排名位移', width: 95, format: row => row.delta == null ? '-' : (row.delta > 0 ? '+' + row.delta : row.delta) }
          ]
        }
      ]
    }
    if (mode === 'refutation') {
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
    if (mode === 'two-stage') {
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
    if (mode === 'feature-enrichment') {
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
    if (mode === 'conformal') {
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
    if (mode === 'explanation-quality') {
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
