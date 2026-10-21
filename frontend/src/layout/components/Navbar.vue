<template>
  <div class="navbar">
    <div class="navbar-left">
      <div class="hamburger-container" @click="toggleSideBar">
        <hamburger id="hamburger-container" :is-active="sidebar.opened" />
      </div>
      <breadcrumb id="breadcrumb-container" class="breadcrumb-container" />
    </div>

    <div class="right-menu">
      <div class="right-menu-item hover-effect" :title="isFullscreen ? '退出全屏' : '全屏'" @click="toggleFullscreen">
        <svg-icon :icon-class="isFullscreen ? 'exit-fullscreen' : 'fullscreen'" />
      </div>

      <el-divider direction="vertical" class="navbar-divider" />

      <el-dropdown class="avatar-container" trigger="click">
        <div class="avatar-wrapper">
          <div class="avatar-circle">{{ avatarText }}</div>
          <div class="user-meta">
            <span class="user-name">{{ userName || '未登录' }}</span>
            <span class="user-role">系统管理员</span>
          </div>
          <svg class="caret" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <router-link to="/profile/index">
              <el-dropdown-item>个人中心</el-dropdown-item>
            </router-link>
            <router-link to="/">
              <el-dropdown-item>回到首页</el-dropdown-item>
            </router-link>
            <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script>
import { mapGetters, mapMutations } from 'vuex'
import loginApi from '@/api/login'
import Breadcrumb from '@/components/Breadcrumb'
import Hamburger from '@/components/Hamburger'

export default {
  components: {
    Breadcrumb,
    Hamburger
  },
  data () {
    return {
      isFullscreen: false
    }
  },
  computed: {
    ...mapGetters([
      'sidebar',
      'userName'
    ]),
    avatarText () {
      const n = this.userName || ''
      return n ? n.charAt(0).toUpperCase() : 'A'
    }
  },
  methods: {
    toggleSideBar () {
      this.$store.dispatch('app/toggleSideBar')
    },
    toggleFullscreen () {
      const el = document.documentElement
      if (!document.fullscreenElement) {
        el.requestFullscreen && el.requestFullscreen()
      } else {
        document.exitFullscreen && document.exitFullscreen()
      }
    },
    onFullscreenChange () {
      this.isFullscreen = !!document.fullscreenElement
    },
    logout () {
      loginApi.logout().then(() => {
        this.clearLogin()
        this.$router.push({ path: '/login' })
      }).catch(() => {
        // 即使后端登出异常，也保证前端清除登录态
        this.clearLogin()
        this.$router.push({ path: '/login' })
      })
    },
    ...mapMutations('user', ['clearLogin'])
  },
  mounted () {
    document.addEventListener('fullscreenchange', this.onFullscreenChange)
  },
  beforeUnmount () {
    document.removeEventListener('fullscreenchange', this.onFullscreenChange)
  }
}
</script>

<style lang="scss" scoped>
.navbar {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #eef0f6;

  .navbar-left {
    display: flex;
    align-items: center;
    height: 100%;
    min-width: 0;
  }

  .hamburger-container {
    height: 100%;
    display: flex;
    align-items: center;
    padding: 0 16px;
    cursor: pointer;
    transition: background .2s;
    -webkit-tap-highlight-color: transparent;

    &:hover {
      background: rgba(99, 102, 241, .06);
    }
  }

  .breadcrumb-container {
    min-width: 0;
  }

  .right-menu {
    display: flex;
    align-items: center;
    height: 100%;
    padding-right: 18px;

    .right-menu-item {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border-radius: 10px;
      font-size: 17px;
      color: #64748b;
      cursor: pointer;
      transition: background .2s, color .2s;

      &:hover {
        background: rgba(99, 102, 241, .08);
        color: #6366f1;
      }
    }
  }

  .navbar-divider {
    height: 22px;
    margin: 0 10px;
    border-color: #eef0f6;
  }

  .avatar-container {
    outline: none;
  }

  .avatar-wrapper {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 5px 8px;
    border-radius: 12px;
    cursor: pointer;
    transition: background .2s;

    &:hover {
      background: rgba(99, 102, 241, .06);
    }

    .avatar-circle {
      width: 34px;
      height: 34px;
      border-radius: 10px;
      background: linear-gradient(135deg, #6366f1, #a855f7);
      color: #fff;
      font-size: 15px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 10px rgba(99, 102, 241, .32);
    }

    .user-meta {
      display: flex;
      flex-direction: column;
      line-height: 1.25;

      .user-name {
        font-size: 13.5px;
        font-weight: 600;
        color: #1e293b;
      }
      .user-role {
        font-size: 11px;
        color: #94a3b8;
      }
    }

    .caret {
      width: 12px;
      height: 12px;
      color: #94a3b8;
      flex-shrink: 0;
    }
  }
}
</style>
