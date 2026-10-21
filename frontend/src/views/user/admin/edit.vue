<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">{{ isEdit ? '编辑管理员' : '新增管理员' }}</div>
        <div class="page-desc">维护后台管理员账号与联系方式，带 * 的为必填项。</div>
      </div>
      <div class="page-head-actions">
        <el-button @click="goBack">返回列表</el-button>
      </div>
    </div>

    <el-form ref="form" :model="form" label-width="96px" v-loading="formLoading" :rules="rules">
      <!-- 账号信息 -->
      <el-card shadow="never" class="form-card">
        <div class="section-title">账号信息</div>
        <el-row :gutter="24">
          <el-col :xs="24" :sm="12">
            <el-form-item label="用户名" prop="userName">
              <el-input v-model="form.userName" placeholder="登录账号，全局唯一" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="密码" prop="password">
              <el-input v-model="form.password" type="password" show-password placeholder="登录密码" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="真实姓名" prop="realName">
              <el-input v-model="form.realName" placeholder="管理员真实姓名" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" placeholder="请选择账号状态" style="width:100%">
                <el-option v-for="item in statusEnum" :key="item.key" :value="item.key" :label="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <div class="form-tip">管理员账号默认角色为「管理员」，可登录后台进行数据、模型与用户管理。</div>
      </el-card>

      <!-- 基本资料 -->
      <el-card shadow="never" class="form-card">
        <div class="section-title">基本资料</div>
        <el-row :gutter="24">
          <el-col :xs="24" :sm="12">
            <el-form-item label="手机号">
              <el-input v-model="form.phone" placeholder="选填，用于找回账号" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="6">
            <el-form-item label="年龄">
              <el-input v-model="form.age" placeholder="选填" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="6">
            <el-form-item label="性别">
              <el-select v-model="form.sex" placeholder="选填" clearable style="width:100%">
                <el-option v-for="item in sexEnum" :key="item.key" :value="item.key" :label="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="出生日期">
              <el-date-picker
                v-model="form.birthDay"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选填"
                style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-card>

      <!-- 职业与地区 -->
      <el-card shadow="never" class="form-card">
        <div class="section-title">职业与地区</div>
        <el-row :gutter="24">
          <el-col :xs="24" :sm="12">
            <el-form-item label="职业">
              <el-input v-model="form.job" placeholder="选填，如：数据工程师" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="所在城市">
              <el-input v-model="form.city" placeholder="选填，如：上海" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-card>

      <!-- 操作 -->
      <el-card shadow="never" class="action-card">
        <el-button type="primary" :loading="formLoading" @click="submitForm">提交保存</el-button>
        <el-button @click="resetForm">重置</el-button>
        <span class="form-tip" style="margin-left:14px">提交后将返回管理员列表。</span>
      </el-card>
    </el-form>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'
import userApi from '@/api/user'

export default {
  data () {
    return {
      form: {
        id: null,
        userName: '',
        password: '',
        realName: '',
        role: 3,
        status: 1,
        age: '',
        sex: '',
        birthDay: null,
        phone: null,
        job: null,
        city: null
      },
      formLoading: false,
      rules: {
        userName: [
          { required: true, message: '请输入用户名', trigger: 'blur' }
        ],
        realName: [
          { required: true, message: '请输入真实姓名', trigger: 'blur' }
        ],
        status: [
          { required: true, message: '请选择状态', trigger: 'change' }
        ]
      }
    }
  },
  computed: {
    isEdit () {
      return !!(this.$route.query.id && parseInt(this.$route.query.id) !== 0)
    },
    ...mapState('enumItem', {
      sexEnum: state => state.user.sexEnum,
      roleEnum: state => state.user.roleEnum,
      statusEnum: state => state.user.statusEnum
    })
  },
  created () {
    const id = this.$route.query.id
    if (id && parseInt(id) !== 0) {
      this.formLoading = true
      userApi.selectUser(id).then(re => {
        this.form = re.response
        this.formLoading = false
      }).catch(() => { this.formLoading = false })
    }
  },
  methods: {
    goBack () {
      this.delCurrentView(this).then(() => {
        this.$router.push('/user/admin/list')
      })
    },
    submitForm () {
      this.$refs.form.validate((valid) => {
        if (!valid) return false
        this.formLoading = true
        userApi.createUser(this.form).then(data => {
          if (data.code === 1) {
            this.$message.success(data.message)
            this.delCurrentView(this).then(() => {
              this.$router.push('/user/admin/list')
            })
          } else {
            this.$message.error(data.message)
            this.formLoading = false
          }
        }).catch(() => { this.formLoading = false })
      })
    },
    resetForm () {
      this.$refs.form.resetFields()
    },
    ...mapActions('tagsView', { delCurrentView: 'delCurrentView' })
  }
}
</script>

<style lang="scss" scoped>
.app-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-card {
  .el-row {
    margin-bottom: -4px;
  }
}

.action-card {
  :deep(.el-card__body) {
    display: flex;
    align-items: center;
  }
}
</style>
