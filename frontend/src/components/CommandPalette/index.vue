<template>
  <el-dialog
    v-model="visible"
    width="560px"
    :show-close="false"
    append-to-body
    class="cmd-dialog"
    @opened="focusInput"
    @closed="reset">
    <div class="cmd-box">
      <div class="cmd-input">
        <span class="cmd-mark">⌘</span>
        <el-input
          ref="input"
          v-model="keyword"
          placeholder="搜索页面或操作…"
          clearable
          @keydown.down.prevent="move(1)"
          @keydown.up.prevent="move(-1)"
          @keydown.enter.prevent="runActive"
          @keydown.esc="close" />
        <span class="cmd-esc">ESC</span>
      </div>

      <div v-if="grouped.length" class="cmd-list">
        <template v-for="group in grouped" :key="group.label">
          <div class="cmd-group">{{ group.label }}</div>
          <div
            v-for="c in group.items"
            :key="c.id"
            class="cmd-item"
            :class="{ active: c.id === activeId }"
            @mouseenter="activeId = c.id"
            @click="run(c)">
            <span class="ci-icon">{{ c.icon }}</span>
            <span class="ci-label">{{ c.label }}</span>
            <span class="ci-hint">{{ c.hint }}</span>
          </div>
        </template>
      </div>
      <div v-else class="cmd-empty">没有匹配的命令</div>

      <div class="cmd-foot">↑↓ 选择 · Enter 执行 · Esc 关闭</div>
    </div>
  </el-dialog>
</template>

<script>
/**
 * 命令面板：Ctrl / Cmd + K 唤起，支持页面跳转与少量快捷操作。
 * 只做前端路由与事件派发，不引入额外依赖。
 */
export default {
  name: 'CommandPalette',
  emits: ['start-tour'],
  data () {
    return {
      visible: false,
      keyword: '',
      activeId: null
    }
  },
  computed: {
    commands () {
      return [
        { id: 'nav-home', group: '页面跳转', label: '主页 · 运行概览', hint: '/dashboard', icon: '◉', path: '/dashboard' },
        { id: 'nav-data', group: '页面跳转', label: '数据管理', hint: '/data/index', icon: '▤', path: '/data/index' },
        { id: 'nav-lineage', group: '页面跳转', label: '数据血缘', hint: '/data/lineage', icon: '⇄', path: '/data/lineage' },
        { id: 'nav-predict', group: '页面跳转', label: '热度预测实验台', hint: '/predict/index', icon: '◎', path: '/predict/index' },
        { id: 'nav-attr', group: '页面跳转', label: '归因解释', hint: '/attribution/index', icon: '✦', path: '/attribution/index' },
        { id: 'nav-eval', group: '页面跳转', label: '实验中心', hint: '/evaluation/index', icon: '⌁', path: '/evaluation/index' },
        { id: 'nav-model', group: '页面跳转', label: '模型治理', hint: '/model/index', icon: '⚙', path: '/model/index' },
        { id: 'nav-report', group: '页面跳转', label: '报告中心', hint: '/report/index', icon: '▦', path: '/report/index' },
        { id: 'nav-screen', group: '页面跳转', label: '数据大屏', hint: '/screen/index', icon: '▣', path: '/screen/index' },
        { id: 'nav-about', group: '页面跳转', label: '项目介绍', hint: '/about/index', icon: 'ℹ', path: '/about/index' },
        { id: 'act-tour', group: '快捷操作', label: '开始演示导览', hint: '六步走完系统', icon: '▶', action: 'tour' },
        { id: 'act-copy', group: '快捷操作', label: '复制当前地址', hint: '分享给评审老师', icon: '⧉', action: 'copy' }
      ]
    },
    filtered () {
      const kw = this.keyword.trim().toLowerCase()
      if (!kw) return this.commands
      return this.commands.filter(c =>
        c.label.toLowerCase().includes(kw) ||
        c.hint.toLowerCase().includes(kw) ||
        c.group.toLowerCase().includes(kw))
    },
    grouped () {
      const map = {}
      this.filtered.forEach(c => {
        if (!map[c.group]) map[c.group] = []
        map[c.group].push(c)
      })
      return Object.keys(map).map(label => ({ label, items: map[label] }))
    },
    activeCommand () {
      if (!this.filtered.length) return null
      return this.filtered.find(c => c.id === this.activeId) || this.filtered[0]
    }
  },
  watch: {
    keyword () {
      this.activeId = this.filtered.length ? this.filtered[0].id : null
    }
  },
  mounted () {
    window.addEventListener('keydown', this.onKeydown)
  },
  beforeUnmount () {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    onKeydown (e) {
      if ((e.metaKey || e.ctrlKey) && String(e.key).toLowerCase() === 'k') {
        e.preventDefault()
        this.toggle()
      }
    },
    toggle () {
      this.visible ? this.close() : this.open()
    },
    open () {
      this.visible = true
      this.keyword = ''
      this.activeId = this.filtered.length ? this.filtered[0].id : null
    },
    close () {
      this.visible = false
    },
    reset () {
      this.keyword = ''
      this.activeId = null
    },
    focusInput () {
      this.$nextTick(() => {
        const el = this.$refs.input && this.$refs.input.$el
        const input = el && el.querySelector('input')
        if (input) input.focus()
      })
    },
    move (step) {
      const list = this.filtered
      if (!list.length) return
      const idx = list.findIndex(c => c.id === this.activeId)
      const next = (idx + step + list.length) % list.length
      this.activeId = list[next].id
    },
    runActive () {
      if (this.activeCommand) this.run(this.activeCommand)
    },
    run (cmd) {
      this.close()
      if (cmd.path) {
        if (this.$route.path !== cmd.path) this.$router.push(cmd.path)
        return
      }
      if (cmd.action === 'tour') {
        this.$emit('start-tour')
        return
      }
      if (cmd.action === 'copy') {
        const url = window.location.href
        if (navigator.clipboard) {
          navigator.clipboard.writeText(url).then(() => this.$message.success('地址已复制'))
            .catch(() => this.$message.warning('复制失败，请手动复制地址栏'))
        } else {
          this.$message.info(url)
        }
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.cmd-box {
  margin: -8px -4px;
}

.cmd-input {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 2px 12px;
  border-bottom: 1px solid #eef0f6;

  .cmd-mark {
    font-size: 14px;
    color: #6366f1;
    font-weight: 700;
  }

  :deep(.el-input__wrapper) {
    box-shadow: none;
    padding-left: 0;
  }

  :deep(.el-input__inner) {
    font-size: 15px;
  }

  .cmd-esc {
    font-size: 10px;
    color: #94a3b8;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 1px 5px;
  }
}

.cmd-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 8px 0;
}

.cmd-group {
  padding: 6px 8px 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .06em;
  color: #b6bec9;
}

.cmd-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 8px;
  cursor: pointer;

  &.active {
    background: #eef2ff;
  }

  .ci-icon {
    width: 18px;
    text-align: center;
    color: #6366f1;
  }

  .ci-label {
    font-size: 13px;
    color: #1e293b;
  }

  .ci-hint {
    margin-left: auto;
    font-size: 11px;
    color: #b6bec9;
  }
}

.cmd-empty {
  padding: 28px 0;
  text-align: center;
  font-size: 12.5px;
  color: #94a3b8;
}

.cmd-foot {
  padding-top: 10px;
  border-top: 1px solid #eef0f6;
  font-size: 11px;
  color: #b6bec9;
  text-align: right;
}
</style>

<style lang="scss">
.cmd-dialog {
  .el-dialog__header {
    display: none;
  }

  .el-dialog__body {
    padding: 16px 18px;
  }
}
</style>
