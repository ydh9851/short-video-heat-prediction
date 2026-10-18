<template>
  <div class="app-container">
    <el-alert type="primary" :closable="false" show-icon style="margin-bottom:14px"
              title="数据探索分析（Python EDA）：由 algorithm/FeatureEDA/eda.py 生成 13 张统计图，覆盖热度分布、类别、作者粉丝数、发布时段等维度。数据源为 data/train.csv（抖音短视频数据集，45476 条），后端经 /eda/** 直接映射到 algorithm/FeatureEDA/figures 目录，重跑脚本后刷新页面即可看到最新图。"/>

    <el-row :gutter="16">
      <el-col :xs="24" :sm="12" :md="12" :lg="8" v-for="(item, idx) in images" :key="item.name" style="margin-bottom:16px">
        <el-card :body-style="{ padding: '12px' }" shadow="hover">
          <div class="eda-card">
            <el-image
              :src="'/eda/' + item.name"
              :preview-src-list="['/eda/' + item.name]"
              fit="contain"
              class="eda-img"
              lazy>
              <template #error>
                <div class="eda-img-error">
                  <span>图片缺失</span>
                </div>
              </template>
            </el-image>
            <div class="eda-title">{{ idx + 1 }}. {{ item.title }}</div>
            <div class="eda-desc">{{ item.desc }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
export default {
  name: 'EdaAnalysis',
  data () {
    return {
      // 每张图：脚本生成的 PNG 文件名 + 中文标题/说明。新增图时在此追加即可。
      // 由 algorithm/FeatureEDA/eda.py 生成
      images: [
        { name: 'fig01_heat_distribution.png', title: '热度分布（原值 vs log1p）', desc: '热度=播放+3×点赞+5×评论+8×转发。原值高度右偏（重尾），log1p 后近似正态，故建模以 log1p 为目标。' },
        { name: 'fig02_category_count.png', title: '各视频类别样本数量', desc: '14 个视频类别的样本量分布：搞笑、美食、音乐为数量最多的类目。' },
        { name: 'fig03_category_avg_heat.png', title: '各视频类别平均热度', desc: '不同类目的平均热度差异明显，可用于指导选题方向。' },
        { name: 'fig04_category_box.png', title: '各类别热度分布（箱线图）', desc: 'log 空间下各类别热度分布对比，观察类目内的离散度与中位水平。' },
        { name: 'fig05_fans_distribution.png', title: '作者粉丝数分布', desc: '粉丝数同样呈长尾分布，做 log1p 变换后用于建模。' },
        { name: 'fig06_fans_vs_heat.png', title: '作者粉丝数 与 热度 的关系', desc: 'log-log 散点：粉丝数与热度整体正相关，是预测的最强特征。' },
        { name: 'fig07_hour_avg_heat.png', title: '发布小时 与 平均热度', desc: '按发布小时统计平均热度，观察是否存在发布时段效应。' },
        { name: 'fig08_weekday_avg_heat.png', title: '发布星期 与 平均热度', desc: '工作日与周末发布的平均热度差异。' },
        { name: 'fig09_month_avg_heat.png', title: '发布月份 与 平均热度', desc: '按月份统计平均热度，观察季节/档期效应。' },
        { name: 'fig10_bucket_avg_heat.png', title: '发布时段 与 平均热度', desc: '凌晨/上午/下午/晚间四个时段的平均热度对比。' },
        { name: 'fig11_correlation.png', title: '特征相关性热力图', desc: '各先验特征与热度的相关系数：作者粉丝数与热度相关性最强。' },
        { name: 'fig12_interaction_ratio.png', title: '互动行为相对播放量比率', desc: '点赞/评论/转发/收藏相对播放量的中位比率，反映互动结构。' },
        { name: 'fig13_grade_distribution.png', title: '热度等级分布', desc: '按 K-Means 分级阈值（684 / 15661）划分的低、中、高热度样本分布。' }
      ]
    }
  }
}
</script>

<style scoped>
.eda-card {
  display: flex;
  flex-direction: column;
}
.eda-img {
  width: 100%;
  height: 260px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fafafa;
}
.eda-img-error {
  height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 14px;
}
.eda-title {
  margin-top: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}
.eda-desc {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: #909399;
}
</style>
