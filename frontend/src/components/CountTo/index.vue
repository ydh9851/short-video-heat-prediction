<template>
  <span>{{ displayValue }}</span>
</template>

<script>
// vue-count-to 的轻量本地替代，兼容 :start-val / :end-val / :duration 接口
export default {
  name: 'CountTo',
  props: {
    startVal: {
      type: Number,
      default: 0
    },
    endVal: {
      type: Number,
      default: 0
    },
    duration: {
      type: Number,
      default: 3000
    },
    // 保留小数位，避免出现 0.8182483784403651 这类超长浮点显示
    decimals: {
      type: Number,
      default: 0
    }
  },
  data () {
    return {
      displayValue: this.startVal,
      rafId: null,
      startTime: null
    }
  },
  watch: {
    endVal (newVal) {
      this.animate(newVal)
    }
  },
  mounted () {
    this.animate(this.endVal)
  },
  beforeUnmount () {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId)
    }
  },
  methods: {
    animate (target) {
      if (this.rafId) {
        cancelAnimationFrame(this.rafId)
      }
      const factor = Math.pow(10, this.decimals)
      const round = v => Math.round(v * factor) / factor
      const start = round(this.displayValue)
      const change = target - start
      const duration = this.duration || 1
      const step = timestamp => {
        if (this.startTime === null) {
          this.startTime = timestamp
        }
        const progress = Math.min((timestamp - this.startTime) / duration, 1)
        // easeOutCubic
        const eased = 1 - Math.pow(1 - progress, 3)
        this.displayValue = round(start + change * eased)
        if (progress < 1) {
          this.rafId = requestAnimationFrame(step)
        } else {
          this.displayValue = round(target)
          this.startTime = null
        }
      }
      this.startTime = null
      this.rafId = requestAnimationFrame(step)
    }
  }
}
</script>
