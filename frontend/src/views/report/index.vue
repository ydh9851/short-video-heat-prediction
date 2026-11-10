<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">报告中心</div>
        <div class="page-desc">
          归因报告统一落库管理：记录<strong>生成时的模型版本与数据版本</strong>快照，与场景联动一键生成；
          支持在线预览、下载与<strong>免登录只读分享链接</strong>。
        </div>
      </div>
      <div class="page-head-actions">
        <el-button type="primary" @click="openGenerate">生成报告</el-button>
      </div>
    </div>

    <el-card shadow="never" class="list-card">
      <div class="list-toolbar">
        <div class="list-toolbar-filters">
          <el-input v-model="queryParam.name" placeholder="按名称搜索" clearable style="width: 200px" @keyup.enter="submitForm" @clear="submitForm" />
          <el-select v-model="queryParam.status" placeholder="状态" clearable style="width: 130px" @change="submitForm">
            <el-option label="生成中" value="GENERATING" />
            <el-option label="已完成" value="DONE" />
            <el-option label="失败" value="FAILED" />
          </el-select>
          <el-button @click="submitForm">搜索</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </div>
        <div class="list-toolbar-actions">
          <span class="muted">共 {{ total }} 份报告</span>
        </div>
      </div>

      <el-table v-loading="listLoading" :data="tableData" stripe style="width: 100%">
        <el-table-column label="报告名称" min-width="200">
          <template #default="{ row }">
            <span class="report-name">{{ row.name }}</span>
            <el-tag size="small" effect="plain" class="type-tag">归因</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联场景" min-width="140">
          <template #default="{ row }">{{ row.caseName || '手动输入' }}</template>
        </el-table-column>
        <el-table-column label="模型 / 版本" min-width="170">
          <template #default="{ row }">
            <span>{{ row.model }}</span>
            <span class="muted version" :title="row.modelVersion">{{ shortVersion(row.modelVersion) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="数据版本" width="130">
          <template #default="{ row }">
            <span class="muted" :title="row.dataVersion">{{ shortVersion(row.dataVersion) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="预测热度 / 等级" width="130">
          <template #default="{ row }">
            <template v-if="row.status === 'DONE'">{{ formatHeat(row.prediction) }} · {{ row.grade }}</template>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'DONE'" type="success" effect="plain">已完成</el-tag>
            <el-tag v-else-if="row.status === 'GENERATING'" type="warning" effect="plain">生成中</el-tag>
            <el-tooltip v-else :content="row.errorMsg || '生成失败'" placement="top">
              <el-tag type="danger" effect="plain">失败</el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="80">
          <template #default="{ row }">{{ row.sizeKb ? row.sizeKb + ' KB' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="userName" label="创建人" width="100">
          <template #default="{ row }">{{ row.userName || '-' }}</template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="165" />
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <div class="cell-actions">
              <el-button link type="primary" :disabled="row.status !== 'DONE'" @click="preview(row)">预览</el-button>
              <el-button link type="primary" :disabled="row.status !== 'DONE'" @click="download(row)">下载</el-button>
              <el-button link type="success" :disabled="row.status !== 'DONE'" @click="openShare(row)">分享</el-button>
              <el-button link type="danger" @click="remove(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty><app-empty compact title="暂无报告，点击右上角「生成报告」" /></template>
      </el-table>

      <div class="list-footer">
        <pagination v-show="total > 0" :total="total" v-model:page="queryParam.pageIndex" v-model:limit="queryParam.pageSize" @pagination="search" />
      </div>
    </el-card>

    <!-- 生成报告对话框 -->
    <el-dialog v-model="genVisible" title="生成归因报告" width="560px">
      <el-form label-position="top">
        <el-form-item label="报告名称">
          <el-input v-model="genForm.name" maxlength="100" show-word-limit placeholder="缺省自动命名：归因报告 · <场景名或类别>" />
        </el-form-item>
        <el-form-item label="分析场景">
          <el-select v-model="genForm.caseId" style="width:100%" placeholder="不使用场景（手动输入参数）" clearable @change="onCaseChange">
            <el-option v-for="c in caseOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <template v-if="selectedCase">
          <el-alert type="info" :closable="false" show-icon>
            <template #title>
              场景参数：{{ selectedCase.model }} · {{ selectedCase.videoCategory }} · 粉丝 {{ formatFans(selectedCase.authorFans) }} ·
              {{ selectedCase.publishHour }}时 · 周{{ weekdayText(selectedCase.publishWeekday) }} · {{ selectedCase.publishMonth }}月
            </template>
          </el-alert>
        </template>
        <template v-else>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item label="预测模型">
                <el-select v-model="genForm.model" style="width:100%">
                  <el-option label="LightGBM（推荐）" value="lgbm" />
                  <el-option label="XGBoost" value="xgb" />
                  <el-option label="随机森林" value="rf" />
                  <el-option label="线性回归" value="lr" />
                  <el-option label="K 近邻" value="knn" />
                  <el-option label="决策树" value="dt" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="视频类别" required>
                <el-select v-model="genForm.videoCategory" style="width:100%">
                  <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="作者粉丝数">
            <el-input-number v-model="genForm.authorFans" :min="0" :step="10000" :controls="false" style="width:100%" />
          </el-form-item>
          <el-row :gutter="12">
            <el-col :span="8">
              <el-form-item label="发布小时">
                <el-input-number v-model="genForm.publishHour" :min="0" :max="23" style="width:100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="发布星期">
                <el-select v-model="genForm.publishWeekday" style="width:100%">
                  <el-option v-for="(w, i) in weekdays" :key="i" :label="w" :value="i" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="发布月份">
                <el-select v-model="genForm.publishMonth" style="width:100%">
                  <el-option v-for="m in 12" :key="m" :label="m + ' 月'" :value="m" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="genVisible = false">取消</el-button>
        <el-button type="primary" :loading="genSaving" @click="submitGenerate">提交生成</el-button>
      </template>
    </el-dialog>

    <!-- 在线预览 -->
    <el-dialog v-model="previewVisible" :title="previewRow ? previewRow.name : ''" width="960px" top="4vh">
      <iframe v-if="previewVisible && previewRow" :src="`/api/report/${previewRow.id}/content`" class="preview-frame" />
    </el-dialog>

    <!-- 分享 -->
    <el-dialog v-model="shareVisible" title="分享报告" width="520px">
      <p class="muted">任何获得该链接的人都可<strong>免登录只读</strong>访问此报告，请谨慎分发。</p>
      <div class="share-row">
        <el-input v-model="shareUrl" readonly>
          <template #append>
            <el-button @click="copyShare">复制</el-button>
          </template>
        </el-input>
      </div>
      <template #footer>
        <el-button type="danger" plain :loading="unsharing" @click="doUnshare">取消分享</el-button>
        <el-button @click="shareVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import Pagination from '@/components/Pagination'
import AppEmpty from '@/components/AppEmpty'
import reportApi from '@/api/report'
import caseApi from '@/api/case'

export default {
  name: 'ReportCenterPage',
  components: { Pagination, AppEmpty },
  data () {
    return {
      queryParam: { name: '', status: '', pageIndex: 1, pageSize: 20 },
      listLoading: true,
      tableData: [],
      total: 0,
      genVisible: false,
      genSaving: false,
      caseOptions: [],
      genForm: this.emptyGenForm(),
      categories: ['搞笑', '美食', '音乐', '美妆', '穿搭', '舞蹈', '旅行', '宠物', '影视', '健身', '情感', '游戏', '生活', '知识'],
      weekdays: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
      previewVisible: false,
      previewRow: null,
      shareVisible: false,
      shareUrl: '',
      shareRow: null,
      unsharing: false,
      pollTimer: null
    }
  },
  computed: {
    ...mapGetters(['currentCase']),
    selectedCase () {
      return this.caseOptions.find(c => c.id === this.genForm.caseId) || null
    }
  },
  created () {
    this.search()
  },
  beforeUnmount () {
    this.stopPoll()
  },
  methods: {
    emptyGenForm () {
      return {
        name: '', caseId: null, model: 'lgbm', videoCategory: '美食',
        authorFans: 50000, publishHour: 20, publishWeekday: 4, publishMonth: 9
      }
    },
    search () {
      this.listLoading = true
      reportApi.page(this.queryParam).then(re => {
        this.listLoading = false
        this.tableData = re.response.records || []
        this.total = re.response.total || 0
        this.refreshPoll()
      }).catch(() => { this.listLoading = false })
    },
    submitForm () {
      this.queryParam.pageIndex = 1
      this.search()
    },
    resetQuery () {
      this.queryParam = { name: '', status: '', pageIndex: 1, pageSize: 20 }
      this.search()
    },
    // ---------------------------------------------------------------- 生成
    openGenerate () {
      this.genForm = this.emptyGenForm()
      caseApi.page({ pageIndex: 1, pageSize: 100 }).then(re => {
        this.caseOptions = (re.response && re.response.records) || []
        // 当前场景默认选中：从归因/预测页带着上下文来时可一键生成
        if (this.currentCase && this.caseOptions.some(c => c.id === this.currentCase.id)) {
          this.genForm.caseId = this.currentCase.id
          this.genForm.name = '归因报告 · ' + this.currentCase.name
        }
      }).catch(() => { this.caseOptions = [] })
      this.genVisible = true
    },
    onCaseChange (id) {
      const c = this.caseOptions.find(x => x.id === id)
      if (c) {
        this.genForm.name = '归因报告 · ' + c.name
      }
    },
    submitGenerate () {
      const f = this.genForm
      const payload = { name: f.name || undefined }
      if (f.caseId) {
        payload.caseId = f.caseId
      } else {
        Object.assign(payload, {
          model: f.model, videoCategory: f.videoCategory, authorFans: f.authorFans,
          publishHour: f.publishHour, publishWeekday: f.publishWeekday, publishMonth: f.publishMonth
        })
      }
      this.genSaving = true
      reportApi.generate(payload).then(() => {
        this.genSaving = false
        this.genVisible = false
        this.$message.success('已提交生成，稍后可在列表查看结果')
        this.search()
      }).catch(() => { this.genSaving = false })
    },
    // ---------------------------------------------------------------- 生成中轮询
    refreshPoll () {
      const generating = this.tableData.some(r => r.status === 'GENERATING')
      if (generating && !this.pollTimer) {
        this.pollTimer = setInterval(this.pollOnce, 4000)
      } else if (!generating) {
        this.stopPoll()
      }
    },
    pollOnce () {
      const rows = this.tableData.filter(r => r.status === 'GENERATING')
      if (!rows.length) {
        this.stopPoll()
        return
      }
      rows.forEach(row => {
        reportApi.get(row.id).then(re => {
          const fresh = re.response
          if (fresh && fresh.status !== 'GENERATING') {
            const idx = this.tableData.findIndex(r => r.id === row.id)
            if (idx >= 0) this.tableData.splice(idx, 1, fresh)
            this.refreshPoll()
          }
        }).catch(() => {})
      })
    },
    stopPoll () {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    // ---------------------------------------------------------------- 操作
    preview (row) {
      this.previewRow = row
      this.previewVisible = true
    },
    download (row) {
      window.open(`/api/report/${row.id}/content?download=1`, '_blank')
    },
    openShare (row) {
      this.shareRow = row
      reportApi.share(row.id).then(re => {
        this.shareUrl = location.origin + re.response.url
        this.shareVisible = true
      }).catch(() => {})
    },
    copyShare () {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(this.shareUrl)
          .then(() => this.$message.success('链接已复制'))
          .catch(() => this.$message.warning('复制失败，请手动全选复制'))
      } else {
        this.$message.warning('当前浏览器不支持自动复制，请手动全选复制')
      }
    },
    doUnshare () {
      if (!this.shareRow) return
      this.unsharing = true
      reportApi.unshare(this.shareRow.id).then(() => {
        this.unsharing = false
        this.shareVisible = false
        this.$message.success('已取消分享，原链接即刻失效')
        this.search()
      }).catch(() => { this.unsharing = false })
    },
    remove (row) {
      this.$confirm(`删除报告「${row.name}」？报告文件将一并删除。`, '确认删除', { type: 'warning' })
        .then(() => reportApi.remove(row.id))
        .then(() => {
          this.$message.success('已删除')
          this.search()
        }).catch(() => {})
    },
    // ---------------------------------------------------------------- 格式化
    shortVersion (v) {
      if (!v) return '-'
      return v.length > 18 ? v.slice(0, 18) + '…' : v
    },
    formatHeat (v) {
      if (v == null) return '-'
      return Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
    },
    formatFans (v) {
      if (v == null) return '-'
      if (v >= 10000) return (v / 10000).toFixed(1) + ' 万'
      return String(v)
    },
    weekdayText (w) {
      return ['一', '二', '三', '四', '五', '六', '日'][w] || '-'
    }
  }
}
</script>

<style scoped>
.report-name { font-weight: 600; }
.type-tag { margin-left: 6px; }
.muted { color: #94a3b8; font-size: 12px; }
.version { margin-left: 6px; font-size: 12px; }
.preview-frame { width: 100%; height: 72vh; border: none; border-radius: 8px; background: #f6f7fb; }
.share-row { margin-top: 10px; }
</style>
