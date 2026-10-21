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
          <span>作者：俞丁豪（Z202508090308）</span>
          <span>指导教师：吴颖</span>
          <span>23 计科（专转本）3 班</span>
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
          <b>14</b>
          <span>视频类别</span>
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
    display: flex;
    gap: 14px;
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
</style>
