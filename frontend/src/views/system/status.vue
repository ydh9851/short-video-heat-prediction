<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">系统状态</div>
        <div class="page-desc">推理引擎、实验线程池、预测指标与 JVM 运行状态总览，每 10 秒自动刷新。</div>
      </div>
      <div class="page-head-actions">
        <el-button :loading="loading" @click="load">立即刷新</el-button>
      </div>
    </div>

    <el-row :gutter="16" v-loading="loading">
      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="status-card">
          <template #header>
            <div class="card-head">
              <span>推理引擎</span>
              <span class="status-dot" :class="engineStatusClass"><i />{{ engine.status || '-' }}</span>
            </div>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="服务地址">{{ engine.baseUrl || '未配置' }}</el-descriptions-item>
            <el-descriptions-item label="最近错误">
              <span :class="{ 'error-text': engine.lastError }">{{ engine.lastError || '无' }}</span>
            </el-descriptions-item>
          </el-descriptions>
          <div class="hint">UP = 常驻服务正常；DEGRADED = 熔断中，请求自动降级 CLI；DISABLED = 未配置。</div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="status-card">
          <template #header>
            <div class="card-head">
              <span>实验线程池</span>
              <span class="status-dot" :class="pool.queueSize > 0 ? 'warn' : 'on'"><i />{{ pool.queueSize > 0 ? '有积压' : '空闲' }}</span>
            </div>
          </template>
          <div class="metric-grid">
            <div class="metric"><div class="metric-value">{{ pool.activeCount ?? '-' }}</div><div class="metric-label">运行中任务</div></div>
            <div class="metric"><div class="metric-value">{{ pool.queueSize ?? '-' }} / {{ pool.queueCapacity ?? '-' }}</div><div class="metric-label">队列积压 / 容量</div></div>
            <div class="metric"><div class="metric-value">{{ pool.poolSize ?? '-' }} ({{ pool.corePoolSize ?? '-' }}~{{ pool.maxPoolSize ?? '-' }})</div><div class="metric-label">当前线程数（核心~最大）</div></div>
            <div class="metric"><div class="metric-value">{{ pool.completedTaskCount ?? '-' }}</div><div class="metric-label">累计完成</div></div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="status-card">
          <template #header>
            <div class="card-head"><span>预测请求</span></div>
          </template>
          <div class="metric-grid">
            <div class="metric"><div class="metric-value">{{ predict.total ?? 0 }}</div><div class="metric-label">累计请求</div></div>
            <div class="metric"><div class="metric-value">{{ predict.meanMs ?? '-' }} ms</div><div class="metric-label">平均耗时</div></div>
            <div class="metric"><div class="metric-value">{{ predict.maxMs ?? '-' }} ms</div><div class="metric-label">最大耗时</div></div>
            <div class="metric"><div class="metric-value">{{ cacheHitRate }}%</div><div class="metric-label">缓存命中率</div></div>
          </div>
          <div class="hint" v-if="predict.requests">
            <span v-for="(v, k) in predict.requests" :key="k" class="source-tag">{{ k }}: {{ v }}</span>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="status-card">
          <template #header>
            <div class="card-head">
              <span>JVM 运行时</span>
              <span class="status-dot" :class="jvm.memoryUsagePercent > 85 ? 'off' : (jvm.memoryUsagePercent > 70 ? 'warn' : 'on')">
                <i />内存 {{ jvm.memoryUsagePercent ?? '-' }}%
              </span>
            </div>
          </template>
          <div class="metric-grid">
            <div class="metric"><div class="metric-value">{{ uptimeText }}</div><div class="metric-label">运行时长</div></div>
            <div class="metric"><div class="metric-value">{{ jvm.processors ?? '-' }}</div><div class="metric-label">CPU 核数</div></div>
            <div class="metric"><div class="metric-value">{{ jvm.memoryUsedMB ?? '-' }} / {{ jvm.memoryMaxMB ?? '-' }} MB</div><div class="metric-label">内存使用 / 上限</div></div>
            <div class="metric"><div class="metric-value">{{ shadowText }}</div><div class="metric-label">影子模式</div></div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import systemApi from '@/api/system'

export default {
  name: 'SystemStatusPage',
  data () {
    return {
      loading: false,
      engine: {},
      pool: {},
      predict: {},
      shadow: {},
      jvm: {},
      timer: null
    }
  },
  computed: {
    engineStatusClass () {
      const s = this.engine.status
      if (s === 'UP') return 'on'
      if (s === 'DEGRADED') return 'warn'
      return 'off'
    },
    cacheHitRate () {
      const reqs = this.predict.requests || {}
      const cache = reqs.cache || 0
      const total = this.predict.total || 0
      if (!total) return '-'
      return Math.round(cache * 1000 / total) / 10
    },
    uptimeText () {
      const s = this.jvm.uptimeSeconds
      if (!s && s !== 0) return '-'
      const h = Math.floor(s / 3600)
      const m = Math.floor((s % 3600) / 60)
      if (h > 0) return `${h} 小时 ${m} 分`
      return `${m} 分 ${Math.floor(s % 60)} 秒`
    },
    shadowText () {
      const stats = this.shadow.stats
      if (!stats) return '-'
      return stats.enabled ? `开启（${stats.shadowModel || '-'}）` : '关闭'
    }
  },
  created () {
    this.load()
    this.timer = setInterval(this.load, 10000)
  },
  beforeUnmount () {
    if (this.timer) clearInterval(this.timer)
  },
  methods: {
    load () {
      this.loading = true
      systemApi.status().then(data => {
        const re = data.response || {}
        this.engine = re.engine || {}
        this.pool = re.evaluationPool || {}
        this.predict = re.predict || {}
        this.shadow = re.shadow || {}
        this.jvm = re.jvm || {}
        this.loading = false
      }).catch(() => { this.loading = false })
    }
  }
}
</script>

<style scoped>
.status-card {
  margin-bottom: 16px;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.metric-value {
  font-size: 22px;
  font-weight: 600;
  line-height: 1.3;
}
.metric-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.hint {
  margin-top: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.error-text {
  color: var(--el-color-danger);
}
.source-tag {
  display: inline-block;
  margin-right: 12px;
}
.status-dot.warn i {
  background: var(--el-color-warning);
}
</style>
