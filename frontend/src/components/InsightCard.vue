<template>
  <div class="insight-card" :class="'tone-' + tone">
    <div class="ic-head">
      <span class="ic-dot" />
      <span class="ic-title">{{ title }}</span>
      <el-tag v-if="tag" size="small" effect="plain" class="ic-tag">{{ tag }}</el-tag>
      <div class="ic-extra"><slot name="extra" /></div>
    </div>
    <div v-if="desc" class="ic-desc">{{ desc }}</div>
    <div v-if="$slots.default" class="ic-body"><slot /></div>
  </div>
</template>

<script>
/**
 * 结论卡：在图表旁给出一句可引用的结论，避免读者只看到数字。
 * 语气色只影响左侧强调条与标签，不改变正文可读性。
 */
export default {
  name: 'InsightCard',
  props: {
    title: { type: String, required: true },
    desc: { type: String, default: '' },
    tone: { type: String, default: 'primary' },
    tag: { type: String, default: '' }
  }
}
</script>

<style lang="scss" scoped>
.insight-card {
  padding: 12px 14px;
  border: 1px solid #eef0f6;
  border-left: 3px solid #6366f1;
  border-radius: 10px;
  background: #fafbfe;

  &.tone-success { border-left-color: #10b981; background: #f6fdfa; }
  &.tone-warning { border-left-color: #f59e0b; background: #fffdf5; }
  &.tone-danger { border-left-color: #ef4444; background: #fff8f8; }
  &.tone-neutral { border-left-color: #94a3b8; background: #f8fafc; }
}

.ic-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ic-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  color: #6366f1;
  flex-shrink: 0;

  .tone-success & { color: #10b981; }
  .tone-warning & { color: #f59e0b; }
  .tone-danger & { color: #ef4444; }
  .tone-neutral & { color: #94a3b8; }
}

.ic-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.ic-tag {
  font-weight: 500;
}

.ic-extra {
  margin-left: auto;
}

.ic-desc {
  margin-top: 6px;
  font-size: 12.5px;
  line-height: 1.8;
  color: #64748b;
}

.ic-body {
  margin-top: 8px;
}
</style>
