<template>
  <div class="job-progress" :class="'st-' + stateKey">
    <div class="jp-head">
      <span class="jp-label">{{ label }}</span>
      <span class="jp-meta">
        {{ clamped }}%
        <em v-if="elapsed"> · 已 {{ elapsed }} 秒</em>
      </span>
    </div>
    <div class="jp-track">
      <div class="jp-bar" :style="{ width: clamped + '%' }" />
    </div>
  </div>
</template>

<script>
/**
 * 任务进度条：用于分钟级实验的等待反馈。
 * 没有真实进度时由调用方按耗时估算 percent，这里只负责视觉状态。
 */
export default {
  name: 'JobProgress',
  props: {
    percent: { type: Number, default: 0 },
    status: { type: String, default: 'RUNNING' },
    label: { type: String, default: '任务运行中' },
    elapsed: { type: [Number, String], default: null }
  },
  computed: {
    clamped () {
      const n = Number(this.percent)
      if (!Number.isFinite(n)) return 0
      return Math.max(0, Math.min(100, Math.round(n)))
    },
    stateKey () {
      return String(this.status || 'RUNNING').toLowerCase()
    }
  }
}
</script>

<style lang="scss" scoped>
.job-progress {
  padding: 10px 14px;
  border: 1px solid #eef0f6;
  border-radius: 10px;
  background: #fafbfe;
}

.jp-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.jp-label {
  font-size: 12.5px;
  font-weight: 650;
  color: #1e293b;
}

.jp-meta {
  font-size: 11.5px;
  color: #94a3b8;

  em {
    font-style: normal;
  }
}

.jp-track {
  height: 6px;
  border-radius: 999px;
  background: #eef2f7;
  overflow: hidden;
}

.jp-bar {
  height: 100%;
  border-radius: 999px;
  transition: width .4s ease;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  background-size: 200% 100%;
  animation: jp-flow 1.4s linear infinite;
}

.st-done .jp-bar {
  animation: none;
  background: linear-gradient(90deg, #10b981, #34d399);
}

.st-failed .jp-bar {
  animation: none;
  background: linear-gradient(90deg, #ef4444, #f87171);
}

.st-queued .jp-bar {
  animation: none;
  background: #cbd5e1;
}

@keyframes jp-flow {
  0% { background-position: 0 0; }
  100% { background-position: 200% 0; }
}
</style>
