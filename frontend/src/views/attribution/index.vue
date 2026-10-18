<template>
  <div class="app-container">
    <el-alert type="success" :closable="false" show-icon style="margin-bottom:14px"
              title="归因分析（SHAP）：回答「为什么这条视频会火 / 不火」。SHAP 值基于博弈论 Shapley 值，给出每个特征对单条预测的贡献方向与大小；全局视图给出整体特征重要性。SHAP 值在 log1p(热度) 空间上计算。"/>

    <el-tabs v-model="tab" type="border-card">
      <!-- ---------------- 全局归因 ---------------- -->
      <el-tab-pane label="全局归因" name="global">
        <div v-loading="globalLoading">
          <el-row :gutter="16">
            <el-col :xs="24" :md="12" style="margin-bottom:16px">
              <el-card shadow="hover">
                <div class="fig-title">全局特征重要性（SHAP 平均绝对贡献）</div>
                <el-image :src="fig('global_importance.png')" :preview-src-list="[fig('global_importance.png')]"
                          fit="contain" class="fig-img" lazy/>
              </el-card>
            </el-col>
            <el-col :xs="24" :md="12" style="margin-bottom:16px">
              <el-card shadow="hover">
                <div class="fig-title">SHAP 汇总图（特征取值与贡献方向）</div>
                <el-image :src="fig('shap_summary.png')" :preview-src-list="[fig('shap_summary.png')]"
                          fit="contain" class="fig-img" lazy/>
              </el-card>
            </el-col>
          </el-row>

          <el-card shadow="never">
            <div class="fig-title">特征重要性排行</div>
            <el-table :data="globalTop" stripe size="small">
              <el-table-column type="index" label="#" width="60"/>
              <el-table-column prop="feature_cn" label="特征" min-width="160"/>
              <el-table-column prop="feature" label="字段名" min-width="150"/>
              <el-table-column label="重要性（平均 |SHAP|）" min-width="180">
                <template #default="scope">
                  <el-progress :percentage="pct(scope.row.importance)" :stroke-width="14"
                               :format="() => scope.row.importance.toFixed(3)"/>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ---------------- 单条视频归因 ---------------- -->
      <el-tab-pane label="单条视频归因" name="explain">
        <el-form :inline="false" label-width="120px">
          <el-row :gutter="20">
            <el-col :span="6">
              <el-form-item label="视频类别">
                <el-select v-model="form.videoCategory" style="width:100%">
                  <el-option v-for="c in categories" :key="c" :label="c" :value="c"/>
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="作者粉丝数">
                <el-input-number v-model="form.authorFans" :min="0" :step="1000" :controls="false" style="width:100%"/>
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item label="发布小时">
                <el-input-number v-model="form.publishHour" :min="0" :max="23" style="width:100%"/>
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item label="星期">
                <el-select v-model="form.publishWeekday" style="width:100%">
                  <el-option v-for="(w, i) in weekdays" :key="i" :label="w" :value="i"/>
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="4">
              <el-form-item label-width="0">
                <el-button type="primary" :loading="explainLoading" style="width:100%" @click="doExplain">
                  归因分析
                </el-button>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <div v-if="explain" v-loading="explainLoading">
          <el-row :gutter="16">
            <el-col :xs="24" :md="14">
              <el-card shadow="hover">
                <div class="fig-title">单样本 SHAP 瀑布图（预测 {{ fmt(explain.prediction) }}，基线 {{ fmt(explain.base_value) }}）</div>
                <el-image :src="fig('shap_waterfall.png', true)" :preview-src-list="[fig('shap_waterfall.png', true)]"
                          fit="contain" class="fig-img-lg" lazy/>
              </el-card>
            </el-col>
            <el-col :xs="24" :md="10">
              <el-card shadow="never" style="margin-bottom:16px">
                <div class="fig-title">特征贡献明细（log 空间）</div>
                <el-table :data="explain.contributions" size="small" stripe>
                  <el-table-column prop="feature_cn" label="特征" min-width="130"/>
                  <el-table-column label="贡献" width="110">
                    <template #default="scope">
                      <span :class="scope.row.shap >= 0 ? 'pos' : 'neg'">
                        {{ scope.row.shap >= 0 ? '+' : '' }}{{ scope.row.shap.toFixed(3) }}
                      </span>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
              <el-card shadow="never">
                <div class="fig-title">
                  运营建议（归因 → 决策）
                  <el-button size="small" style="float:right" @click="exportReport">导出报告</el-button>
                </div>
                <ul class="advice-list">
                  <li v-for="(a, i) in explain.advice" :key="i">{{ a }}</li>
                </ul>
              </el-card>
            </el-col>
          </el-row>
        </div>
        <el-empty v-else description="填写左侧参数后点击「归因分析」"/>
      </el-tab-pane>

      <!-- ---------------- 部分依赖图 PDP ---------------- -->
      <el-tab-pane label="特征依赖关系 (PDP)" name="pdp">
        <el-form inline>
          <el-form-item label="选择特征">
            <el-select v-model="pdpFeature" style="width:240px">
              <el-option v-for="f in pdpOptions" :key="f.value" :label="f.label" :value="f.value"/>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="pdpLoading" @click="doPdp">生成部分依赖图</el-button>
          </el-form-item>
          <el-form-item v-if="pdp">
            <el-tag type="success">最优取值点：{{ pdpFeatureLabel }} = {{ fmt(pdp.best_point.x) }}，平均热度 ≈ {{ formatNum(pdp.best_point.avg_heat) }}</el-tag>
          </el-form-item>
        </el-form>
        <div v-loading="pdpLoading">
          <el-image v-if="pdp" :src="fig(pdp.figure, true)" :preview-src-list="[fig(pdp.figure, true)]"
                    fit="contain" class="fig-img-lg" lazy/>
          <el-empty v-else description="选择特征后点击「生成部分依赖图」"/>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import attributionApi from '@/api/attribution'

export default {
  name: 'AttributionIndex',
  data () {
    return {
      tab: 'global',
      globalLoading: false,
      globalTop: [],
      categories: ['搞笑', '美食', '音乐', '美妆', '穿搭', '舞蹈', '旅行', '宠物', '影视', '健身', '情感', '游戏', '生活', '知识'],
      weekdays: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      form: {
        videoCategory: '美食',
        authorFans: 50000,
        publishHour: 20,
        publishWeekday: 5,
        publishMonth: 6
      },
      explain: null,
      explainLoading: false,
      pdpFeature: 'author_fans_log',
      pdp: null,
      pdpLoading: false,
      pdpOptions: [
        { value: 'author_fans_log', label: '作者粉丝数(log)' },
        { value: 'publish_hour', label: '发布小时' },
        { value: 'publish_weekday', label: '发布星期' },
        { value: 'publish_month', label: '发布月份' },
        { value: 'video_category', label: '视频类别' },
        { value: 'hour_bucket', label: '发布时段' }
      ]
    }
  },
  computed: {
    pdpFeatureLabel () {
      const o = this.pdpOptions.find(x => x.value === this.pdpFeature)
      return o ? o.label : this.pdpFeature
    }
  },
  created () {
    this.loadGlobal()
  },
  methods: {
    fig (name, bust) {
      return '/attribution/' + name + (bust ? ('?t=' + Date.now()) : '')
    },
    loadGlobal () {
      this.globalLoading = true
      attributionApi.global().then(re => {
        this.globalTop = (re.response && re.response.top_features) || []
        this.globalLoading = false
      }).catch(() => { this.globalLoading = false })
    },
    pct (v) {
      if (!this.globalTop.length || !this.globalTop[0].importance) return 0
      return Math.round(v / this.globalTop[0].importance * 100)
    },
    doExplain () {
      this.explainLoading = true
      attributionApi.explain({ ...this.form }).then(re => {
        this.explain = re.response || null
        this.explainLoading = false
      }).catch(() => { this.explainLoading = false })
    },
    doPdp () {
      this.pdpLoading = true
      attributionApi.pdp(this.pdpFeature).then(re => {
        this.pdp = re.response || null
        this.pdpLoading = false
      }).catch(() => { this.pdpLoading = false })
    },
    exportReport () {
      const e = this.explain
      if (!e) return
      const f = this.form
      const lines = []
      lines.push('短视频热度归因分析报告')
      lines.push('分析参数,' + ['视频类别=' + f.videoCategory, '作者粉丝数=' + f.authorFans,
        '发布小时=' + f.publishHour, '发布星期=' + f.publishWeekday, '发布月份=' + f.publishMonth].join(' '))
      lines.push('预测热度,' + e.prediction + ',log1p,' + e.prediction_log + ',基线,' + e.base_value)
      lines.push('')
      lines.push('特征,取值,SHAP贡献(log空间)')
      ;(e.contributions || []).forEach(c => {
        lines.push([c.feature_cn, c.value, c.shap].join(','))
      })
      lines.push('')
      lines.push('运营建议')
      ;(e.advice || []).forEach((a, i) => {
        lines.push((i + 1) + ',' + String(a).replace(/,/g, '，'))
      })
      const blob = new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = '归因报告_' + f.videoCategory + '_' + new Date().toISOString().slice(0, 10) + '.csv'
      link.click()
      URL.revokeObjectURL(url)
      this.$message.success('归因报告已导出')
    },
    fmt (v) {
      return v == null ? '-' : Number(v).toFixed(3)
    },
    formatNum (v) {
      if (v == null) return '-'
      return Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })
    }
  }
}
</script>

<style scoped>
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
.fig-img-lg {
  width: 100%;
  height: 420px;
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}
.pos {
  color: #f56c6c;
  font-weight: 600;
}
.neg {
  color: #409eff;
  font-weight: 600;
}
.advice-list {
  margin: 0;
  padding-left: 18px;
  color: #606266;
  font-size: 13px;
  line-height: 1.9;
}
</style>
