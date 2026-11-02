<template>
  <div class="app-container about">
    <!-- ============ 项目头部 ============ -->
    <section class="about-hero">
      <div class="hero-left">
        <div class="hero-tags">
          <el-tag effect="dark" class="tag-tone">毕业设计</el-tag>
          <el-tag effect="plain" class="tag-plain">智能媒体工程学院</el-tag>
        </div>
        <h1>基于 LightGBM 的短视频热度预测与归因分析系统</h1>
        <p class="hero-sub">—— 含热度分级与运营决策支持</p>
        <p class="hero-desc">
          输入视频<strong>发布时即可获得</strong>的先验信息（视频类别 / 作者粉丝数 / 发布时段），
          系统即可输出其<strong>热度预测值</strong>、<strong>热度等级</strong>，并通过 SHAP 解释
          <strong>「为什么这条视频会火 / 不火」</strong>，最终映射为可执行的运营建议。
        </p>
        <div class="hero-meta">
          <span>毕业设计作品</span>
          <span>智能媒体工程学院</span>
          <span>技术栈：Vue 3 + Spring Boot + Python</span>
        </div>
      </div>
      <div class="hero-right">
        <div class="hero-stat">
          <b>36,381</b>
          <span>训练样本</span>
        </div>
        <div class="hero-stat">
          <b>0.818</b>
          <span>LightGBM R²(log)</span>
        </div>
        <div class="hero-stat">
          <b>89.5%</b>
          <span>90% 区间实测覆盖</span>
        </div>
        <div class="hero-stat">
          <b>+9.46pp</b>
          <span>特征维度增益</span>
        </div>
        <div class="hero-stat">
          <b>17</b>
          <span>类可复现实验</span>
        </div>
        <div class="hero-stat">
          <b>34 ms</b>
          <span>预测响应（常驻服务）</span>
        </div>
      </div>
    </section>

    <!-- ============ 要解决的问题 ============ -->
    <el-card shadow="never" class="block-card">
      <div class="section-title">为什么做这个系统</div>
      <div class="problem-grid">
        <div class="problem-item">
          <div class="problem-idx">01</div>
          <div class="problem-title">经验判断主观、滞后、无法规模化</div>
          <p>内容创作者与平台运营方需要在视频发布早期判断其能否「火」，但人工经验判断难以覆盖海量内容，也无法给出量化依据。</p>
        </div>
        <div class="problem-item">
          <div class="problem-idx">02</div>
          <div class="problem-title">「黑盒模型」无法指导内容改进</div>
          <p>即使模型能给出一个预测数值，业务方也无法据此改进内容。本项目引入可解释机器学习，把预测结果拆解到具体特征上。</p>
        </div>
        <div class="problem-item">
          <div class="problem-idx">03</div>
          <div class="problem-title">预测结果与业务决策之间存在断层</div>
          <p>现有公开研究多停留在「播放量预测」，较少把预测、分级、归因与运营建议整合进同一个可交付系统。</p>
        </div>
      </div>
    </el-card>

    <!-- ============ 四大功能模块 ============ -->
    <div class="section-title">系统四大功能模块</div>
    <div class="module-grid">
      <div v-for="m in modules" :key="m.title" class="module-card" :class="'tone-' + m.tone">
        <div class="module-head">
          <div class="module-icon"><svg-icon :icon-class="m.icon" /></div>
          <span class="module-no">{{ m.no }}</span>
        </div>
        <div class="module-title">{{ m.title }}</div>
        <div class="module-label">{{ m.label }}</div>
        <p class="module-desc">{{ m.desc }}</p>
        <ul class="module-points">
          <li v-for="p in m.points" :key="p">{{ p }}</li>
        </ul>
      </div>
    </div>

    <!-- ============ 与同类工作的能力对照 ============ -->
    <div class="section-title">与同类工作的能力对照</div>
    <div class="compare-wrap">
      <table class="compare-table">
        <thead>
          <tr>
            <th class="col-cap">能力</th>
            <th class="col-us">本系统</th>
            <th>内容驱动型<br />热度预测研究</th>
            <th>传统 BI /<br />数据大屏类</th>
            <th>开源可解释<br />平台</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in compareRows" :key="row.name">
            <td class="col-cap">{{ row.name }}</td>
            <td class="col-us">
              <span class="mark" :class="'m-' + row.us">{{ marks[row.us] }}</span>
              <span v-if="row.usNote" class="mark-note">{{ row.usNote }}</span>
            </td>
            <td><span class="mark" :class="'m-' + row.a">{{ marks[row.a] }}</span></td>
            <td><span class="mark" :class="'m-' + row.b">{{ marks[row.b] }}</span></td>
            <td><span class="mark" :class="'m-' + row.c">{{ marks[row.c] }}</span></td>
          </tr>
        </tbody>
      </table>
      <p class="compare-note">
        说明：本表只比较<b>能力有无</b>，不比较数值——各工作的数据规模、模态与评价口径差异极大，
        指标不可直接横向比较（详见技术方案第 2.1 节）。同类研究指 SnapUGC（arXiv:2410.00289）、
        arXiv:2501.01422 等内容驱动型短视频流行度预测工作；开源可解释平台指 shapash、MLflow 等。
      </p>
    </div>

    <!-- ============ 数据集与特征 / 实验结果 ============ -->
    <el-row :gutter="16">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="block-card">
          <div class="section-title">数据集与特征体系</div>
          <el-descriptions :column="1" border size="small" class="data-desc">
            <el-descriptions-item label="数据集">Kaggle 公开数据集 chaoqunx/douyin-video-datasets（Apache-2.0）</el-descriptions-item>
            <el-descriptions-item label="规模">45,476 行 × 9 列，零缺失值；时间跨度 2025-09-01 ~ 2025-12-26</el-descriptions-item>
            <el-descriptions-item label="热度定义">热度 = 播放量 + 3×点赞 + 5×评论 + 8×转发（加权互动量）</el-descriptions-item>
            <el-descriptions-item label="防数据泄漏">播放/点赞/评论/转发/收藏量是热度目标的组成部分，<b>不作为特征</b>，仅使用发布时可得信息</el-descriptions-item>
          </el-descriptions>
          <el-table :data="features" size="small" class="feature-table">
            <el-table-column prop="name" label="特征" width="170" />
            <el-table-column prop="type" label="类型" width="110" />
            <el-table-column prop="desc" label="说明" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="block-card">
          <div class="section-title">多模型对照实验结果（20% 测试集）</div>
          <el-table :data="models" size="small" class="feature-table">
            <el-table-column prop="name" label="模型" width="130" />
            <el-table-column label="RMSE(log)" width="110">
              <template #default="{ row }">{{ row.rmse.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="MAE(log)" width="100">
              <template #default="{ row }">{{ row.mae.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="R²(log)" min-width="150">
              <template #default="{ row }">
                <div class="r2-cell">
                  <el-progress :percentage="Math.round(row.r2 * 100)" :stroke-width="10" :show-text="false" />
                  <span :class="row.best ? 'r2-best' : 'r2-num'">{{ row.r2.toFixed(4) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="R²(原始)" width="100">
              <template #default="{ row }">{{ row.r2raw.toFixed(4) }}</template>
            </el-table-column>
          </el-table>
          <el-alert type="success" :closable="false" show-icon class="conclusion">
            <template #title>
              LightGBM 在 log 空间指标最优，选型成立。原始热度空间 R² 偏低源于热度强重尾（少数爆款主导方差），
              论文中据此讨论「分位数误差比均值误差更能反映业务可用性」。
            </template>
          </el-alert>
        </el-card>
      </el-col>
    </el-row>

    <!-- ============ 能力全景 ============ -->
    <el-card shadow="never" class="block-card">
      <div class="section-title">能力全景：三端协同 · 六类能力</div>
      <el-table :data="capabilities" size="small" class="cap-table">
        <el-table-column prop="layer" label="层次" width="130" />
        <el-table-column prop="stack" label="技术栈" width="220" />
        <el-table-column prop="ability" label="关键能力" min-width="360" />
        <el-table-column prop="output" label="可交付产物" min-width="230" />
      </el-table>
      <div class="cross-grid">
        <div v-for="c in crossCutting" :key="c.title" class="cross-card">
          <div class="cross-title">{{ c.title }}</div>
          <div class="cross-desc">{{ c.desc }}</div>
        </div>
      </div>
    </el-card>

    <!-- ============ 结论如何被证明 ============ -->
    <div class="section-title">结论如何被证明：三步递进的可信度论证</div>
    <div class="proof-grid">
      <div v-for="p in proofs" :key="p.no" class="proof-card">
        <div class="proof-no">{{ p.no }}</div>
        <div class="proof-title">{{ p.title }}</div>
        <div class="proof-question">{{ p.question }}</div>
        <ul class="proof-points">
          <li v-for="t in p.points" :key="t.k">
            <b>{{ t.k }}</b>
            <span>{{ t.v }}</span>
          </li>
        </ul>
        <div class="proof-verdict">{{ p.verdict }}</div>
        <router-link to="/evaluation/index">
          <el-button link type="primary" size="small">在实验中心运行该实验 ›</el-button>
        </router-link>
      </div>
    </div>

    <!-- ============ 系统架构 ============ -->
    <el-card shadow="never" class="block-card">
      <div class="section-title">系统架构（三端协同）</div>
      <div class="arch">
        <div class="arch-box tone-front">
          <div class="arch-title">前端展示层</div>
          <div class="arch-tech">Vue 3 · Element Plus · ECharts</div>
          <ul>
            <li>预测 / 归因 / 分级交互页面</li>
            <li>图表可视化与报告导出</li>
          </ul>
        </div>
        <div class="arch-arrow">
          <span>HTTP / JSON</span>
          <div class="line" />
        </div>
        <div class="arch-box tone-back">
          <div class="arch-title">Java 服务层</div>
          <div class="arch-tech">Spring Boot · Security · MyBatis-Plus · MySQL</div>
          <ul>
            <li>REST API 与登录鉴权</li>
            <li>ProcessBuilder 调用算法引擎、静态图挂载</li>
          </ul>
        </div>
        <div class="arch-arrow">
          <span>CLI 单行 JSON</span>
          <div class="line" />
        </div>
        <div class="arch-box tone-algo">
          <div class="arch-title">Python 算法引擎</div>
          <div class="arch-tech">LightGBM · SHAP · scikit-learn · pandas</div>
          <ul>
            <li>preprocess / predict_api / grade_cluster / shap_analysis</li>
            <li>模型缓存，首次训练后秒级加载</li>
          </ul>
        </div>
      </div>
    </el-card>

    <!-- ============ 创新点 ============ -->
    <el-card shadow="never" class="block-card">
      <div class="section-title">项目创新点</div>
      <div class="innov-grid">
        <div v-for="(it, i) in innovations" :key="i" class="innov-item">
          <div class="innov-no">{{ i + 1 }}</div>
          <div>
            <div class="innov-title">{{ it.title }}</div>
            <p>{{ it.desc }}</p>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
export default {
  name: 'AboutIndex',
  data () {
    return {
      modules: [
        {
          no: 'M1', title: '热度预测', label: '回归任务 · LightGBM 为核心', icon: 'chart', tone: 'indigo',
          desc: '以发布时先验特征预测视频后续热度，并做 6 模型横向对照实验。',
          points: ['单条预测 + 批量预测（≤500 条/次）', '预测历史留痕，支持分页回溯', '模型指标与体积可视化对比']
        },
        {
          no: 'M2', title: '热度分级', label: '分类任务 · K-Means + 分类器', icon: 'star', tone: 'violet',
          desc: '对热度做 K-Means 聚类得到「低 / 中 / 高」等级与阈值，再训练分类模型预测等级。',
          points: ['阈值：低 < 684 ｜ 中 684~15661 ｜ 高 ≥ 15661', '轮廓系数 0.664，等级分布可解释', 'LightGBM / 随机森林 / 逻辑回归 分类对照']
        },
        {
          no: 'M3', title: '归因分析', label: '可解释性 · SHAP（核心创新）', icon: 'eye', tone: 'blue',
          desc: '把预测结果拆解到每个特征，回答「哪些特征、以多大贡献驱动了这条视频的热度」。',
          points: ['全局重要性 + SHAP 汇总图（beeswarm）', '单样本贡献瀑布图 + Top-K 明细', '部分依赖图（PDP）找最优取值区间']
        },
        {
          no: 'M4', title: '运营决策支持', label: '归因 → 建议 的闭环', icon: 'skill', tone: 'green',
          desc: '依据输入特征与 SHAP 贡献方向，自动生成可执行的运营建议，实现「归因 → 决策」闭环。',
          points: ['粉丝基数偏低 → 账号导流 / 联动', '凌晨发布 → 迁移至晚间高峰', '主要拖累特征 → 优先改善项']
        }
      ],
      capabilities: [
        {
          layer: '前端展示层',
          stack: 'Vue 3 · Element Plus · ECharts',
          ability: '预测 / 归因 / 分级交互页、数据大屏、实验中心（17 类实验分组运行 + 结论卡）、模型治理页',
          output: '交互式分析界面、图表、自包含 HTML 审计报告'
        },
        {
          layer: 'Java 服务层',
          stack: 'Spring Boot · Security · MyBatis-Plus · Redis · Undertow',
          ability: 'REST API 与登录鉴权、分钟级实验异步任务调度（Redis 状态 + 轮询）、令牌桶限流、traceId 贯穿',
          output: '统一响应契约、可观测接口（/actuator/prometheus）'
        },
        {
          layer: '算法引擎层',
          stack: 'Python · LightGBM · SHAP · scikit-learn',
          ability: '六模型回归对照、SHAP 四维归因、保形预测区间、两阶段预测、解释质量三指标、稳健性三重检验',
          output: '可复现实验脚本、图表与 JSON 结论产物'
        }
      ],
      crossCutting: [
        { title: '数据治理', desc: '4 平台数据统一归一化 + 8 项质量断言（schema / 缺失率 / 非负 / 重复率 / 类别覆盖 / PSI / 时间区间），PASS-WARN-FAIL 三态，不达标可阻断建模' },
        { title: '模型治理', desc: '模型注册表（版本 + production/staging/archived 阶段，支持切换与回滚）+ 影子模式（候选模型并行打分，实测 lgbm vs rf 平均偏差 29.5%）' },
        { title: '工程保障', desc: '常驻推理服务（890ms → 34ms，30 秒熔断自动降级回 CLI）+ Prometheus 指标 + 16 项自动化测试 + CI 流水线' },
        { title: '实验治理', desc: '每次实验自动记入台账（参数 / 耗时 / traceId / 结果），失败也记账，可回看任意历史实验并两条对比' }
      ],
      proofs: [
        {
          no: 'P1',
          title: '区间可信吗',
          question: '给出的预测区间，凭什么相信它能覆盖真实值？',
          points: [
            { k: '保形预测实测覆盖', v: '89.5%（名义 90%，偏差 0.5pp）' },
            { k: '分位数回归对照', v: '仅 76.4%，且置信水平越低欠覆盖越严重' },
            { k: '条件覆盖（Mondrian）', v: '高热度档 69.1% → 80.8%' }
          ],
          verdict: '结论：区间从「事后检验覆盖率」升级为「有限样本覆盖保证」。'
        },
        {
          no: 'P2',
          title: '归因可信吗',
          question: 'SHAP 说粉丝数最重要，凭什么相信这个排序？',
          points: [
            { k: '紧凑性 k80', v: '1 个特征即可解释 80% 的平均绝对贡献' },
            { k: '一致性 Kendall τ', v: '0.81（SHAP vs 增益重要性）' },
            { k: '稳定性 Jaccard', v: '1.000（3 次 bootstrap 重训 Top-3 集合一致）' }
          ],
          verdict: '结论：解释结论在数据扰动下可复现；且只有首位特征在三种度量下收敛，其余特征接近噪声——这一点如实呈现。'
        },
        {
          no: 'P3',
          title: '建议可信吗',
          question: '「改到 16 点能涨 48%」这种建议，是模型的幻觉吗？',
          points: [
            { k: '安慰剂维度', v: '弱维度增益 0.0%，程序未凭空造出收益（PASS）' },
            { k: '子集重估', v: '小时增益 6.2%~118.9%，CV = 0.71（WARN）' },
            { k: '跨模型替换', v: '最优时点一致，但最优类别不一致（WARN）' }
          ],
          verdict: '结论：反事实建议只作「方向 + 区间」参考。主动暴露并下调自己的结论强度，是本课题的方法论特点。'
        }
      ],
      // 与同类工作的能力对照：只比"有无"，不比数值（口径差异过大，数值不可横向比较）
    marks: {
      yes: '✓',
      part: '部分',
      no: '—'
    },
    compareRows: [
      { name: '预测 + 分级 + 归因 + 建议一体化', us: 'yes', usNote: '本系统', a: 'part', b: 'no', c: 'no' },
      { name: '不确定性量化（带覆盖保证的区间）', us: 'yes', usNote: '保形 89.5%', a: 'no', b: 'no', c: 'no' },
      { name: '解释可信度评估（紧凑性/一致性/稳定性）', us: 'yes', usNote: '三指标', a: 'no', b: 'no', c: 'part' },
      { name: '结论稳健性检验（安慰剂/重估/跨模型）', us: 'yes', a: 'no', b: 'no', c: 'no' },
      { name: '数据质量门禁与漂移监控', us: 'yes', usNote: '8 断言 + PSI', a: 'no', b: 'part', c: 'no' },
      { name: '模型版本治理与影子验证', us: 'yes', a: 'no', b: 'no', c: 'yes' },
      { name: '实验台账与结论可复现', us: 'yes', usNote: '17 类实验', a: 'part', b: 'no', c: 'yes' }
    ],
    features: [
        { name: 'video_category', type: '类别特征', desc: '视频类别（14 类：搞笑 / 美食 / 音乐 …）' },
        { name: 'hour_bucket', type: '类别特征', desc: '发布时段（凌晨 / 上午 / 下午 / 晚间）' },
        { name: 'author_fans_log', type: '数值特征', desc: '作者粉丝数 log1p 变换（缓解长尾）' },
        { name: 'publish_hour', type: '数值特征', desc: '发布小时（0-23）' },
        { name: 'publish_weekday', type: '数值特征', desc: '发布星期（0-6）' },
        { name: 'publish_month', type: '数值特征', desc: '发布月份（1-12）' },
        { name: 'is_weekend', type: '数值特征', desc: '是否周末发布' }
      ],
      models: [
        { name: 'LightGBM', rmse: 0.9778, mae: 0.6523, r2: 0.8182, r2raw: 0.1957, best: true },
        { name: 'XGBoost', rmse: 0.9835, mae: 0.6591, r2: 0.8161, r2raw: 0.1802 },
        { name: '随机森林', rmse: 0.9863, mae: 0.6622, r2: 0.8151, r2raw: 0.3718 },
        { name: '线性回归', rmse: 1.0851, mae: 0.8143, r2: 0.7762, r2raw: 0.1052 },
        { name: 'K 近邻', rmse: 1.0996, mae: 0.7499, r2: 0.7701, r2raw: 0.2421 },
        { name: '决策树', rmse: 1.3868, mae: 0.9319, r2: 0.6344, r2raw: -0.1493 }
      ],
      innovations: [
        { title: '预测 + 分级 + 归因 + 运营建议一体化', desc: '区别于仅做预测的现有研究，同一系统内既给预测值、又给等级，再给可解释原因与改进建议。' },
        { title: 'SHAP 在短视频热度场景的工程化落地', desc: '将博弈论解释方法封装为可调用的 CLI 与前端可视化模块，覆盖全局 / 单样本 / 依赖关系三维度。' },
        { title: '防数据泄漏的特征体系设计', desc: '明确排除与目标共线的互动量字段，保证「预测」在业务上真实有效，而非换个方式还原目标。' },
        { title: '可复用的企业级三端工程脚手架', desc: 'Vue + Spring Boot + Python 算法引擎，含登录鉴权、模型缓存与静态图挂载，保证系统可演示、可交付。' }
      ]
    }
  }
}
</script>

<style lang="scss" scoped>
.about {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ---------------- 头部 ---------------- */
.about-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  flex-wrap: wrap;
  padding: 28px 32px;
  border-radius: 18px;
  background: linear-gradient(120deg, #eef0fe 0%, #f7f2ff 55%, #fdf2ff 100%);
  border: 1px solid #e6e2fb;

  .hero-left {
    min-width: 320px;
    flex: 1;
  }

  .hero-tags {
    display: flex;
    gap: 8px;
    margin-bottom: 14px;

    .tag-tone {
      background: linear-gradient(135deg, #6366f1, #a855f7);
      border: none;
      font-weight: 600;
    }
    .tag-plain {
      color: #6b5bd2;
      border-color: #d8d2f7;
      background: rgba(255, 255, 255, .7);
    }
  }

  h1 {
    font-size: 24px;
    font-weight: 800;
    color: #1e293b;
    margin: 0 0 6px;
    letter-spacing: .3px;
    line-height: 1.35;
  }

  .hero-sub {
    font-size: 15px;
    color: #7c6bd6;
    font-weight: 600;
    margin: 0 0 14px;
  }

  .hero-desc {
    font-size: 13.5px;
    line-height: 1.9;
    color: #475569;
    margin: 0 0 16px;
    max-width: 720px;

    strong {
      color: #4f46e5;
      font-weight: 650;
    }
  }

  .hero-meta {
    display: flex;
    gap: 18px;
    flex-wrap: wrap;
    font-size: 12.5px;
    color: #94a3b8;
  }

  .hero-right {
    display: grid;
    grid-template-columns: repeat(3, minmax(104px, 1fr));
    gap: 12px;
    flex-shrink: 0;
  }

  .hero-stat {
    background: #fff;
    border: 1px solid #e9e6fb;
    border-radius: 14px;
    padding: 16px 20px;
    text-align: center;
    min-width: 108px;
    box-shadow: 0 6px 18px rgba(99, 102, 241, .08);

    b {
      display: block;
      font-size: 22px;
      font-weight: 800;
      color: #4f46e5;
      letter-spacing: .4px;
    }
    span {
      display: block;
      font-size: 11.5px;
      color: #94a3b8;
      margin-top: 5px;
    }
  }
}

.block-card {
  margin-bottom: 0;
}

/* ---------------- 问题 ---------------- */
.problem-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.problem-item {
  position: relative;
  padding: 18px 18px 18px 20px;
  border-radius: 14px;
  background: #fafbfe;
  border: 1px solid #eef0f6;

  .problem-idx {
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 1px;
    color: #a5a9f0;
    margin-bottom: 6px;
  }
  .problem-title {
    font-size: 14px;
    font-weight: 650;
    color: #1e293b;
    margin-bottom: 8px;
  }
  p {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.8;
    color: #64748b;
  }
}

/* ---------------- 模块 ---------------- */
.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(255px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.module-card {
  background: #fff;
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  box-shadow: var(--app-shadow-1);
  padding: 20px;
  transition: box-shadow .22s ease, transform .22s ease;

  &:hover {
    box-shadow: var(--app-shadow-2);
    transform: translateY(-2px);
  }

  .module-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }

  .module-icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 20px;
  }

  .module-no {
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 1px;
    color: #cbd2e0;
  }

  .module-title {
    font-size: 16px;
    font-weight: 750;
    color: #1e293b;
  }

  .module-label {
    font-size: 12px;
    color: #8b93f0;
    font-weight: 600;
    margin: 5px 0 10px;
  }

  .module-desc {
    font-size: 12.5px;
    line-height: 1.8;
    color: #64748b;
    margin: 0 0 12px;
  }

  .module-points {
    margin: 0;
    padding-left: 0;
    list-style: none;

    li {
      position: relative;
      padding-left: 16px;
      font-size: 12px;
      line-height: 1.9;
      color: #475569;

      &::before {
        content: "";
        position: absolute;
        left: 3px;
        top: 9px;
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: #c3c6f8;
      }
    }
  }

  &.tone-indigo .module-icon { background: linear-gradient(135deg, #6366f1, #8b5cf6); box-shadow: 0 8px 18px rgba(99, 102, 241, .3); }
  &.tone-violet .module-icon { background: linear-gradient(135deg, #8b5cf6, #d946ef); box-shadow: 0 8px 18px rgba(139, 92, 246, .3); }
  &.tone-blue .module-icon { background: linear-gradient(135deg, #38bdf8, #6366f1); box-shadow: 0 8px 18px rgba(56, 189, 248, .3); }
  &.tone-green .module-icon { background: linear-gradient(135deg, #34d399, #10b981); box-shadow: 0 8px 18px rgba(16, 185, 129, .3); }
}

/* ---------------- 表格 ---------------- */
.data-desc {
  margin-bottom: 14px;
}

.feature-table {
  ::v-deep .el-table__cell {
    padding: 7px 0;
  }
}

.r2-cell {
  display: flex;
  align-items: center;
  gap: 8px;

  ::v-deep .el-progress {
    flex: 1;
    min-width: 60px;
  }

  .r2-best {
    font-weight: 700;
    color: #4f46e5;
  }
  .r2-num {
    color: #64748b;
  }
}

.conclusion {
  margin-top: 14px;

  ::v-deep .el-alert__title {
    font-size: 12.5px;
    line-height: 1.8;
  }
}

/* ---------------- 架构 ---------------- */
.arch {
  display: flex;
  align-items: stretch;
  gap: 0;
  flex-wrap: wrap;
}

.arch-box {
  flex: 1 1 240px;
  border-radius: 14px;
  padding: 18px;
  border: 1px solid #e9ecf5;
  background: #fafbfe;

  .arch-title {
    font-size: 14px;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 4px;
  }
  .arch-tech {
    font-size: 11.5px;
    color: #8b93f0;
    font-weight: 600;
    margin-bottom: 10px;
  }
  ul {
    margin: 0;
    padding-left: 16px;
    li {
      font-size: 12px;
      line-height: 1.85;
      color: #64748b;
    }
  }

  &.tone-front { border-top: 3px solid #6366f1; }
  &.tone-back { border-top: 3px solid #8b5cf6; }
  &.tone-algo { border-top: 3px solid #10b981; }
}

.arch-arrow {
  flex: 0 0 96px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;

  span {
    font-size: 11px;
    color: #a9b2c4;
    font-weight: 600;
  }
  .line {
    width: 62px;
    height: 2px;
    border-radius: 999px;
    background: linear-gradient(90deg, #c7cbf7, #a5a9f0);
    position: relative;

    &::after {
      content: "";
      position: absolute;
      right: -1px;
      top: -4px;
      border-left: 7px solid #a5a9f0;
      border-top: 5px solid transparent;
      border-bottom: 5px solid transparent;
    }
  }
}

/* ---------------- 创新点 ---------------- */
.innov-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.innov-item {
  display: flex;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 14px;
  background: #fafbfe;
  border: 1px solid #eef0f6;

  .innov-no {
    width: 26px;
    height: 26px;
    border-radius: 9px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 800;
    color: #fff;
    background: linear-gradient(135deg, #6366f1, #a855f7);
  }

  .innov-title {
    font-size: 13.5px;
    font-weight: 650;
    color: #1e293b;
    margin-bottom: 6px;
  }

  p {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.8;
    color: #64748b;
  }
}

@media (max-width: 900px) {
  .about-hero {
    padding: 22px;
  }
  .arch-arrow {
    flex: 1 1 100%;
    transform: rotate(90deg);
    padding: 8px 0;
  }
}

/* ============ 能力全景 ============ */
.cap-table {
  margin-bottom: 14px;
}

.cross-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
}

.cross-card {
  border: 1px solid #eceafc;
  border-radius: 10px;
  background: linear-gradient(160deg, #fafaff 0%, #ffffff 100%);
  padding: 12px 14px;
}

.cross-title {
  font-size: 13.5px;
  font-weight: 700;
  color: #4f46e5;
  margin-bottom: 6px;
}

.cross-desc {
  font-size: 12.5px;
  line-height: 1.8;
  color: #64748b;
}

/* ============ 结论如何被证明 ============ */
.proof-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.proof-card {
  border: 1px solid #e9e6fb;
  border-radius: 12px;
  background: #fff;
  padding: 16px 18px;
  box-shadow: 0 6px 18px rgba(99, 102, 241, .06);
}

.proof-no {
  display: inline-block;
  font-size: 12px;
  font-weight: 800;
  color: #fff;
  background: #4f46e5;
  border-radius: 5px;
  padding: 2px 9px;
  letter-spacing: .06em;
  margin-bottom: 9px;
}

.proof-title {
  font-size: 16px;
  font-weight: 800;
  color: #1e293b;
  margin-bottom: 4px;
}

.proof-question {
  font-size: 12.5px;
  color: #94a3b8;
  margin-bottom: 10px;
}

.proof-points {
  list-style: none;
  margin: 0 0 10px;
  padding: 0;
}

.proof-points li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12.5px;
  line-height: 2;
  border-bottom: 1px dashed #f0f1f8;
}

.proof-points b {
  color: #64748b;
  font-weight: 600;
  flex-shrink: 0;
}

.proof-points span {
  color: #1e293b;
  font-weight: 700;
  text-align: right;
}

.proof-verdict {
  font-size: 12.5px;
  line-height: 1.8;
  color: #4f46e5;
  background: #f6f4ff;
  border-radius: 8px;
  padding: 9px 11px;
  margin-bottom: 6px;
}
/* ============ 与同类工作的能力对照 ============ */
.compare-wrap {
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  background: var(--app-card);
  padding: 14px 16px 12px;
  margin-bottom: 20px;
  overflow-x: auto;
}

.compare-table {
  width: 100%;
  min-width: 880px;
  border-collapse: collapse;
  font-size: 13px;

  th,
  td {
    border-bottom: 1px solid var(--app-border);
    padding: 9px 12px;
    text-align: center;
    color: var(--app-text-2);
  }

  thead th {
    background: #f7f8fc;
    color: var(--app-text);
    font-weight: 600;
    line-height: 1.5;
  }

  tbody tr:last-child td {
    border-bottom: none;
  }

  .col-cap {
    width: 252px;
    text-align: left;
    color: var(--app-text);
    font-weight: 600;
  }

  .col-us {
    width: 128px;
    background: #f6f4ff;
  }
}

.mark {
  display: inline-block;
  min-width: 24px;
  font-weight: 700;
  white-space: nowrap;
}

.m-yes {
  color: #10b981;
}

.m-part {
  color: #f59e0b;
}

.m-no {
  color: #cbd5e1;
}

.mark-note {
  display: block;
  margin-top: 3px;
  font-size: 11px;
  color: var(--app-text-3);
  font-weight: 400;
}

.compare-note {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.85;
  color: var(--app-text-3);

  b {
    color: var(--app-text-2);
  }
}</style>
