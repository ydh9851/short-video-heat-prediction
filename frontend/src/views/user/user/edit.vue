<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">{{ isEdit ? '编辑用户' : '新增用户' }}</div>
        <div class="page-desc">维护系统注册用户的账号、资料与兴趣标签，带 * 的为必填项。</div>
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
            <el-form-item label="等级" prop="userLevel">
              <el-select v-model="form.userLevel" placeholder="请选择用户等级" style="width:100%">
                <el-option v-for="item in levelEnum" :key="item.key" :value="item.key" :label="item.value" />
              </el-select>
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
        <div class="form-tip">密码仅在新增或重置时填写；等级决定该账号可访问的功能范围。</div>
      </el-card>

      <!-- 基本资料 -->
      <el-card shadow="never" class="form-card">
        <div class="section-title">基本资料</div>
        <el-row :gutter="24">
          <el-col :xs="24" :sm="12">
            <el-form-item label="真实姓名" prop="realName">
              <el-input v-model="form.realName" placeholder="用户真实姓名" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="手机号">
              <el-input v-model="form.phone" placeholder="选填，用于找回账号" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="年龄">
              <el-input v-model="form.age" placeholder="选填" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="性别">
              <el-select v-model="form.sex" placeholder="选填" clearable style="width:100%">
                <el-option v-for="item in sexEnum" :key="item.key" :value="item.key" :label="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
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
              <el-input v-model="form.job" placeholder="选填，如：产品经理 / 学生" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="城市">
              <el-input v-model="form.city" placeholder="选填，如：杭州" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-card>

      <!-- 兴趣标签 -->
      <el-card shadow="never" class="form-card">
        <div class="section-title">
          兴趣标签
          <span class="title-count">{{ form.userTagList.length }} 个</span>
        </div>
        <el-form-item label="标签">
          <div class="tag-box">
            <el-tag
              v-for="(t, i) in form.userTagList"
              :key="i"
              closable
              class="tag-item"
              @close="removeTag(i)">{{ t.tagName || '未命名' }}</el-tag>
            <span v-if="!form.userTagList.length" class="tag-empty">还没有标签，添加几个感兴趣的内容方向吧</span>
          </div>
        </el-form-item>
        <el-form-item label="添加标签">
          <el-input
            v-model="tagInput"
            placeholder="输入标签后按回车添加，如：篮球 / 美食"
            style="max-width:320px"
            @keyup.enter="addTag">
            <template #append>
              <el-button @click="addTag">添加</el-button>
            </template>
          </el-input>
        </el-form-item>
        <div class="form-tip">标签用于刻画用户兴趣偏好，重复标签会被自动忽略。</div>
      </el-card>

      <!-- 操作 -->
      <el-card shadow="never" class="action-card">
        <el-button type="primary" :loading="formLoading" @click="submitForm">提交保存</el-button>
        <el-button @click="resetForm">重置</el-button>
        <span class="form-tip" style="margin-left:14px">提交后将返回用户列表。</span>
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
        role: 1,
        status: 1,
        age: '',
        sex: '',
        birthDay: null,
        phone: null,
        userLevel: null,
        job: null,
        city: null,
        userTagList: []
      },
      tagInput: '',
      formLoading: false,
      rules: {
        userName: [
          { required: true, message: '请输入用户名', trigger: 'blur' }
        ],
        realName: [
          { required: true, message: '请输入真实姓名', trigger: 'blur' }
        ],
        userLevel: [
          { required: true, message: '请选择等级', trigger: 'change' }
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
      statusEnum: state => state.user.statusEnum,
      levelEnum: state => state.user.levelEnum
    })
  },
  created () {
    const id = this.$route.query.id
    if (id && parseInt(id) !== 0) {
      this.formLoading = true
      userApi.selectUser(id).then(re => {
        this.form = re.response
        if (!this.form.userTagList) this.form.userTagList = []
        this.formLoading = false
      }).catch(() => { this.formLoading = false })
    }
  },
  methods: {
    addTag () {
      const name = (this.tagInput || '').trim()
      if (!name) return
      if (this.form.userTagList.some(t => t.tagName === name)) {
        this.tagInput = ''
        this.$message.info('该标签已存在')
        return
      }
      this.form.userTagList.push({ tagName: name })
      this.tagInput = ''
    },
    removeTag (i) {
      this.form.userTagList.splice(i, 1)
    },
    goBack () {
      this.delCurrentView(this).then(() => {
        this.$router.push('/user/user/list')
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
              this.$router.push('/user/user/list')
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
      this.tagInput = ''
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

.title-count {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--app-text-3);
}

.tag-box {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-height: 32px;
}
.tag-item {
  font-size: 12.5px;
}
.tag-empty {
  font-size: 12.5px;
  color: var(--app-text-3);
}
</style>
