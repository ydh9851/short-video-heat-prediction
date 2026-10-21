<template>
  <div class="sidebar-logo-container" :class="{'collapse':collapse}">
    <router-link class="sidebar-logo-link" to="/">
      <div class="logo-mark">
        <brand-mark />
      </div>
      <transition name="sidebarLogoFade">
        <div v-if="!collapse" key="expand" class="logo-text">
          <span class="logo-title">短视频热度预测</span>
          <span class="logo-sub">HEAT PREDICTION</span>
        </div>
      </transition>
    </router-link>
  </div>
</template>

<script>
import BrandMark from '@/components/BrandMark'

export default {
  name: 'SidebarLogo',
  components: { BrandMark },
  props: {
    collapse: {
      type: Boolean,
      required: true
    }
  }
}
</script>

<style lang="scss" scoped>
.sidebarLogoFade-enter-active {
  transition: opacity .4s;
}
.sidebarLogoFade-enter,
.sidebarLogoFade-leave-to {
  opacity: 0;
}

.sidebar-logo-container {
  position: relative;
  width: 100%;
  height: 64px;
  overflow: hidden;
  border-bottom: 1px solid #eef0f6;

  .sidebar-logo-link {
    height: 100%;
    width: 100%;
    display: flex;
    align-items: center;
    padding: 0 16px;
    gap: 11px;
    box-sizing: border-box;
  }

  .logo-mark {
    width: 38px;
    height: 38px;
    flex-shrink: 0;
    border-radius: 11px;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 55%, #a855f7 100%);
    box-shadow:
      0 6px 16px rgba(99, 102, 241, .38),
      inset 0 1px 0 rgba(255, 255, 255, .32);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;

    svg {
      width: 23px;
      height: 23px;
    }
  }

  .logo-text {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
    flex: 1;
    overflow: hidden;
  }

  .logo-title {
    font-size: 15px;
    font-weight: 700;
    color: #1e293b;
    line-height: 1.3;
    letter-spacing: .2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .logo-sub {
    font-size: 9.5px;
    font-weight: 600;
    color: #a3adc2;
    letter-spacing: .9px;
    line-height: 1.4;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  &.collapse {
    .sidebar-logo-link {
      padding: 0;
      justify-content: center;
    }
  }
}
</style>
