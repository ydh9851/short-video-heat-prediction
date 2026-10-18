<template>
  <div class="app-container">
    <el-tabs v-model="tab" type="border-card" @tab-change="onTabChange">
      <!-- ==================== 单条预测 ==================== -->
      <el-tab-pane label="单条预测" name="single">
        <el-card shadow="never" class="predict-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">短视频热度预测（LightGBM）</span>
              <el-tag size="small" type="info">多模型对照：LightGBM / XGBoost / RandomForest / LinearRegression / KNN / DecisionTree</el-tag>
            </div>
          </template>

          <el-alert type="success" :closable="false" show-icon class="explain-tip"
                    title="输入视频发布时即可获得的先验信息（类别、作者粉丝数、发布时段），模型预测其后续热度。热度定义为加权互动量：播放量 + 3×点赞 + 5×评论 + 8×转发。" />

          <el-form :inline="false" label-width="120px" class="predict-form">
            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item label="预测模型">
                  <el-select v-model="form.model" style="width:100%">
                    <el-option label="LightGBM（推荐，效果最佳）" value="lgbm"/>
                    <el-option label="XGBoost" value="xgb"/>
                    <el-option label="随机森林 RandomForest" value="rf"/>
                    <el-option label="线性回归 LinearRegression" value="lr"/>
                    <el-option label="K 近邻回归 KNN" value="knn"/>
                    <el-option label="决策树 DecisionTree" value="dt"/>
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="视频类别">
                  <el-select v-model="form.videoCategory" style="width:100%">
                    <el-option v-for="c in categories" :key="c" :label="c" :value="c"/>
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="作者粉丝数">
                  <el-input-number v-model="form.authorFans" :min="0" :step="1000"
                                   :controls="false" style="width:100%"/>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="8">
                <el-form-item label="发布小时(0-23)">
                  <el-input-number v-model="form.publishHour" :min="0" :max="23" style="width:100%"/>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="发布星期">
                  <el-select v-model="form.publishWeekday" style="width:100%">
                    <el-option v-for="(w, i) in weekdays" :key="i" :label="w" :value="i"/>
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="发布月份">
                  <el-select v-model="form.publishMonth" style="width:100%">
                    <el-option v-for="m in 12" :key="m" :label="m + ' 月'" :value="m"/>
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="16">
                <el-form-item label="参考示例">
                  <div class="example-btns">
                    <el-button size="small" @click="fillExample(0)">头部达人·晚间</el-button>
                    <el-button size="small" @click="fillExample(1)">腰部作者·下午</el-button>
                    <el-button size="small" @click="fillExample(2)">素人·凌晨</el-button>
                  </div>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label-width="0">
                  <el-button type="primary" :loading="loading" class="predict-btn" @click="predict">
                    开始预测热度
                  </el-button>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>

        <el-card v-if="result" shadow="never" class="result-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">预测结果</span>
              <el-tag v-if="result.trainedNow" type="warning" size="small">本次为新训练模型</el-tag>
              <el-tag type="info" size="small">模型：{{ result.model }}</el-tag>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="result-item">
                <div class="result-label">预测热度（加权互动量）</div>
                <div class="result-value usd">{{ formatNum(result.prediction) }}</div>
                <div class="result-sub">log1p 空间：{{ fmt(result.predictionLog) }}</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="result-item">
                <div class="result-label">分级参考</div>
                <div class="result-value" :class="gradeClass(result.prediction)">{{ gradeOf(result.prediction) }}</div>
                <div class="result-sub">低热度 &lt; 684 ｜ 中热度 684~15661 ｜ 高热度 ≥ 15661</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="result-item">
                <div class="result-label">模型指标（20% 测试集）</div>
                <div v-if="result.metrics" class="result-metrics">
                  <div>决定系数 R²（log）：<b>{{ fmt(result.metrics.r2) }}</b></div>
                  <div>RMSE（log）：{{ fmt(result.metrics.rmse) }}</div>
                  <div>MAE（log）：{{ fmt(result.metrics.mae) }}</div>
                  <div v-if="result.metricsRaw">R²（原始）：{{ fmt(result.metricsRaw.r2) }}</div>
                </div>
                <div v-else class="result-sub">暂无指标</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-tab-pane>

      <!-- ==================== 批量预测 ==================== -->
      <el-tab-pane label="批量预测" name="batch">
        <el-card shadow="never" class="predict-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">批量热度预测</span>
              <el-tag size="small" type="info">一次最多 500 条</el-tag>
            </div>
          </template>

          <el-alert type="success" :closable="false" show-icon class="explain-tip"
                    title="每行一条视频，字段用逗号分隔：视频类别,作者粉丝数,发布小时(0-23),发布星期(0-6,0=周一),发布月份(1-12)。示例：美食,50000,20,5,6" />

          <el-form :inline="false" label-width="90px">
            <el-form-item label="预测模型">
              <el-select v-model="batch.model" style="width:260px">
                <el-option label="LightGBM（推荐）" value="lgbm"/>
                <el-option label="XGBoost" value="xgb"/>
                <el-option label="随机森林 RandomForest" value="rf"/>
                <el-option label="线性回归 LinearRegression" value="lr"/>
                <el-option label="K 近邻回归 KNN" value="knn"/>
                <el-option label="决策树 DecisionTree" value="dt"/>
              </el-select>
            </el-form-item>
            <el-form-item label="数据">
              <el-input v-model="batch.text" type="textarea" :rows="8"
                        placeholder="美食,50000,20,5,6&#10;音乐,1200,15,2,9&#10;搞笑,80,2,1,3"/>
            </el-form-item>
            <el-form-item label-width="0">
              <el-button size="small" @click="fillBatchExample">填入示例</el-button>
              <el-button size="small" @click="batch.text = ''">清空</el-button>
              <el-button type="primary" :loading="batchLoading" @click="doBatch">开始批量预测</el-button>
              <span v-if="batchError" class="batch-error">{{ batchError }}</span>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card v-if="batchResult" shadow="never" class="result-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">批量预测结果（{{ batchResult.count }} 条）</span>
              <el-tag v-if="batchResult.metrics" type="info" size="small">
                R²(log) {{ fmt(batchResult.metrics.r2) }}
              </el-tag>
            </div>
          </template>
          <el-table :data="batchRows" stripe size="small" max-height="420">
            <el-table-column type="index" label="#" width="60"/>
            <el-table-column prop="video_category" label="视频类别" width="110"/>
            <el-table-column label="作者粉丝数" width="130">
              <template #default="scope">{{ formatNum(scope.row.author_fans) }}</template>
            </el-table-column>
            <el-table-column label="预测热度" min-width="150">
              <template #default="scope">
                <b>{{ formatNum(scope.row.prediction) }}</b>
              </template>
            </el-table-column>
            <el-table-column prop="prediction_log" label="log1p" width="110">
              <template #default="scope">{{ fmt(scope.row.prediction_log) }}</template>
            </el-table-column>
            <el-table-column label="热度等级" width="120">
              <template #default="scope">
                <el-tag :type="gradeTag(scope.row.grade)" size="small">{{ scope.row.grade }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ==================== 模型对比 ==================== -->
      <el-tab-pane label="模型对比" name="compare">
        <el-card shadow="never">
          <div class="card-header">
            <span class="card-title">多模型对照实验（20% 测试集）</span>
            <el-button size="small" @click="loadMetrics">刷新</el-button>
          </div>
          <el-alert type="success" :closable="false" show-icon class="explain-tip"
                    title="相同特征与数据划分下对 6 种模型横向对比。log 空间指标更稳定；原始热度空间受强长尾影响，R² 偏低属正常现象。LightGBM 综合最优。" />
          <el-table :data="metrics" v-loading="metricsLoading" size="small" stripe>
            <el-table-column type="index" label="#" width="60"/>
            <el-table-column label="模型" min-width="170">
              <template #default="scope">
                {{ modelName(scope.row.model) }}
                <el-tag v-if="scope.$index === 0 && scope.row.trained" type="success" size="small">最优</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="RMSE(log)" width="120">
              <template #default="scope">{{ fmt(scope.row.rmse) }}</template>
            </el-table-column>
            <el-table-column label="MAE(log)" width="120">
              <template #default="scope">{{ fmt(scope.row.mae) }}</template>
            </el-table-column>
            <el-table-column label="R²(log)" width="190">
              <template #default="scope">
                <el-progress v-if="scope.row.trained" :percentage="r2pct(scope.row.r2)" :stroke-width="14"
                             :format="() => fmt(scope.row.r2)"/>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="R²(原始)" width="110">
              <template #default="scope">{{ fmt(scope.row.r2_raw) }}</template>
            </el-table-column>
            <el-table-column label="模型体积" width="110">
              <template #default="scope">{{ scope.row.trained ? scope.row.size_mb + ' MB' : '-' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.trained ? 'info' : 'warning'" size="small">
                  {{ scope.row.trained ? '已训练' : '未训练' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import predictApi from '@/api/predict'

export default {
  name: 'PredictIndex',
  data () {
    return {
      tab: 'single',
      loading: false,
      result: null,
      categories: ['搞笑', '美食', '音乐', '美妆', '穿搭', '舞蹈', '旅行', '宠物', '影视', '健身', '情感', '游戏', '生活', '知识'],
      weekdays: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      examples: [
        { videoCategory: '美食', authorFans: 500000, publishHour: 20, publishWeekday: 5, publishMonth: 6 },
        { videoCategory: '旅行', authorFans: 5000, publishHour: 15, publishWeekday: 2, publishMonth: 9 },
        { videoCategory: '搞笑', authorFans: 80, publishHour: 2, publishWeekday: 1, publishMonth: 3 }
      ],
      form: {
        model: 'lgbm',
        videoCategory: '美食',
        authorFans: 50000,
        publishHour: 20,
        publishWeekday: 5,
        publishMonth: 6
      },
      batch: { model: 'lgbm', text: '' },
      batchLoading: false,
      batchError: '',
      batchResult: null,
      batchRows: [],
      metrics: [],
      metricsLoading: false
    }
  },
  methods: {
    fillExample (idx) {
      Object.assign(this.form, this.examples[idx])
    },
    predict () {
      this.loading = true
      predictApi.predict({ ...this.form }).then(re => {
        this.result = re.response || {}
        this.loading = false
      }).catch(() => { this.loading = false })
    },
    fillBatchExample () {
      this.batch.text = [
        '美食,50000,20,5,6',
        '音乐,1200,15,2,9',
        '搞笑,80,2,1,3',
        '旅行,800000,21,6,10'
      ].join('\n')
    },
    parseBatch () {
      const lines = (this.batch.text || '').split(/\r?\n/).map(l => l.trim()).filter(l => l)
      if (!lines.length) {
        this.batchError = '请至少输入一行数据'
        return null
      }
      const items = []
      for (let i = 0; i < lines.length; i++) {
        const p = lines[i].split(/[,，]/).map(s => s.trim())
        if (p.length < 5) {
          this.batchError = `第 ${i + 1} 行格式不对，应为：类别,粉丝数,小时,星期,月份`
          return null
        }
        const fans = Number(p[1])
        const hour = Number(p[2])
        const weekday = Number(p[3])
        const month = Number(p[4])
        if ([fans, hour, weekday, month].some(v => Number.isNaN(v))) {
          this.batchError = `第 ${i + 1} 行含非数字字段`
          return null
        }
        if (hour < 0 || hour > 23 || weekday < 0 || weekday > 6 || month < 1 || month > 12) {
          this.batchError = `第 ${i + 1} 行取值超出范围（小时0-23，星期0-6，月份1-12）`
          return null
        }
        items.push({
          videoCategory: p[0],
          authorFans: fans,
          publishHour: hour,
          publishWeekday: weekday,
          publishMonth: month
        })
      }
      if (items.length > 500) {
        this.batchError = '一次最多 500 条'
        return null
      }
      this.batchError = ''
      return items
    },
    doBatch () {
      const items = this.parseBatch()
      if (!items) return
      this.batchLoading = true
      predictApi.predictBatch({ model: this.batch.model, items }).then(re => {
        this.batchResult = re.response || null
        this.batchRows = (this.batchResult && this.batchResult.results) || []
        this.batchLoading = false
      }).catch(() => { this.batchLoading = false })
    },
    onTabChange (name) {
      if (name === 'compare' && !this.metrics.length) {
        this.loadMetrics()
      }
    },
    loadMetrics () {
      this.metricsLoading = true
      predictApi.metrics().then(re => {
        this.metrics = (re.response && re.response.models) || []
        this.metricsLoading = false
      }).catch(() => { this.metricsLoading = false })
    },
    modelName (m) {
      return {
        lgbm: 'LightGBM', xgb: 'XGBoost', rf: '随机森林', lr: '线性回归', knn: 'K 近邻', svm: '支持向量回归', dt: '决策树'
      }[m] || m
    },
    r2pct (v) {
      if (v == null || !this.metrics.length || !this.metrics[0].r2) return 0
      return Math.max(0, Math.round(v / this.metrics[0].r2 * 100))
    },
    fmt (v) {
      return v == null ? '-' : Number(v).toFixed(3)
    },
    formatNum (v) {
      if (v == null) return '-'
      return Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })
    },
    gradeOf (v) {
      if (v == null) return '-'
      if (v < 684) return '低热度'
      if (v < 15661) return '中热度'
      return '高热度'
    },
    gradeClass (v) {
      if (v == null) return ''
      if (v < 684) return 'grade-low'
      if (v < 15661) return 'grade-mid'
      return 'grade-high'
    },
    gradeTag (g) {
      return { 低热度: 'info', 中热度: 'warning', 高热度: 'danger' }[g] || 'info'
    }
  }
}
</script>

<style scoped>
.predict-card {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
}
.explain-tip {
  margin-bottom: 12px;
}
.predict-form {
  margin-top: 8px;
}
.predict-btn {
  width: 100%;
}
.example-btns {
  padding-top: 2px;
}
.batch-error {
  color: #f56c6c;
  font-size: 13px;
  margin-left: 12px;
}
.result-card {
  margin-top: 16px;
}
.result-item {
  text-align: center;
  padding: 16px 0;
}
.result-label {
  color: #909399;
  font-size: 13px;
  margin-bottom: 12px;
}
.result-value {
  font-size: 30px;
  font-weight: 700;
  line-height: 1.2;
}
.result-value.usd {
  color: #409eff;
}
.result-value.grade-low {
  color: #909399;
}
.result-value.grade-mid {
  color: #e6a23c;
}
.result-value.grade-high {
  color: #f56c6c;
}
.result-sub {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}
.result-metrics {
  font-size: 14px;
  color: #606266;
  line-height: 2;
}
.result-metrics b {
  color: #67c23a;
}
</style>
