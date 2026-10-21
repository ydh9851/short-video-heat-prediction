<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">用户详情</div>
        <div class="page-desc">查看用户基础信息及其行为记录（喜好标签、播放记录、操作记录与推荐记录）。</div>
      </div>
    </div>

    <el-card shadow="never" style="margin-bottom:16px" v-loading="formLoading">
      <div class="section-title">基础信息</div>
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="用户名">{{ orDash(form.userName) }}</el-descriptions-item>
        <el-descriptions-item label="真实姓名">{{ orDash(form.realName) }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ enumFormat(sexEnum, form.sex) || orDash(form.sex) }}</el-descriptions-item>
        <el-descriptions-item label="年龄">{{ orDash(form.age) }}</el-descriptions-item>
        <el-descriptions-item label="职业">{{ orDash(form.job) }}</el-descriptions-item>
        <el-descriptions-item label="城市">{{ orDash(form.city) }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ orDash(form.phone) }}</el-descriptions-item>
        <el-descriptions-item label="身份">{{ enumFormat(roleEnum, form.role) || orDash(form.role) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ orDash(form.createTime) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-tabs v-model="tab" type="border-card">
      <el-tab-pane :label="'用户喜好 (' + (form.userTagList || []).length + ')'" name="tag">
        <el-table :data="form.userTagList || []" size="small" stripe>
          <el-table-column type="index" label="#" width="70" />
          <el-table-column prop="tagName" label="喜好标签" />
          <template #empty><el-empty description="暂无喜好标签记录" :image-size="70" /></template>
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="'播放记录 (' + (form.userPlayList || []).length + ')'" name="play">
        <el-table :data="form.userPlayList || []" size="small" stripe>
          <el-table-column type="index" label="#" width="70" />
          <el-table-column prop="videoName" label="视频名称" />
          <el-table-column prop="createTime" label="播放时间" width="180" />
          <template #empty><el-empty description="暂无播放记录" :image-size="70" /></template>
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="'视频操作 (' + (form.userOperationList || []).length + ')'" name="op">
        <el-table :data="form.userOperationList || []" size="small" stripe>
          <el-table-column type="index" label="#" width="70" />
          <el-table-column prop="videoName" label="视频名称" />
          <el-table-column prop="operationName" label="操作类型" width="160" />
          <el-table-column prop="createTime" label="操作时间" width="180" />
          <template #empty><el-empty description="暂无操作记录" :image-size="70" /></template>
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="'视频推荐 (' + (form.userRecommendList || []).length + ')'" name="rec">
        <el-table :data="form.userRecommendList || []" size="small" stripe>
          <el-table-column type="index" label="#" width="70" />
          <el-table-column prop="title" label="推荐内容" />
          <el-table-column prop="createTime" label="推荐时间" width="180" />
          <template #empty><el-empty description="暂无推荐记录" :image-size="70" /></template>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import { mapGetters, mapState } from 'vuex'
import userApi from '@/api/user'

export default {
  data () {
    return {
      tab: 'tag',
      form: {
        id: null,
        userName: '',
        userPlayList: [],
        userOperationList: [],
        userTagList: [],
        userRecommendList: [],
        subscription: null
      },
      formLoading: false
    }
  },
  created () {
    const id = this.$route.query.id
    if (id && parseInt(id) !== 0) {
      this.formLoading = true
      userApi.getUserDetailByUserId(id).then(re => {
        this.form = re.response || {}
        this.formLoading = false
      }).catch(() => { this.formLoading = false })
    }
  },
  methods: {
    orDash (v) {
      return (v === null || v === undefined || v === '') ? '-' : v
    }
  },
  computed: {
    ...mapGetters('enumItem', ['enumFormat']),
    ...mapState('enumItem', {
      sexEnum: state => state.user.sexEnum,
      roleEnum: state => state.user.roleEnum
    })
  }
}
</script>
