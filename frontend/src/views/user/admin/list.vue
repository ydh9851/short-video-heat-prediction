<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">管理员列表</div>
        <div class="page-desc">管理系统管理员账号、联系方式与启用状态。</div>
      </div>
      <div class="page-head-actions">
        <router-link :to="{path:'/user/admin/edit'}">
          <el-button type="primary">新增管理员</el-button>
        </router-link>
      </div>
    </div>

    <el-card shadow="never" class="list-card">
      <div class="list-toolbar">
        <div class="list-toolbar-filters">
          <el-input
            v-model="queryParam.userName"
            placeholder="搜索用户名"
            clearable
            style="width: 240px"
            @keyup.enter="submitForm"
            @clear="submitForm">
            <template #prefix><svg-icon icon-class="search" /></template>
          </el-input>
          <el-button type="primary" @click="submitForm">查询</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </div>
        <div class="list-toolbar-actions">
          <span class="muted">共 {{ total }} 个管理员</span>
        </div>
      </div>

      <el-table v-loading="listLoading" :data="tableData" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="userName" label="用户名" min-width="150" />
        <el-table-column prop="sex" label="性别" width="90" :formatter="sexFormatter" />
        <el-table-column prop="phone" label="手机号" min-width="150" />
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="status-dot" :class="row.status === 1 ? 'on' : 'off'">
              <i />{{ statusFormatter(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <div class="cell-actions">
              <el-button link type="primary" @click="changeStatus(row)">
                {{ statusBtnFormatter(row.status) }}
              </el-button>
              <router-link :to="{path:'/user/admin/edit', query:{id:row.id}}">
                <el-button link type="primary">编辑</el-button>
              </router-link>
              <el-button link type="danger" @click="deleteUser(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无管理员数据" :image-size="80" /></template>
      </el-table>

      <div class="list-footer">
        <pagination v-show="total > 0" :total="total" v-model:page="queryParam.pageIndex" v-model:limit="queryParam.pageSize" @pagination="search" />
      </div>
    </el-card>
  </div>
</template>

<script>
import { mapGetters, mapState } from 'vuex'
import Pagination from '@/components/Pagination'
import userApi from '@/api/user'

export default {
  components: { Pagination },
  data () {
    return {
      queryParam: {
        userName: '',
        role: 3,
        pageIndex: 1,
        pageSize: 10
      },
      listLoading: true,
      tableData: [],
      total: 0
    }
  },
  created () {
    this.search()
  },
  methods: {
    search () {
      this.listLoading = true
      userApi.getUserPageList(this.queryParam).then(data => {
        const re = data.response
        this.tableData = re.list
        this.total = re.total
        this.queryParam.pageIndex = re.pageNum
        this.listLoading = false
      }).catch(() => { this.listLoading = false })
    },
    resetQuery () {
      this.queryParam.userName = ''
      this.queryParam.pageIndex = 1
      this.search()
    },
    changeStatus (row) {
      userApi.changeStatus(row.id).then(re => {
        if (re.code === 1) {
          row.status = re.response
          this.$message.success(re.message)
        } else {
          this.$message.error(re.message)
        }
      })
    },
    deleteUser (row) {
      this.$confirm(`确认删除管理员「${row.userName}」？删除后不可恢复。`, '删除确认', {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消'
      }).then(() => {
        userApi.deleteUser(row.id).then(re => {
          if (re.code === 1) {
            this.search()
            this.$message.success(re.message)
          } else {
            this.$message.error(re.message)
          }
        })
      }).catch(() => {})
    },
    submitForm () {
      this.queryParam.pageIndex = 1
      this.search()
    },
    sexFormatter (row, column, cellValue) {
      return this.enumFormat(this.sexEnum, cellValue)
    },
    statusFormatter (status) {
      return this.enumFormat(this.statusEnum, status)
    },
    statusTagFormatter (status) {
      return this.enumFormat(this.statusTag, status)
    },
    statusBtnFormatter (status) {
      return this.enumFormat(this.statusBtn, status)
    }
  },
  computed: {
    ...mapGetters('enumItem', [
      'enumFormat'
    ]),
    ...mapState('enumItem', {
      sexEnum: state => state.user.sexEnum,
      statusEnum: state => state.user.statusEnum,
      statusTag: state => state.user.statusTag,
      statusBtn: state => state.user.statusBtn
    })
  }
}
</script>
