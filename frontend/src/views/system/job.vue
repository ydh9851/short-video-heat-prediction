<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">任务中心</div>
        <div class="page-desc">长耗时任务（数据导入等）的提交、进度与结果追踪；失败任务可一键重试。</div>
      </div>
      <div class="page-head-actions">
        <el-button :loading="listLoading" @click="search">刷新</el-button>
      </div>
    </div>

    <el-card shadow="never" class="list-card">
      <div class="list-toolbar">
        <div class="list-toolbar-filters">
          <el-select v-model="queryParam.jobType" placeholder="任务类型" clearable style="width: 180px" @change="submitForm">
            <el-option label="数据导入" value="data.import" />
          </el-select>
          <el-select v-model="queryParam.status" placeholder="状态" clearable style="width: 140px" @change="submitForm">
            <el-option label="排队中" value="QUEUED" />
            <el-option label="执行中" value="RUNNING" />
            <el-option label="已完成" value="DONE" />
            <el-option label="失败" value="FAILED" />
          </el-select>
          <el-button @click="resetQuery">重置</el-button>
        </div>
        <div class="list-toolbar-actions">
          <span class="muted">共 {{ total }} 个任务</span>
        </div>
      </div>

      <el-table v-loading="listLoading" :data="tableData" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="jobType" label="类型" width="130">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ typeLabel(row.jobType) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <span class="status-dot" :class="statusClass(row.status)"><i />{{ statusLabel(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="userName" label="提交人" width="120">
          <template #default="{ row }">{{ row.userName || '-' }}</template>
        </el-table-column>
        <el-table-column label="耗时" width="110">
          <template #default="{ row }">{{ costText(row) }}</template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="170" />
        <el-table-column prop="finishTime" label="完成时间" width="170">
          <template #default="{ row }">{{ row.finishTime || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <div class="cell-actions">
              <el-button link type="primary" @click="showDetail(row)">详情</el-button>
              <el-button
                v-if="row.status === 'FAILED' || row.status === 'DONE'"
                link type="warning"
                @click="retryJob(row)">重试</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty><app-empty compact title="暂无任务" /></template>
      </el-table>

      <div class="list-footer">
        <pagination v-show="total > 0" :total="total" v-model:page="queryParam.pageIndex" v-model:limit="queryParam.pageSize" @pagination="search" />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" title="任务详情" width="640px">
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="任务 ID">{{ current.id }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ typeLabel(current.jobType) }}（{{ current.jobType }}）</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusLabel(current.status) }}</el-descriptions-item>
        <el-descriptions-item label="参数">
          <pre class="detail-pre">{{ prettyJson(current.params) }}</pre>
        </el-descriptions-item>
        <el-descriptions-item v-if="current.result" label="结果">
          <pre class="detail-pre">{{ prettyJson(current.result) }}</pre>
        </el-descriptions-item>
        <el-descriptions-item v-if="current.errorMsg" label="错误信息">
          <pre class="detail-pre error">{{ current.errorMsg }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="提交人">{{ current.userName || '-' }}（ID: {{ current.userId || '-' }}）</el-descriptions-item>
        <el-descriptions-item label="TraceId">{{ current.traceId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ costText(current) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ current.createTime }}</el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ current.startTime || '-' }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ current.finishTime || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script>
import Pagination from '@/components/Pagination'
import AppEmpty from '@/components/AppEmpty'
import jobApi from '@/api/job'

export default {
  name: 'JobCenterPage',
  components: { Pagination, AppEmpty },
  data () {
    return {
      queryParam: {
        jobType: '',
        status: '',
        pageIndex: 1,
        pageSize: 20
      },
      listLoading: true,
      tableData: [],
      total: 0,
      detailVisible: false,
      current: {},
      timer: null
    }
  },
  created () {
    this.search()
    // 有排队/执行中的任务时每 5 秒自动刷新，便于观察导入进度
    this.timer = setInterval(() => {
      if (this.tableData.some(j => j.status === 'QUEUED' || j.status === 'RUNNING')) {
        this.search()
      }
    }, 5000)
  },
  beforeUnmount () {
    if (this.timer) clearInterval(this.timer)
  },
  methods: {
    search () {
      this.listLoading = true
      jobApi.page(this.queryParam).then(data => {
        const re = data.response
        this.tableData = re.records || []
        this.total = re.total || 0
        this.queryParam.pageIndex = re.current || this.queryParam.pageIndex
        this.listLoading = false
      }).catch(() => { this.listLoading = false })
    },
    submitForm () {
      this.queryParam.pageIndex = 1
      this.search()
    },
    resetQuery () {
      this.queryParam.jobType = ''
      this.queryParam.status = ''
      this.queryParam.pageIndex = 1
      this.search()
    },
    showDetail (row) {
      this.current = row
      this.detailVisible = true
    },
    retryJob (row) {
      this.$confirm(`以相同参数重新提交任务 #${row.id}？`, '重试确认', {
        type: 'warning',
        confirmButtonText: '重新提交',
        cancelButtonText: '取消'
      }).then(() => {
        jobApi.retry(row.id).then(re => {
          if (re.code === 1) {
            this.$message.success(`已重新提交，新任务 ID：${re.response}`)
            this.search()
          } else {
            this.$message.error(re.message)
          }
        })
      }).catch(() => {})
    },
    typeLabel (t) {
      return { 'data.import': '数据导入' }[t] || t
    },
    statusLabel (s) {
      return { QUEUED: '排队中', RUNNING: '执行中', DONE: '已完成', FAILED: '失败' }[s] || s
    },
    statusClass (s) {
      if (s === 'DONE') return 'on'
      if (s === 'FAILED') return 'off'
      return 'warn'
    },
    costText (row) {
      if (row.costMs == null) return '-'
      if (row.costMs < 1000) return `${row.costMs} ms`
      const s = Math.round(row.costMs / 1000)
      if (s < 60) return `${s} 秒`
      return `${Math.floor(s / 60)} 分 ${s % 60} 秒`
    },
    prettyJson (s) {
      if (!s) return '-'
      try {
        return JSON.stringify(JSON.parse(s), null, 2)
      } catch (e) {
        return s
      }
    }
  }
}
</script>

<style scoped>
.detail-pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
  max-height: 240px;
  overflow: auto;
}
.detail-pre.error {
  color: var(--el-color-danger);
}
.status-dot.warn i {
  background: var(--el-color-warning);
}
</style>
