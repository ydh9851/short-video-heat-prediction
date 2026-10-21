<template>
  <div class="login-page">
    <!-- 左侧品牌区 -->
    <aside class="brand-panel">
      <div class="brand-glow brand-glow-1" />
      <div class="brand-glow brand-glow-2" />
      <div class="brand-grid" />

      <div class="brand-inner">
        <div class="brand-logo">
          <div class="brand-mark">
            <brand-mark />
          </div>
          <span class="brand-name">短视频热度预测</span>
        </div>

        <h1 class="brand-title">短视频热度预测与<br />归因分析系统</h1>
        <p class="brand-sub">
          基于 LightGBM 的多模型热度预测、SHAP 归因解释与 K-Means 热度分级，
          让每一条内容「为什么火」有据可循。
        </p>

        <ul class="brand-features">
          <li v-for="f in features" :key="f.title">
            <span class="feature-dot" />
            <div>
              <strong>{{ f.title }}</strong>
              <em>{{ f.desc }}</em>
            </div>
          </li>
        </ul>

        <div class="brand-stats">
          <div class="brand-stat">
            <b>36,381</b>
            <span>数据样本</span>
          </div>
          <div class="brand-stat">
            <b>6</b>
            <span>对比模型</span>
          </div>
          <div class="brand-stat">
            <b>13</b>
            <span>EDA 图组</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧表单区 -->
    <main class="form-panel">
      <div class="form-card">
        <div class="form-head">
          <h2>欢迎回来</h2>
          <p>请登录以继续使用管理系统</p>
        </div>

        <el-form ref="loginForm" :model="loginForm" :rules="loginRules" class="login-form" @submit.prevent>
          <el-form-item prop="userName">
            <label class="field-label">用户名</label>
            <el-input
              ref="userName"
              v-model="loginForm.userName"
              placeholder="请输入用户名"
              name="userName"
              type="text"
              tabindex="1"
              autocomplete="on">
              <template #prefix>
                <svg-icon icon-class="user" class="input-icon" />
              </template>
            </el-input>
          </el-form-item>

          <el-form-item prop="password">
            <label class="field-label">密码</label>
            <el-input
              ref="password"
              v-model="loginForm.password"
              :type="passwordType"
              placeholder="请输入密码"
              name="password"
              tabindex="2"
              autocomplete="on"
              @keyup.enter="handleLogin">
              <template #prefix>
                <svg-icon icon-class="lock" class="input-icon" />
              </template>
              <template #suffix>
                <span class="pwd-eye" @click="showPwd">
                  <svg-icon :icon-class="passwordType === 'password' ? 'eye' : 'eye-open'" />
                </span>
              </template>
            </el-input>
          </el-form-item>

          <div class="form-row">
            <el-checkbox v-model="loginForm.remember">记住我</el-checkbox>
            <span class="forgot" @click="tipForgot">忘记密码？</span>
          </div>

          <el-button type="primary" :loading="loading" class="login-btn" @click="handleLogin">
            登 录
          </el-button>
        </el-form>

        <div class="demo-tip">
          <span class="demo-badge">演示账号</span>
          <span>admin / 123456</span>
          <span class="demo-fill" @click="fillDemo">一键填入</span>
        </div>
      </div>

      <footer class="form-footer">
        © 2026 短视频热度预测与归因分析系统 · 毕业设计
      </footer>
    </main>
  </div>
</template>

<script>
import { mapMutations } from 'vuex'
import loginApi from '@/api/login'
import BrandMark from '@/components/BrandMark'

export default {
  name: 'Login',
  components: { BrandMark },
  data () {
    const validateUsername = (rule, value, callback) => {
      if (!value || value.length < 5) {
        callback(new Error('用户名不能少于5个字符'))
      } else {
        callback()
      }
    }
    const validatePassword = (rule, value, callback) => {
      if (!value || value.length < 5) {
        callback(new Error('密码不能少于5个字符'))
      } else {
        callback()
      }
    }
    return {
      features: [
        { title: '多模型热度预测', desc: 'LightGBM / XGBoost / 随机森林等 6 模型横向对比' },
        { title: 'SHAP 归因解释', desc: '定位每条视频火与不火的关键特征' },
        { title: '热度分级与 EDA', desc: 'K-Means 自动分级，13 组探索性图表' }
      ],
      loginForm: {
        userName: '',
        password: '',
        remember: false
      },
      loginRules: {
        userName: [{ required: true, trigger: 'blur', validator: validateUsername }],
        password: [{ required: true, trigger: 'blur', validator: validatePassword }]
      },
      passwordType: 'password',
      loading: false
    }
  },
  mounted () {
    if (this.loginForm.userName === '') {
      this.$refs.userName.focus()
    } else if (this.loginForm.password === '') {
      this.$refs.password.focus()
    }
  },
  methods: {
    fillDemo () {
      this.loginForm.userName = 'admin'
      this.loginForm.password = '123456'
    },
    tipForgot () {
      this.$message.info('演示环境请使用演示账号 admin / 123456 登录')
    },
    showPwd () {
      this.passwordType = this.passwordType === 'password' ? '' : 'password'
      this.$nextTick(() => {
        this.$refs.password.focus()
      })
    },
    handleLogin () {
      this.$refs.loginForm.validate(valid => {
        if (!valid) return false
        this.loading = true
        loginApi.login(this.loginForm).then(result => {
          if (result && result.code === 1) {
            this.setUserName(this.loginForm.userName)
            this.$router.push({ path: '/' })
          } else {
            this.loading = false
            this.$message.error((result && result.message) || '登录失败，请检查账号密码')
          }
        }).catch(() => {
          this.loading = false
        })
      })
    },
    ...mapMutations('user', ['setUserName'])
  }
}
</script>

<style lang="scss" scoped>
$brand-gradient: linear-gradient(145deg, #4f46e5 0%, #6366f1 42%, #8b5cf6 72%, #a855f7 100%);

.login-page {
  min-height: 100vh;
  width: 100%;
  display: flex;
  background: #fff;
}

/* ---------------- 左侧品牌区 ---------------- */
.brand-panel {
  position: relative;
  flex: 1 1 56%;
  overflow: hidden;
  background: $brand-gradient;
  color: #fff;
  display: flex;
  align-items: center;
  padding: 60px 68px;

  .brand-glow {
    position: absolute;
    border-radius: 50%;
    filter: blur(70px);
    opacity: .5;
    pointer-events: none;
  }
  .brand-glow-1 {
    width: 420px;
    height: 420px;
    background: #c084fc;
    top: -120px;
    right: -80px;
  }
  .brand-glow-2 {
    width: 360px;
    height: 360px;
    background: #38bdf8;
    bottom: -140px;
    left: -60px;
    opacity: .35;
  }
  .brand-grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(255, 255, 255, .08) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 255, 255, .08) 1px, transparent 1px);
    background-size: 46px 46px;
    mask-image: radial-gradient(circle at 30% 40%, #000 0%, transparent 72%);
    pointer-events: none;
  }

  .brand-inner {
    position: relative;
    z-index: 2;
    max-width: 520px;
  }

  .brand-logo {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 40px;

    .brand-mark {
      width: 42px;
      height: 42px;
      border-radius: 12px;
      background: rgba(255, 255, 255, .18);
      border: 1px solid rgba(255, 255, 255, .3);
      display: flex;
      align-items: center;
      justify-content: center;
      backdrop-filter: blur(4px);

      svg {
        width: 24px;
        height: 24px;
      }
    }
    .brand-name {
      font-size: 17px;
      font-weight: 700;
      letter-spacing: .5px;
    }
  }

  .brand-title {
    font-size: 38px;
    line-height: 1.32;
    font-weight: 800;
    margin: 0 0 20px;
    letter-spacing: .6px;
    text-shadow: 0 4px 24px rgba(0, 0, 0, .18);
  }

  .brand-sub {
    font-size: 14.5px;
    line-height: 1.9;
    color: rgba(255, 255, 255, .86);
    margin: 0 0 36px;
    max-width: 430px;
  }

  .brand-features {
    list-style: none;
    margin: 0 0 40px;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;

    li {
      display: flex;
      align-items: flex-start;
      gap: 12px;
    }

    .feature-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #fff;
      margin-top: 7px;
      box-shadow: 0 0 0 4px rgba(255, 255, 255, .22);
      flex-shrink: 0;
    }

    strong {
      display: block;
      font-size: 14.5px;
      font-weight: 650;
    }
    em {
      display: block;
      font-style: normal;
      font-size: 12.5px;
      color: rgba(255, 255, 255, .72);
      margin-top: 3px;
    }
  }

  .brand-stats {
    display: flex;
    gap: 34px;
    padding-top: 28px;
    border-top: 1px solid rgba(255, 255, 255, .22);

    .brand-stat {
      display: flex;
      flex-direction: column;

      b {
        font-size: 24px;
        font-weight: 800;
        letter-spacing: .5px;
      }
      span {
        font-size: 12px;
        color: rgba(255, 255, 255, .74);
        margin-top: 4px;
      }
    }
  }
}

/* ---------------- 右侧表单区 ---------------- */
.form-panel {
  flex: 1 1 44%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 48px;
  background: #fbfcfe;
  position: relative;
}

.form-card {
  width: 100%;
  max-width: 400px;
}

.form-head {
  margin-bottom: 30px;

  h2 {
    font-size: 26px;
    font-weight: 700;
    color: #1e293b;
    margin: 0 0 8px;
    letter-spacing: .3px;
  }
  p {
    font-size: 13.5px;
    color: #94a3b8;
    margin: 0;
  }
}

.field-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 7px;
}

.login-form {
  ::v-deep .el-form-item {
    margin-bottom: 20px;
    display: block;
  }
  ::v-deep .el-form-item__content {
    display: block;
    line-height: normal;
  }
  ::v-deep .el-input__wrapper {
    border-radius: 11px;
    padding: 4px 14px;
    box-shadow: 0 0 0 1px #e3e7ef inset;
    background: #fff;
    transition: box-shadow .2s ease;
  }
  ::v-deep .el-input__wrapper.is-focus {
    box-shadow: 0 0 0 1px #6366f1 inset, 0 0 0 4px rgba(99, 102, 241, .13);
  }
  ::v-deep .el-input__inner {
    height: 42px;
    font-size: 14px;
  }
}

.input-icon {
  font-size: 16px;
  color: #a3adc2;
}

.pwd-eye {
  cursor: pointer;
  color: #a3adc2;
  font-size: 16px;
  display: inline-flex;
  align-items: center;

  &:hover {
    color: #6366f1;
  }
}

.form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 4px 0 22px;

  .forgot {
    font-size: 13px;
    color: #6366f1;
    cursor: pointer;

    &:hover {
      color: #4f52c1;
    }
  }
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 15.5px;
  font-weight: 600;
  letter-spacing: 4px;
  border-radius: 11px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  box-shadow: 0 10px 24px rgba(99, 102, 241, .34);

  &:hover {
    box-shadow: 0 14px 30px rgba(99, 102, 241, .42);
    transform: translateY(-1px);
  }
}

.demo-tip {
  margin-top: 26px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 11px;
  background: #f2f4fb;
  border: 1px dashed #d5daf0;
  font-size: 12.5px;
  color: #64748b;

  .demo-badge {
    background: #6366f1;
    color: #fff;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
  }
  .demo-fill {
    margin-left: auto;
    color: #6366f1;
    font-weight: 600;
    cursor: pointer;

    &:hover {
      color: #4f52c1;
    }
  }
}

.form-footer {
  position: absolute;
  bottom: 26px;
  font-size: 12px;
  color: #b6bec9;
}

@media (max-width: 960px) {
  .brand-panel {
    display: none;
  }
  .form-panel {
    flex: 1 1 100%;
    background: #fff;
  }
}
</style>
