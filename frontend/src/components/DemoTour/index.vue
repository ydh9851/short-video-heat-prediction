<template>
  <teleport to="body">
    <div v-if="visible && rect" class="tour-layer">
      <div class="tour-ring" :style="ringStyle" />
      <div class="tour-card" :style="cardStyle">
        <div class="tc-head">
          <span class="tc-step">{{ index + 1 }} / {{ steps.length }}</span>
          <span class="tc-title">{{ step.title }}</span>
        </div>
        <p class="tc-text">{{ step.text }}</p>
        <div class="tc-actions">
          <el-button size="small" text @click="close">跳过</el-button>
          <span class="tc-spacer" />
          <el-button size="small" :disabled="index === 0" @click="prev">上一步</el-button>
          <el-button size="small" type="primary" @click="next">
            {{ index === steps.length - 1 ? '完成' : '下一步' }}
          </el-button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script>
const STEPS = [
  {
    route: '/dashboard',
    target: '.page-head',
    title: '运行概览',
    text: '这里是系统的总入口：关键指标、预测趋势与任务状态都集中在这一页，先建立整体印象。'
  },
  {
    route: '/data/index',
    target: '.quality-strip',
    title: '数据管理',
    text: '导入数据集后，顶部质量门禁会给出硬性 / 软性检查结果；只有通过门禁的数据才建议进入建模。'
  },
  {
    route: '/predict/index',
    target: '.predict-form',
    title: '热度预测实验台',
    text: '输入发布时就能拿到的先验信息，得到点预测、两种区间与决策卡；右侧还能做 what-if 与场景沉淀。'
  },
  {
    route: '/attribution/index',
    target: '.explain-row',
    title: '归因解释',
    text: '解释报告按「结论 → 证据 → 建议 → 局限」组织，SHAP 贡献与反事实建议都能直接引用到论文里。'
  },
  {
    route: '/evaluation/index',
    target: '.page-head',
    title: '实验中心',
    text: '所有指标都来自可复现实验：一键运行、任务队列、结果登记，保证论文里的数字能追溯。'
  },
  {
    route: '/model/index',
    target: '.page-head',
    title: '模型治理',
    text: '模型注册、版本与影子对比集中在这里，线上模型与候选模型的效果差异一目了然。'
  }
]

/**
 * 轻量演示导览：不依赖 Element Plus 版本，按选择器定位高亮目标。
 * 每一步自动切换路由，等待渲染后再测量元素，找不到时回退到页面标题。
 */
export default {
  name: 'DemoTour',
  props: {
    visible: { type: Boolean, default: false }
  },
  emits: ['close'],
  data () {
    return {
      steps: STEPS,
      index: 0,
      rect: null,
      card: { top: 0, left: 0 },
      timer: null
    }
  },
  computed: {
    step () {
      return this.steps[this.index] || this.steps[0]
    },
    ringStyle () {
      if (!this.rect) return {}
      return {
        top: this.rect.top + 'px',
        left: this.rect.left + 'px',
        width: this.rect.width + 'px',
        height: this.rect.height + 'px'
      }
    },
    cardStyle () {
      return {
        top: this.card.top + 'px',
        left: this.card.left + 'px'
      }
    }
  },
  watch: {
    visible (v) {
      v ? this.start() : this.cleanup()
    }
  },
  mounted () {
    window.addEventListener('resize', this.measure)
    window.addEventListener('keydown', this.onKeydown)
  },
  beforeUnmount () {
    window.removeEventListener('resize', this.measure)
    window.removeEventListener('keydown', this.onKeydown)
    this.cleanup()
  },
  methods: {
    start () {
      this.index = 0
      this.goto()
    },
    goto () {
      this.rect = null
      const step = this.step
      const sameRoute = this.$route.path === step.route
      const run = () => {
        this.timer = setTimeout(this.measure, sameRoute ? 180 : 420)
      }
      if (sameRoute) {
        run()
      } else {
        this.$router.push(step.route).then(run).catch(run)
      }
    },
    measure () {
      const el = document.querySelector(this.step.target) ||
        document.querySelector('.page-head') ||
        document.querySelector('.app-main')
      if (!el) return
      el.scrollIntoView({ block: 'center', behavior: 'smooth' })
      this.timer = setTimeout(() => {
        const r = el.getBoundingClientRect()
        this.rect = {
          top: Math.max(6, r.top - 6),
          left: Math.max(6, r.left - 6),
          width: Math.min(window.innerWidth - 12, r.width + 12),
          height: Math.min(window.innerHeight - 12, r.height + 12)
        }
        const cardW = 350
        const cardH = 200
        let top = r.bottom + 16
        if (top + cardH > window.innerHeight) top = Math.max(16, r.top - cardH - 16)
        const left = Math.min(Math.max(16, r.left), window.innerWidth - cardW - 16)
        this.card = { top, left }
      }, 220)
    },
    next () {
      if (this.index >= this.steps.length - 1) {
        this.close()
        return
      }
      this.index += 1
      this.goto()
    },
    prev () {
      if (this.index === 0) return
      this.index -= 1
      this.goto()
    },
    close () {
      try { localStorage.setItem('demoTourDone', '1') } catch (e) { /* 忽略存储失败 */ }
      this.$emit('close')
    },
    onKeydown (e) {
      if (!this.visible) return
      if (e.key === 'Escape') this.close()
      else if (e.key === 'ArrowRight') this.next()
      else if (e.key === 'ArrowLeft') this.prev()
    },
    cleanup () {
      if (this.timer) {
        clearTimeout(this.timer)
        this.timer = null
      }
      this.rect = null
    }
  }
}
</script>

<style lang="scss" scoped>
.tour-layer {
  position: fixed;
  inset: 0;
  z-index: 3000;
  pointer-events: none;
}

.tour-ring {
  position: fixed;
  border: 2px solid #6366f1;
  border-radius: 10px;
  box-shadow: 0 0 0 9999px rgba(15, 23, 42, .55);
  transition: all .28s ease;
}

.tour-card {
  position: fixed;
  width: 350px;
  padding: 16px 18px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 18px 48px rgba(15, 23, 42, .28);
  pointer-events: auto;
  transition: all .28s ease;
}

.tc-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.tc-step {
  font-size: 11px;
  font-weight: 700;
  color: #6366f1;
  background: #eef2ff;
  border-radius: 999px;
  padding: 1px 8px;
}

.tc-title {
  font-size: 15px;
  font-weight: 750;
  color: #1e293b;
}

.tc-text {
  margin: 10px 0 14px;
  font-size: 12.5px;
  line-height: 1.85;
  color: #64748b;
}

.tc-actions {
  display: flex;
  align-items: center;
  gap: 8px;

  .tc-spacer {
    flex: 1;
  }
}
</style>
