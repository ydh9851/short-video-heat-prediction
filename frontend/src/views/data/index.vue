<template>
  <div class="app-container">
    <el-alert type="success" :closable="false" show-icon style="margin-bottom:14px"
              title="数据管理：规范化数据集由 algorithm/FeatureEDA/preprocess.py 产出（data/processed/train_clean.csv），包含缺失值处理、类别编码与特征工程结果。此处提供总览统计与样本预览。"/>

    <!-- 总览卡片 -->
    <el-row :gutter="16" class="stat-row" v-loading="loadingOverview">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div class="stat"><div class="stat-val">{{ fmtInt(ov.total) }}</div><div class="stat-lab">样本总量</div></div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div class="stat"><div class="stat-val">{{ ov.categoryCount }}</div><div class="stat-lab">视频类别数</div></div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover"><div class="stat"><div class="stat-val">{{ fmtInt(ov.heat && ov.heat.median) }}</div><div class="stat-lab">热度中位数</div></div></el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover">
          <div class="stat">
            <div class="stat-val date">{{ (ov.publishRange && ov.publishRange.start || '').slice(0,10) }}</div>
            <div class="stat-lab">起始发布日期</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 热度分布与分级 -->
      <el-col :xs="24" :md="12" style="margin-bottom:16px">
        <el-card shadow="never">
          <div class="sec-title">热度分布（加权互动量）</div>
          <el-descriptions :column="2" border size="small" v-if="ov.heat">
            <el-descriptions-item label="最小">{{ fmtInt(ov.heat.min) }}</el-descriptions-item>
            <el-descriptions-item label="均值">{{ fmtInt(ov.heat.mean) }}</el-descriptions-item>
            <el-descriptions-item label="P25">{{ fmtInt(ov.heat.q1) }}</el-descriptions-item>
            <el-descriptions-item label="中位数">{{ fmtInt(ov.heat.median) }}</el-descriptions-item>
            <el-descriptions-item label="P75">{{ fmtInt(ov.heat.q3) }}</el-descriptions-item>
            <el-descriptions-item label="最大">{{ fmtInt(ov.heat.max) }}</el-descriptions-item>
          </el-descriptions>
          <div class="sec-title" style="margin-top:16px">热度等级分布</div>
          <el-table :data="ov.gradeDistribution || []" size="small" stripe>
            <el-table-column prop="grade" label="等级" width="120"/>
            <el-table-column prop="count" label="样本数">
              <template #default="scope">
                <el-progress :percentage="gradePct(scope.row.count)" :stroke-width="14"
                             :format="() => fmtInt(scope.row.count)"/>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 类别分布 -->
      <el-col :xs="24" :md="12" style="margin-bottom:16px">
        <el-card shadow="never">
          <div class="sec-title">视频类别分布</div>
          <el-table :data="ov.categories || []" size="small" stripe max-height="360">
            <el-table-column type="index" label="#" width="60"/>
            <el-table-column prop="name" label="类别" width="110"/>
            <el-table-column label="样本数">
              <template #default="scope">
                <el-progress :percentage="catPct(scope.row.count)" :stroke-width="14"
                             :format="() => fmtInt(scope.row.count)"/>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 样本预览 -->
    <el-card shadow="never">
      <div class="card-header">
        <div class="sec-title">样本预览（共 {{ sampleTotal }} 条）</div>
        <div>
          <el-select v-model="category" size="small" style="width:150px;margin-right:10px" @change="onFilter">
            <el-option label="全部类别" value=""/>
            <el-option v-for="c in (ov.categories || [])" :key="c.name" :label="c.name" :value="c.name"/>
          </el-select>
          <el-button size="small" @click="loadSamples">刷新</el-button>
        </div>
      </div>
      <el-table :data="samples" size="small" stripe v-loading="loadingSamples">
        <el-table-column prop="videoId" label="视频ID" width="180"/>
        <el-table-column prop="videoCategory" label="类别" width="90"/>
        <el-table-column label="作者粉丝数" width="120">
          <template #default="scope">{{ fmtInt(scope.row.authorFans) }}</template>
        </el-table-column>
        <el-table-column prop="publishTime" label="发布时间" width="160"/>
        <el-table-column label="播放量" width="110">
          <template #default="scope">{{ fmtInt(scope.row.playCnt) }}</template>
        </el-table-column>
        <el-table-column label="点赞" width="90">
          <template #default="scope">{{ fmtInt(scope.row.likeCnt) }}</template>
        </el-table-column>
        <el-table-column label="评论" width="80">
          <template #default="scope">{{ fmtInt(scope.row.commentCnt) }}</template>
        </el-table-column>
        <el-table-column label="转发" width="80">
          <template #default="scope">{{ fmtInt(scope.row.shareCnt) }}</template>
        </el-table-column>
        <el-table-column label="热度" min-width="120">
          <template #default="scope"><b>{{ fmtInt(scope.row.heat) }}</b></template>
        </el-table-column>
        <el-table-column label="等级" width="100">
          <template #default="scope">
            <el-tag :type="gradeTag(scope.row.grade)" size="small">{{ scope.row.grade }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        style="margin-top:12px;text-align:right"
        background
        layout="total, prev, pager, next"
        :total="sampleTotal"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPageChange"/>
    </el-card>
  </div>
</template>

<script>
import dataApi from '@/api/data'

export default {
  name: 'DataManage',
  data () {
    return {
      loadingOverview: false,
      loadingSamples: false,
      ov: {},
      samples: [],
      sampleTotal: 0,
      page: 1,
      pageSize: 20,
      category: ''
    }
  },
  created () {
    this.loadOverview()
    this.loadSamples()
  },
  methods: {
    loadOverview () {
      this.loadingOverview = true
      dataApi.overview().then(re => {
        this.ov = re.response || {}
        this.loadingOverview = false
      }).catch(() => { this.loadingOverview = false })
    },
    loadSamples () {
      this.loadingSamples = true
      dataApi.samples({ page: this.page, size: this.pageSize, category: this.category }).then(re => {
        const r = re.response || {}
        this.samples = r.list || []
        this.sampleTotal = r.total || 0
        this.loadingSamples = false
      }).catch(() => { this.loadingSamples = false })
    },
    onFilter () {
      this.page = 1
      this.loadSamples()
    },
    onPageChange (p) {
      this.page = p
      this.loadSamples()
    },
    catPct (v) {
      const max = (this.ov.categories && this.ov.categories.length) ? this.ov.categories[0].count : 0
      return max ? Math.round(v / max * 100) : 0
    },
    gradePct (v) {
      const g = this.ov.gradeDistribution || []
      const max = g.length ? Math.max(...g.map(x => x.count)) : 0
      return max ? Math.round(v / max * 100) : 0
    },
    fmtInt (v) {
      if (v == null || Number.isNaN(Number(v))) return '-'
      return Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })
    },
    gradeTag (g) {
      return { 低热度: 'info', 中热度: 'warning', 高热度: 'danger' }[g] || 'info'
    }
  }
}
</script>

<style scoped>
.stat-row {
  margin-bottom: 16px;
}
.stat {
  text-align: center;
  padding: 6px 0;
}
.stat-val {
  font-size: 26px;
  font-weight: 700;
  color: #409eff;
}
.stat-val.date {
  font-size: 20px;
}
.stat-lab {
  color: #909399;
  font-size: 13px;
  margin-top: 6px;
}
.sec-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
</style>
