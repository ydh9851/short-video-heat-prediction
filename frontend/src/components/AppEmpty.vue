<template>
  <!--
    统一空态：统一「没有数据」时的表达方式。
    强调「为什么空 + 下一步做什么」，避免只显示一句干巴巴的「暂无数据」。
  -->
  <div class="app-empty" :class="{ compact: compact }">
    <div class="empty-icon">
      <svg-icon v-if="icon" :icon-class="icon" />
      <span v-else class="empty-glyph">▤</span>
    </div>
    <div class="empty-title">{{ title }}</div>
    <div v-if="description" class="empty-desc">{{ description }}</div>
    <div v-if="$slots.default" class="empty-action">
      <slot />
    </div>
  </div>
</template>

<script>
export default {
  name: 'AppEmpty',
  props: {
    title: {
      type: String,
      default: '暂无数据'
    },
    description: {
      type: String,
      default: ''
    },
    // 可选：src/icons/svg 下的图标名
    icon: {
      type: String,
      default: ''
    },
    compact: {
      type: Boolean,
      default: false
    }
  }
}
</script>

<style lang="scss" scoped>
.app-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 32px 16px;
  color: var(--app-text-3);
}

.app-empty.compact {
  padding: 16px 12px;
}

.empty-icon {
  color: #cbd5e1;
  font-size: 40px;
  line-height: 1;
  margin-bottom: 12px;
}

.empty-glyph {
  font-size: 40px;
  opacity: .7;
}

.empty-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--app-text-2);
}

.empty-desc {
  margin-top: 6px;
  font-size: 12.5px;
  line-height: 1.8;
  color: var(--app-text-3);
  max-width: 520px;
}

.empty-action {
  margin-top: 14px;
}
</style>