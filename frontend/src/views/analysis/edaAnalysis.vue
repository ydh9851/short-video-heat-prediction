<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">数据探索分析</div>
        <div class="page-desc">
          Python EDA 生成的统计图表，覆盖热度分布、类别特征、作者特征、时间特征与相关性五个维度；
          重跑算法脚本后刷新即可看到最新结果。
        </div>
      </div>
      <div class="page-head-actions">
        <el-tag type="info" effect="plain">{{ images.length }} 张图表</el-tag>
      </div>
    </div>

    <!-- 分组筛选 -->
    <div class="filter-bar">
      <div
        v-for="g in groupTabs"
        :key="g.key"
        class="filter-pill"
        :class="{ active: group === g.key }"
        @click="group = g.key"
      >
        {{ g.label }}
        <span class="pill-count">{{ g.count }}</span>
      </div>
    </div>

    <!-- 图表库 -->
    <el-row :gutter="16">
      <el-col
        v-for="(item, idx) in filteredImages"
        :key="item.name"
        :xs="24" :sm="12" :md="12" :lg="8"
        class="eda-col"
      >
        <el-card :body-style="{ padding: '0' }" shadow="never" class="eda-card">
          <div class="eda-media">
            <el-image
              :src="'/eda/' + item.name"
              :preview-src-list="['/eda/' + item.name]"
              fit="contain"
              class="eda-img"
              lazy>
              <template #error>
                <div class="eda-img-error"><span>图片缺失</span></div>
              </template>
            </el-image>
            <span class="eda-group-tag">{{ item.group }}</span>
          </div>
          <div class="eda-body">
            <div class="eda-title">{{ item.title }}</div>
            <div class="eda-desc">{{ item.desc }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!filteredImages.length" description="该分组暂无可视化图表，切换到其他分组看看" :image-size="90" />
  </div>
</template>

<script>
export default {
  name: 'EdaAnalysis',
  data () {
    return {
      group: 'all',
      // 每张图：脚本生成的 PNG 文件名 + 所属分组 + 中文标题/说明。
      // 由 algorithm/FeatureEDA/eda.py 生成，新增图时在此追加即可。
      images: [
        { name: 'fig01_heat_distribution.png', group: '热度分布', title: '热度分布（原值 vs log1p）', desc: '热度=播放+3×点赞+5×评论+8×转发。原值高度右偏（重尾），log1p 后近似正态，故建模以 log1p 为目标。' },
        { name: 'fig13_grade_distribution.png', group: '热度分布', title: '热度等级分布', desc: '按 K-Means 分级阈值（684 / 15661）划分的低、中、高热度样本分布。' },
        { name: 'fig02_category_count.png', group: '类别分析', title: '各视频类别样本数量', desc: '14 个视频类别的样本量分布：搞笑、美食、音乐为数量最多的类目。' },
        { name: 'fig03_category_avg_heat.png', group: '类别分析', title: '各视频类别平均热度', desc: '不同类目的平均热度差异明显，可用于指导选题方向。' },
        { name: 'fig04_category_box.png', group: '类别分析', title: '各类别热度分布（箱线图）', desc: 'log 空间下各类别热度分布对比，观察类目内的离散度与中位水平。' },
        { name: 'fig05_fans_distribution.png', group: '作者特征', title: '作者粉丝数分布', desc: '粉丝数同样呈长尾分布，做 log1p 变换后用于建模。' },
        { name: 'fig06_fans_vs_heat.png', group: '作者特征', title: '作者粉丝数 与 热度 的关系', desc: 'log-log 散点：粉丝数与热度整体正相关，是预测的最强特征。' },
        { name: 'fig07_hour_avg_heat.png', group: '时间特征', title: '发布小时 与 平均热度', desc: '按发布小时统计平均热度，观察是否存在发布时段效应。' },
        { name: 'fig08_weekday_avg_heat.png', group: '时间特征', title: '发布星期 与 平均热度', desc: '工作日与周末发布的平均热度差异。' },
        { name: 'fig09_month_avg_heat.png', group: '时间特征', title: '发布月份 与 平均热度', desc: '按月份统计平均热度，观察季节 / 档期效应。' },
        { name: 'fig10_bucket_avg_heat.png', group: '时间特征', title: '发布时段 与 平均热度', desc: '凌晨 / 上午 / 下午 / 晚间四个时段的平均热度对比。' },
        { name: 'fig11_correlation.png', group: '相关性', title: '特征相关性热力图', desc: '各先验特征与热度的相关系数：作者粉丝数与热度相关性最强。' },
        { name: 'fig12_interaction_ratio.png', group: '相关性', title: '互动行为相对播放量比率', desc: '点赞 / 评论 / 转发 / 收藏相对播放量的中位比率，反映互动结构。' }
      ]
    }
  },
  computed: {
    filteredImages () {
      if (this.group === 'all') return this.images
      return this.images.filter(i => i.group === this.group)
    },
    groupTabs () {
      const counts = {}
      this.images.forEach(i => { counts[i.group] = (counts[i.group] || 0) + 1 })
      const order = ['热度分布', '类别分析', '作者特征', '时间特征', '相关性']
      const tabs = [{ key: 'all', label: '全部', count: this.images.length }]
      order.forEach(k => {
        if (counts[k]) tabs.push({ key: k, label: k, count: counts[k] })
      })
      return tabs
    }
  }
}
</script>

<style lang="scss" scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 15px;
  border-radius: 999px;
  font-size: 13px;
  color: #5b6478;
  background: #fff;
  border: 1px solid #e6e9f0;
  cursor: pointer;
  transition: all .18s ease;
  user-select: none;

  &:hover {
    color: #4f52c1;
    border-color: #cdcffa;
    background: #f7f8ff;
  }

  &.active {
    color: #fff;
    border-color: transparent;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    box-shadow: 0 6px 16px rgba(99, 102, 241, .3);
  }

  .pill-count {
    font-size: 11.5px;
    padding: 1px 7px;
    border-radius: 999px;
    background: rgba(99, 102, 241, .1);
  }
  &.active .pill-count {
    background: rgba(255, 255, 255, .24);
  }
}

.eda-col {
  margin-bottom: 16px;
}

.eda-card {
  height: 100%;
  transition: box-shadow .22s ease, transform .22s ease;

  &:hover {
    box-shadow: var(--app-shadow-2) !important;
    transform: translateY(-2px);
  }
}

.eda-media {
  position: relative;
  padding: 12px 12px 0;
}

.eda-group-tag {
  position: absolute;
  top: 20px;
  left: 20px;
  font-size: 11px;
  color: #6b5bd2;
  background: rgba(246, 244, 255, .94);
  border: 1px solid #e2ddfa;
  border-radius: 999px;
  padding: 2px 10px;
}

.eda-img {
  width: 100%;
  height: 240px;
  border: 1px solid #eef0f6;
  border-radius: 10px;
  background: #fafbfe;
}

.eda-img-error {
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 13px;
}

.eda-body {
  padding: 12px 16px 16px;
}

.eda-title {
  font-size: 14px;
  font-weight: 650;
  color: #1e293b;
}

.eda-desc {
  margin-top: 6px;
  font-size: 12.5px;
  line-height: 1.7;
  color: #94a3b8;
}
</style>
