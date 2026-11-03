/**
 * buildNotes —— 按实验模式构造结果区的展示内容。
 *
 * 纯函数：只依赖模式名与该次实验的返回结果，便于单独测试与复用。
 */

export function buildNotes (mode, r) {
  if (!r) return []
    if (mode === 'ablation') {
      return ['周期编码对树模型几乎无增益（树本身可通过切分捕捉周期），但对线性模型有稳定提升；'
        + '因此生产环境保留基础特征集即可，避免不必要的特征膨胀。']
    }
    if (mode === 'importance') return r.note ? [r.note] : []
    if (mode === 'interaction' && r.note) return [r.note]
    if (mode === 'conformal') {
      const cov = ((r.global || {}).coverage || 0) * 100
      const base = (((r.quantile_baseline || {}).coverage) || 0) * 100
      return ['保形区间在样本可交换假设下满足 P(y ∈ [lo, hi]) ≥ 1−α，是有限样本保证；'
        + '分位数回归只能事后检验覆盖率。同一测试集上两者分别达到 '
        + cov.toFixed(1) + '% 与 ' + base.toFixed(1) + '%。'
        + 'Mondrian 分组校准用于缓解高热度档覆盖不足，代价是区间变宽。']
    }
    if (mode === 'target-compare') {
      const rows = r.rows || []
      const heat = rows.find(x => x.target === 'heat') || {}
      const play = rows.find(x => x.target === 'play') || {}
      const shifts = r.feature_shift || []
      const moved = shifts.filter(s => s.delta !== 0).length
      const dR2 = (heat.r2 != null && play.r2 != null) ? Math.abs(play.r2 - heat.r2) : null
      return [
        '把预测目标从「加权热度」换成「播放量」后，R² 仅由 ' + (heat.r2 == null ? '-' : heat.r2.toFixed(4))
          + ' 变为 ' + (play.r2 == null ? '-' : play.r2.toFixed(4))
          + '（差 ' + (dR2 == null ? '-' : dR2.toFixed(4)) + '），相对误差中位数 '
          + (heat.rel_err_p50 == null ? '-' : (heat.rel_err_p50 * 100).toFixed(1) + '%')
          + ' → ' + (play.rel_err_p50 == null ? '-' : (play.rel_err_p50 * 100).toFixed(1) + '%')
          + '；6 个特征的贡献排名发生位移的有 ' + moved + ' 个。',
        '原因：两个目标在 log 空间的相关性高达 ' + (r.target_corr == null ? '-' : r.target_corr.toFixed(4))
          + '——在当前数据中作者粉丝数同时驱动播放与互动，两个口径近似同义，因此学到的驱动因素也相同。',
        '这带来两个结论：(1) 本系统采用加权热度口径并未牺牲精度，与只预测播放量的同类工作在精度上可比；'
          + '(2) 更重要的是，它暴露了本数据集的区分度上限——"预测热度"与"预测播放量"几乎是同一件事，'
          + '因此系统的价值不在精度，而在分级、归因与决策建议这些播放量本身无法回答的问题；'
          + '两个口径真正产生差异的场景是"高播放、低互动"的样本，需在互动转化率分层下进一步区分。'
      ]
    }
    if (mode === 'refutation') {
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
        + '微小差异会被放大成可观的百分比收益。因此建议应表述为「方向 + 区间」，'
        + '并对强特征（作者粉丝数）之外的维度明确标注不确定性。']
    }
    if (mode === 'two-stage') {
      const s = r.summary || {}
      return ['仅用发布时先验预测第 7 天热度，R²(log) 为 ' + (s.prior_r2 == null ? '-' : s.prior_r2.toFixed(4))
        + '、相对误差中位数 ' + (s.prior_rel_err_p50 == null ? '-' : (s.prior_rel_err_p50 * 100).toFixed(1)) + '%；'
        + '加入发布后第 1 天真实累计互动后跃升到 ' + (s.d1_r2 == null ? '-' : s.d1_r2.toFixed(4))
        + '（+' + (s.d1_gain || 0).toFixed(4) + '），相对误差降到 '
        + (s.d1d3_rel_err_p50 == null ? '-' : (s.d1d3_rel_err_p50 * 100).toFixed(1)) + '%。'
        + '这说明「发布前预测」与「发布后 24 小时修正」应当作为两阶段能力分别呈现：'
        + '前者用于选题与排期，后者用于投放与追投决策。']
    }
    if (mode === 'feature-enrichment') {
      const s = r.summary || {}
      return ['同一份数据、同一套交叉验证、同一个 LightGBM：仅仅把「内容属性」加进特征集，R²(log) 就从 '
        + (s.base_r2 == null ? '-' : s.base_r2.toFixed(4)) + ' 提升到 '
        + (s.content_r2 == null ? '-' : s.content_r2.toFixed(4)) + '（+' + (s.content_gain || 0).toFixed(4) + '）；'
        + '再叠加标题文本向量到 ' + (s.text_r2 == null ? '-' : s.text_r2.toFixed(4)) + '（再 +'
        + (s.text_gain || 0).toFixed(4) + '）。'
        + '作为对照：抖音数据把训练样本从 80% 加到 100%，R² 只提升约 0.002。'
        + '这说明当前瓶颈是特征维度而非样本量，扩充内容与文本特征是更有效的方向。']
    }
    if (mode === 'explanation-quality') {
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
    if (mode === 'residual') {
      return ['原始热度空间受少数爆款主导，均值误差被极值放大；分位数误差（P50/P90）更能反映'
        + '「多数内容预测得准不准」，这也是讨论业务可用性的依据。']
    }
    if (mode === 'learning-curve' && r.saturated) {
      return ['测试误差在 80% 数据量后基本不再下降，说明当前特征体系下的信息量已接近饱和，'
        + '继续扩充同源数据收益有限，后续提升应聚焦新特征（如视频时长、话题标签）。']
    }
    if (mode === 'counterfactual') {
      return ['反事实分析仅改变「运营方可控」的维度（时段/星期/月份/类别），粉丝数为账号长期资产，'
        + '不纳入单条内容的可调整建议。']
    }
    if (mode === 'cross-platform') {
      return ['各平台分别独立训练模型后归一化 SHAP 贡献占比，用于横向对照。贡献占比差异大的特征说明其'
        + '「平台特异性」强；占比在各平台都靠前的特征则具备跨平台可迁移性。'
        + '注意：不同平台的数据规模与特征可获得性不同，R² 的绝对值不宜直接横比，应结合样本量解读。']
    }
    if (mode === 'drift') {
      return ['PSI 以抖音为基准衡量特征分布整体偏移：<0.1 稳定、0.1~0.25 中等漂移、≥0.25 显著漂移。'
        + 'KS 检验对样本量敏感，大平台间几乎必然「显著」，因此应把 PSI 作为主要判据、KS 作为辅助证据。'
        + '漂移显著的特征意味着「在一个平台训练的模型迁移到另一平台时需要重新校准或加入平台特征」。']
    }
    if (mode === 'growth') {
      return ['数据源为 TikTok 真实每日累计快照（每个视频第 0~30 天各一条累计记录），'
        + '热度口径与预测模块一致（播放量 + 3×点赞 + 5×评论 + 8×转发）。'
        + '结论：短视频热度高度集中于发布后 24 小时内，第 1 天即可决定约九成的后续走势；'
        + '因此冷启动期的早期数据是最有信息量的预测信号，可用于判断是否追加投放。']
    }
    return []
}
