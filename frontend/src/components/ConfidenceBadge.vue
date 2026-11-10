<template>
  <span class="confidence-badge" :class="state">
    <span v-if="label" class="cb-label">{{ label }}</span>
    <template v-if="hasValue">
      <b>{{ displayValue }}</b>
      <span v-if="target != null" class="cb-target">/ {{ targetText }}</span>
    </template>
    <span v-else class="cb-muted">待评估</span>
  </span>
</template>

<script>
/**
 * 覆盖率徽标：把「实测 vs 名义」放在一个可比较的小组件里。
 * 达标（实测 >= 名义）为绿色，欠覆盖为琥珀色，缺失时显示「待评估」。
 */
export default {
  name: 'ConfidenceBadge',
  props: {
    value: { type: Number, default: null },
    target: { type: Number, default: 90 },
    label: { type: String, default: '' },
    suffix: { type: String, default: '%' },
    decimals: { type: Number, default: 1 }
  },
  computed: {
    hasValue () {
      return this.value != null && Number.isFinite(Number(this.value))
    },
    numeric () {
      return this.hasValue ? Number(this.value) : null
    },
    state () {
      if (!this.hasValue) return 'is-empty'
      return this.numeric >= this.target ? 'is-good' : 'is-warn'
    },
    displayValue () {
      return this.numeric.toFixed(this.decimals) + this.suffix
    },
    targetText () {
      return Number(this.target).toFixed(this.decimals) + this.suffix
    }
  }
}
</script>

<style lang="scss" scoped>
.confidence-badge {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  line-height: 1.6;
  background: #f1f5f9;
  color: #64748b;

  b {
    font-size: 12.5px;
    font-variant-numeric: tabular-nums;
  }

  .cb-target {
    color: #94a3b8;
    font-size: 11px;
  }

  &.is-good {
    background: #ecfdf5;
    color: #047857;

    b { color: #059669; }
  }

  &.is-warn {
    background: #fffbeb;
    color: #b45309;

    b { color: #d97706; }
  }

  &.is-empty {
    background: #f8fafc;
    color: #94a3b8;
  }
}
</style>
