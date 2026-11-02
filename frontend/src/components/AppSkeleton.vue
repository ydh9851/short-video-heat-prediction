<template>
  <!--
    统一骨架屏：替代各页面零散的 v-loading 遮罩。
    优势：骨架形状与真实布局一致，加载完成时几乎无跳变；不遮挡已渲染的内容。
  -->
  <div class="app-skeleton" :class="'sk-' + type">
    <!-- 指标卡 -->
    <template v-if="type === 'kpi'">
      <div v-for="i in rows" :key="i" class="sk-kpi">
        <el-skeleton :animated="animated" :rows="0">
          <template #template>
            <div class="sk-kpi-line">
              <el-skeleton-item variant="text" style="width: 56%" />
            </div>
            <div class="sk-kpi-value">
              <el-skeleton-item variant="h1" style="width: 42%" />
            </div>
          </template>
        </el-skeleton>
      </div>
    </template>

    <!-- 图表 -->
    <template v-else-if="type === 'chart'">
      <div class="sk-chart-bar" :style="{ height: barHeight }">
        <div v-for="i in rows" :key="i" class="sk-bar" :style="{ height: barRatio(i) }" />
      </div>
    </template>

    <!-- 表格 / 文本块 -->
    <template v-else>
      <el-skeleton :animated="animated" :rows="rows" />
    </template>
  </div>
</template>

<script>
export default {
  name: 'AppSkeleton',
  props: {
    /** kpi / chart / table / text */
    type: {
      type: String,
      default: 'text'
    },
    /** 骨架行数（kpi 为卡片数，chart 为柱数） */
    rows: {
      type: Number,
      default: 4
    },
    animated: {
      type: Boolean,
      default: true
    }
  },
  computed: {
    barHeight () {
      return this.rows > 6 ? '120px' : '96px'
    }
  },
  methods: {
    /** 柱高做确定性伪随机，避免每次渲染跳动 */
    barRatio (i) {
      const seed = (i * 37) % 100
      return 30 + (seed % 65)
    }
  }
}
</script>

<style lang="scss" scoped>
.app-skeleton {
  width: 100%;
}

.sk-kpi {
  padding: 14px 16px;
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  background: var(--app-card);
}

.sk-kpi + .sk-kpi {
  margin-top: 10px;
}

.sk-kpi-line :deep(.el-skeleton__item) {
  height: 12px;
  border-radius: 4px;
}

.sk-kpi-value {
  margin-top: 10px;

  :deep(.el-skeleton__item) {
    height: 22px;
    border-radius: 6px;
  }
}

.sk-chart-bar {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 8px 4px 0;
}

.sk-bar {
  flex: 1;
  border-radius: 6px 6px 0 0;
  background: linear-gradient(180deg, #eef0fe 0%, #e2e6f8 100%);
}
</style>
