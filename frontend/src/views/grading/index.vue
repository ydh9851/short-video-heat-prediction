<template>
  <div class="app-container">
    <el-alert type="success" :closable="false" show-icon style="margin-bottom:14px"
              title="热度分级：先对热度（log1p 空间）做 K-Means 聚类得到「低 / 中 / 高」热度等级与分级阈值，再用与预测相同的先验特征训练分类模型，判断视频所属热度等级。"/>

    <el-card shadow="never" style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="聚类簇数 k">
          <el-radio-group v-model="k" @change="load">
            <el-radio-button :label="3">3 级</el-radio-button>
            <el-radio-button :label="4">4 级</el-radio-button>
            <el-radio-button :label="5">5 级</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="data">
          <el-tag type="info">轮廓系数：{{ fmt(data.silhouette) }}</el-tag>
        </el-form-item>
      </el-form>

      <div v-if="data" class="grade-cards">
        <el-card v-for="(n, i) in data.grade_names" :key="i" shadow="hover" class="grade-card">
          <div class="grade-name">{{ n }}</div>
          <div class="grade-range">{{ rangeText(i) }}</div>
          <div class="grade-count">{{ data.distribution[n].count }} 条</div>
          <div class="grade-mean">均值 {{ formatNum(data.distribution[n].mean) }}</div>
        </el-card>
      </div>
    </el-card>

    <div v-loading="loading">
      <el-row :gutter="16">
        <el-col :xs="24" :md="12" style="margin-bottom:16px">
          <el-card shadow="hover">
            <div class="fig-title">热度等级分布</div>
            <el-image :src="fig('grade_distribution.png')" :preview-src-list="[fig('grade_distribution.png')]"
                      fit="contain" class="fig-img" lazy/>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="12" style="margin-bottom:16px">
          <el-card shadow="hover">
            <div class="fig-title">分类混淆矩阵（LightGBM）</div>
            <el-image :src="fig('grade_confusion.png')" :preview-src-list="[fig('grade_confusion.png')]"
                      fit="contain" class="fig-img" lazy/>
          </el-card>
        </el-col>
      </el-row>

      <el-card v-if="data" shadow="never">
        <div class="fig-title">分级分类模型对照</div>
        <el-table :data="data.classifier_metrics" stripe size="small">
          <el-table-column type="index" label="#" width="60"/>
          <el-table-column prop="model" label="模型" min-width="160"/>
          <el-table-column label="准确率 Accuracy" min-width="180">
            <template #default="scope">
              <el-progress :percentage="Math.round(scope.row.accuracy * 100)" :stroke-width="14"
                           :format="() => (scope.row.accuracy * 100).toFixed(2) + '%'"/>
            </template>
          </el-table-column>
          <el-table-column label="宏平均 F1" min-width="140">
            <template #default="scope">{{ scope.row.macro_f1.toFixed(4) }}</template>
          </el-table-column>
          <el-table-column prop="model" label="说明" min-width="200">
            <template #default="scope">
              <span>{{ modelDesc(scope.row.model) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script>
import gradeApi from '@/api/grade'

export default {
  name: 'GradingIndex',
  data () {
    return {
      k: 3,
      loading: false,
      data: null
    }
  },
  created () {
    this.load()
  },
  methods: {
    fig (name) {
      return '/grading/' + name + '?t=' + Date.now()
    },
    load () {
      this.loading = true
      gradeApi.grade(this.k).then(re => {
        this.data = re.response || null
        this.loading = false
      }).catch(() => { this.loading = false })
    },
    rangeText (i) {
      if (!this.data) return ''
      const d = this.data
      if (i === 0) return '< ' + this.formatNum(d.thresholds[0])
      if (i === d.grade_names.length - 1) return '≥ ' + this.formatNum(d.thresholds[d.thresholds.length - 1])
      return this.formatNum(d.thresholds[i - 1]) + ' ~ ' + this.formatNum(d.thresholds[i])
    },
    modelDesc (m) {
      return { lgbm: 'LightGBM 分类器（梯度提升树）', rf: '随机森林分类器', lr: '逻辑回归（线性基线）' }[m] || m
    },
    fmt (v) {
      return v == null ? '-' : Number(v).toFixed(4)
    },
    formatNum (v) {
      if (v == null) return '-'
      return Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })
    }
  }
}
</script>

<style scoped>
.grade-cards {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.grade-card {
  flex: 1;
  min-width: 160px;
  text-align: center;
}
.grade-name {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
}
.grade-range {
  color: #909399;
  font-size: 13px;
  margin: 8px 0;
}
.grade-count {
  color: #409eff;
  font-size: 22px;
  font-weight: 700;
}
.grade-mean {
  color: #909399;
  font-size: 12px;
  margin-top: 6px;
}
.fig-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}
.fig-img {
  width: 100%;
  height: 300px;
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}
</style>
