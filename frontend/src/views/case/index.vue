<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">场景库</div>
        <div class="page-desc">分析场景承载一次分析的完整先验输入（模型 / 类别 / 粉丝数 / 发布时刻）。设为当前场景后，预测与归因页将自动填充，全流程不重复输入。</div>
      </div>
      <div class="page-head-actions">
        <el-button type="primary" @click="openEdit(null)">新建场景</el-button>
      </div>
    </div>

    <el-card shadow="never" class="list-card">
      <div class="list-toolbar">
        <div class="list-toolbar-filters">
          <el-input v-model="queryParam.name" placeholder="按名称搜索" clearable style="width: 220px" @keyup.enter="submitForm" @clear="submitForm" />
          <el-button @click="submitForm">搜索</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </div>
        <div class="list-toolbar-actions">
          <span class="muted">共 {{ total }} 个场景</span>
        </div>
      </div>

      <el-table v-loading="listLoading" :data="tableData" stripe style="width: 100%">
        <el-table-column label="场景名称" min-width="160">
          <template #default="{ row }">
            <span class="case-name">{{ row.name }}</span>
            <el-tag v-if="isCurrent(row)" size="small" type="success" effect="plain" class="current-tag">当前</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model" label="模型" width="90">
          <template #default="{ row }">{{ row.model || 'lgbm' }}</template>
        </el-table-column>
        <el-table-column prop="videoCategory" label="类别" width="90" />
        <el-table-column label="粉丝数" width="110">
          <template #default="{ row }">{{ formatFans(row.authorFans) }}</template>
        </el-table-column>
        <el-table-column label="发布时间" width="150">
          <template #default="{ row }">{{ row.publishHour }}时 · 周{{ weekdayText(row.publishWeekday) }} · {{ row.publishMonth }}月</template>
        </el-table-column>
        <el-table-column label="来源" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.source === 'data-sample' ? '数据样本' : '手动创建' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="userName" label="创建人" width="110">
          <template #default="{ row }">{{ row.userName || '-' }}</template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="170" />
        <el-table-column label="操作" width="272" fixed="right">
          <template #default="{ row }">
            <div class="cell-actions">
              <el-button v-if="!isCurrent(row)" link type="success" @click="setCurrent(row)">设为当前</el-button>
              <el-button v-else link type="info" @click="clearCurrent">取消当前</el-button>
              <el-button link type="primary" @click="toggleCompare(row)">{{ isInCompare(row) ? '移出对比' : '加入对比' }}</el-button>
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="remove(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty><app-empty compact title="暂无场景，点击右上角「新建场景」" /></template>
      </el-table>

      <div class="list-footer">
        <pagination v-show="total > 0" :total="total" v-model:page="queryParam.pageIndex" v-model:limit="queryParam.pageSize" @pagination="search" />
      </div>
    </el-card>

    <el-dialog v-model="editVisible" :title="editForm.id ? '编辑场景' : '新建场景'" width="520px">
      <el-form label-position="top">
        <el-form-item label="场景名称" required>
          <el-input v-model="editForm.name" maxlength="50" show-word-limit placeholder="如：美食大号 · 周五晚间" />
        </el-form-item>
        <el-form-item label="场景描述">
          <el-input v-model="editForm.description" type="textarea" :rows="2" maxlength="200" placeholder="可选，记录该场景的分析意图" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="预测模型">
              <el-select v-model="editForm.model" style="width:100%">
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
              <el-select v-model="editForm.videoCategory" style="width:100%">
                <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="作者粉丝数">
          <el-input-number v-model="editForm.authorFans" :min="0" :step="10000" :controls="false" style="width:100%" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="发布小时">
              <el-input-number v-model="editForm.publishHour" :min="0" :max="23" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="发布星期">
              <el-select v-model="editForm.publishWeekday" style="width:100%">
                <el-option v-for="(w, i) in weekdays" :key="i" :label="w" :value="i" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="发布月份">
              <el-select v-model="editForm.publishMonth" style="width:100%">
                <el-option v-for="m in 12" :key="m" :label="m + ' 月'" :value="m" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { mapGetters, mapState } from 'vuex'
import Pagination from '@/components/Pagination'
import AppEmpty from '@/components/AppEmpty'
import caseApi from '@/api/case'

export default {
  name: 'CaseLibraryPage',
  components: { Pagination, AppEmpty },
  data () {
    return {
      queryParam: { name: '', pageIndex: 1, pageSize: 20 },
      listLoading: true,
      tableData: [],
      total: 0,
      editVisible: false,
      saving: false,
      editForm: this.emptyForm(),
      categories: ['搞笑', '美食', '音乐', '美妆', '穿搭', '舞蹈', '旅行', '宠物', '影视', '健身', '情感', '游戏', '生活', '知识'],
      weekdays: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    }
  },
  computed: {
    ...mapGetters(['currentCase']),
    ...mapState('caseCompare', ['items'])
  },
  created () {
    this.search()
  },
  methods: {
    emptyForm () {
      return {
        id: null,
        name: '',
        description: '',
        model: 'lgbm',
        videoCategory: '美食',
        authorFans: 50000,
        publishHour: 20,
        publishWeekday: 5,
        publishMonth: 6
      }
    },
    search () {
      this.listLoading = true
      caseApi.page(this.queryParam).then(data => {
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
      this.queryParam.name = ''
      this.queryParam.pageIndex = 1
      this.search()
    },
    isCurrent (row) {
      return this.currentCase && this.currentCase.id === row.id
    },
    setCurrent (row) {
      this.$store.dispatch('caseStudy/setCurrent', row)
      this.$message.success(`已设为当前场景：${row.name}`)
    },
    clearCurrent () {
      this.$store.dispatch('caseStudy/clearCurrent')
    },
    isInCompare (row) {
      return this.items.some(i => i.id === row.id)
    },
    toggleCompare (row) {
      if (this.isInCompare(row)) {
        this.$store.dispatch('caseCompare/remove', row.id)
        this.$message.info('已移出对比托盘')
      } else if (this.items.length >= 3) {
        this.$message.warning('对比托盘最多 3 个场景，请先在右下角托盘移出一个')
      } else {
        this.$store.dispatch('caseCompare/add', row)
        this.$message.success('已加入对比托盘，可在右下角发起对比')
      }
    },
    openEdit (row) {
      this.editForm = row ? { ...row } : this.emptyForm()
      this.editVisible = true
    },
    save () {
      if (!this.editForm.name || !this.editForm.videoCategory) {
        this.$message.warning('请填写场景名称与视频类别')
        return
      }
      this.saving = true
      const req = this.editForm.id
        ? caseApi.update(this.editForm.id, this.editForm)
        : caseApi.create(this.editForm)
      req.then(() => {
        this.$message.success('已保存')
        this.editVisible = false
        // 若编辑的正是当前场景，同步刷新上下文里的参数
        if (this.editForm.id && this.isCurrent(this.editForm)) {
          this.$store.dispatch('caseStudy/setCurrent', { ...this.editForm })
        }
        this.search()
      }).finally(() => { this.saving = false })
    },
    remove (row) {
      this.$confirm(`删除场景「${row.name}」？`, '删除确认', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      }).then(() => {
        caseApi.remove(row.id).then(() => {
          this.$message.success('已删除')
          if (this.isCurrent(row)) this.clearCurrent()
          this.search()
        })
      }).catch(() => {})
    },
    formatFans (v) {
      const n = Number(v || 0)
      if (n >= 10000) return (n / 10000).toFixed(1).replace(/\.0$/, '') + ' 万'
      return String(n)
    },
    weekdayText (w) {
      // 0=周一 … 6=周日（与预测页、算法侧一致）
      return ['一', '二', '三', '四', '五', '六', '日'][Number(w || 0)] || w
    }
  }
}
</script>

<style scoped>
.case-name {
  font-weight: 600;
  color: #1e293b;
}
.current-tag {
  margin-left: 8px;
}
</style>
