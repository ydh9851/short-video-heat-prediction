<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">操作审计日志</div>
        <div class="page-desc">记录平台关键管理操作（模型上下线、数据导入等）的操作人、参数、结果与耗时，支持按操作与操作人追溯。</div>
      </div>
    </div>

    <el-card shadow="never" class="list-card">
      <div class="list-toolbar">
        <div class="list-toolbar-filters">
          <el-input
            v-model="queryParam.operation"
            placeholder="操作标识，如 model.promote"
            clearable
            style="width: 220px"
            @keyup.enter="submitForm"
            @clear="submitForm" />
          <el-input
            v-model="queryParam.userName"
            placeholder="操作人用户名"
            clearable
            style="width: 180px"
            @keyup.enter="submitForm"
            @clear="submitForm" />
          <el-button type="primary" @click="submitForm">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </div>
        <div class="list-toolbar-actions">
          <span class="muted">共 {{ total }} 条记录</span>
        </div>
      </div>

      <el-table v-loading="listLoading" :data="tableData" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="operation" label="操作" min-width="140">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.operation }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="userName" label="操作人" width="130">
          <template #default="{ row }">{{ row.userName || '未知' }}</template>
        </el-table-column>
        <el-table-column prop="method" label="方法" min-width="200" show-overflow-tooltip />
        <el-table-column prop="result" label="结果" width="100">
          <template #default="{ row }">
            <span class="status-dot" :class="row.result === 'SUCCESS' ? 'on' : 'off'">
              <i />{{ row.result === 'SUCCESS' ? '成功' : '失败' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="costMs" label="耗时" width="100">
          <template #default="{ row }">{{ row.costMs }} ms</template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="130" show-overflow-tooltip />
        <el-table-column prop="createTime" label="时间" width="180" />
        <el-table-column label="详情" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
        <template #empty><app-empty compact title="暂无审计记录" /></template>
      </el-table>

      <div class="list-footer">
        <pagination v-show="total > 0" :total="total" v-model:page="queryParam.pageIndex" v-model:limit="queryParam.pageSize" @pagination="search" />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" title="操作详情" width="640px">
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="操作">{{ current.operation }}</el-descriptions-item>
        <el-descriptions-item label="操作人">{{ current.userName || '未知' }}（ID: {{ current.userId || '-' }}）</el-descriptions-item>
        <el-descriptions-item label="方法">{{ current.method }}</el-descriptions-item>
        <el-descriptions-item label="参数">
          <pre class="detail-pre">{{ current.params || '-' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="结果">{{ current.result }}</el-descriptions-item>
        <el-descriptions-item v-if="current.errorMsg" label="错误信息">
          <pre class="detail-pre error">{{ current.errorMsg }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="耗时">{{ current.costMs }} ms</el-descriptions-item>
        <el-descriptions-item label="TraceId">{{ current.traceId || '-' }}</el-descriptions-item>
        <el-descriptions-item label="IP">{{ current.ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ current.createTime }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script>
import Pagination from '@/components/Pagination'
import AppEmpty from '@/components/AppEmpty'
import operationLogApi from '@/api/operationLog'

export default {
  name: 'OperationLogPage',
  components: { Pagination, AppEmpty },
  data () {
    return {
      queryParam: {
        operation: '',
        userName: '',
        pageIndex: 1,
        pageSize: 20
      },
      listLoading: true,
      tableData: [],
      total: 0,
      detailVisible: false,
      current: {}
    }
  },
  created () {
    this.search()
  },
  methods: {
    search () {
      this.listLoading = true
      operationLogApi.page(this.queryParam).then(data => {
        const re = data.response
        // MyBatis-Plus IPage：records / total / current
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
      this.queryParam.operation = ''
      this.queryParam.userName = ''
      this.queryParam.pageIndex = 1
      this.search()
    },
    showDetail (row) {
      this.current = row
      this.detailVisible = true
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
  max-height: 200px;
  overflow: auto;
}
.detail-pre.error {
  color: var(--el-color-danger);
}
</style>
