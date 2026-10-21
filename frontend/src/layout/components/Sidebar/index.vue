<template>
  <div class="has-logo">
    <logo :collapse="isCollapse" />
    <el-scrollbar wrap-class="scrollbar-wrapper">
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :background-color="variables.menuBg"
        :text-color="variables.menuText"
        :unique-opened="true"
        :active-text-color="variables.menuActiveText"
        :collapse-transition="false"
        :router="true"
        mode="vertical"
      >
        <template v-for="(item, index) in menuItems" :key="item.path">
          <!-- 分组标题（非折叠态显示，仅作视觉分组，不可折叠） -->
          <div
            v-if="!isCollapse && (index === 0 || menuItems[index - 1].group !== item.group)"
            class="menu-group-label"
          >
            {{ item.group }}
          </div>
          <!-- 折叠态：用细分隔线替代分组标题 -->
          <div
            v-else-if="isCollapse && index !== 0 && menuItems[index - 1].group !== item.group"
            class="menu-group-line"
          />
          <el-menu-item :index="item.path" class="menu-leaf">
            <svg-icon :icon-class="item.icon" />
            <span>{{ item.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-scrollbar>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import Logo from './Logo'
import variables from '@/styles/variables.js'

// 分组顺序（决定侧边栏中分组的排列）
const GROUP_ORDER = ['项目概览', '数据与特征', '模型与归因', '系统管理']

// 把嵌套路由压平成「扁平菜单项」，每项只带 { path, title, icon, group }
function flattenRoutes (routes, basePath, out) {
  routes.forEach(route => {
    if (route.hidden) return
    const children = (route.children || []).filter(c => !c.hidden)
    if (children.length) {
      flattenRoutes(children, route.path ? joinPath(basePath, route.path) : basePath, out)
      return
    }
    const meta = route.meta || {}
    if (!meta.title) return
    out.push({
      path: joinPath(basePath, route.path),
      title: meta.title,
      icon: meta.icon || 'list',
      group: meta.group || '其他'
    })
  })
}

function joinPath (base, path) {
  return (base + '/' + path).replace(/\/{2,}/g, '/')
}

export default {
  components: { Logo },
  computed: {
    ...mapGetters(['sidebar', 'routes']),
    activeMenu () {
      const route = this.$route
      const { meta, path } = route
      if (meta.activeMenu) {
        return meta.activeMenu
      }
      return path
    },
    variables () {
      return variables
    },
    isCollapse () {
      return !this.sidebar.opened
    },
    menuItems () {
      const out = []
      flattenRoutes(this.routes, '', out)
      return out.sort((a, b) => {
        const gi = GROUP_ORDER.indexOf(a.group)
        const gj = GROUP_ORDER.indexOf(b.group)
        return (gi < 0 ? 99 : gi) - (gj < 0 ? 99 : gj)
      })
    }
  }
}
</script>
