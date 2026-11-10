<template>
  <!-- 大屏 standalone：跳过侧栏/顶栏/托盘，只渲染子路由（拿到真正 100vw×100vh） -->
  <router-view v-if="isStandalone" />
  <div v-else :class="classObj" class="app-wrapper">
    <div v-if="device==='mobile'&&sidebar.opened" class="drawer-bg" @click="handleClickOutside" />
    <sidebar class="sidebar-container" />
    <div  class="hasTagsView main-container">
      <div class="fixed-header">
        <navbar />
        <tags-view/>
      </div>
      <app-main />
      <scenario-compare-tray />
      <command-palette ref="command" @start-tour="tourVisible = true" />
      <demo-tour :visible="tourVisible" @close="tourVisible = false" />
      <back-to-top :visibility-height="100" :back-position="0" transition-name="fade" ref="backTop"/>
    </div>
  </div>
</template>

<script>
import { AppMain, Navbar, Sidebar, TagsView } from './components'
import ResizeMixin from './mixin/ResizeHandler'
import { mapState } from 'vuex'
import BackToTop from '@/components/BackToTop'
import ScenarioCompareTray from '@/components/ScenarioCompareTray'
import CommandPalette from '@/components/CommandPalette'
import DemoTour from '@/components/DemoTour'
export default {
  name: 'Layout',
  components: {
    AppMain,
    Navbar,
    Sidebar,
    TagsView,
    BackToTop,
    ScenarioCompareTray,
    CommandPalette,
    DemoTour
  },
  mixins: [ResizeMixin],
  data () {
    return {
      tourVisible: false
    }
  },
  computed: {
    ...mapState({
      sidebar: state => state.app.sidebar,
      device: state => state.app.device
    }),
    classObj () {
      return {
        hideSidebar: !this.sidebar.opened,
        openSidebar: this.sidebar.opened,
        withoutAnimation: this.sidebar.withoutAnimation,
        mobile: this.device === 'mobile'
      }
    },
    isStandalone () {
      // 任一级别 route 的 meta.standalone 为 true 时跳过外壳
      return this.$route.matched.some(r => r.meta && r.meta.standalone)
    }
  },
  methods: {
    handleClickOutside () {
      this.$store.dispatch('app/closeSideBar', { withoutAnimation: false })
    },
    openCommand () {
      if (this.$refs.command) this.$refs.command.open()
    },
    startTour () {
      this.tourVisible = true
    }
  },
  mounted () {
    this.$root.$on('app:command', this.openCommand)
    this.$root.$on('app:tour', this.startTour)
  },
  beforeUnmount () {
    this.$root.$off('app:command', this.openCommand)
    this.$root.$off('app:tour', this.startTour)
  }
}
</script>

<style lang="scss" scoped>
  @import "@/styles/mixin.scss";
  @import "@/styles/variables.scss";

  .app-wrapper {
    @include clearfix;
    position: relative;
    height: 100%;
    width: 100%;

    &.mobile.openSidebar {
      position: fixed;
      top: 0;
    }
  }

  .drawer-bg {
    background: #000;
    opacity: 0.3;
    width: 100%;
    top: 0;
    height: 100%;
    position: absolute;
    z-index: 999;
  }

  .fixed-header {
    position: fixed;
    top: 0;
    right: 0;
    z-index: 9;
    width: calc(100% - #{$sideBarWidth});
    background: #fff;
    transition: width 0.28s;
  }

  .hideSidebar .fixed-header {
    width: calc(100% - 64px)
  }

  .mobile .fixed-header {
    width: 100%;
  }

</style>
