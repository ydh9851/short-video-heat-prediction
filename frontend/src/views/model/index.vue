<template>
  <div class="app-container model-page">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">模型治理</div>
        <div class="page-desc">
          参考 MLflow Model Registry 的「版本 + 阶段 + 灰度」模型：模型重训即产生新版本，
          上线前用影子模式与线上模型并行打分对比差异，确认无退化后再切换版本，出问题可一键回滚。
        </div>
      </div>
      <div class="page-head-actions">
        <el-button size="small" type="primary" :loading="syncing" @click="sync">同步注册表</el-button>
      </div>
    </div>

    <!-- ============ 引擎与影子状态 ============ -->
    <div class="gov-grid">
      <el-card shadow="never" class="gov-card">
        <div class="section-title">常驻推理服务</div>
        <div class="engine-row">
          <el-tag :type="engineTag" effect="dark" size="medium">{{ engineStatusText }}</el-tag>
          <span class="muted">{{ engine.url || '未配置' }}</span>
        </div>
        <ul class="gov-notes">
          <li>服务启动即预热模型，单次预测约 <b>11ms</b>；CLI 通道约 <b>890ms</b>。</li>
          <li>HTTP 优先，失败进入 <b>30 秒熔断</b>并自动降级回 CLI，两条通道结果完全一致。</li>
          <li v-if="engine.lastError" class="err">最近错误：{{ engine.lastError }}</li>
        </ul>
      </el-card>

      <el-card shadow="never" class="gov-card">
        <div class="section-title">影子模式（候选模型并行打分）</div>
        <div class="shadow-stats">
          <div class="stat">
            <div class="stat-label">对比次数</div>
            <div class="stat-value">{{ shadow.count || 0 }}</div>
          </div>
          <div class="stat">
            <div class="stat-label">平均偏差</div>
            <div class="stat-value tone-warn">{{ pct(shadow.meanAbsDiffPct) }}</div>
          </div>
          <div class="stat">
            <div class="stat-label">P50 偏差</div>
            <div class="stat-value">{{ pct(shadow.p50AbsDiffPct) }}</div>
          </div>
          <div class="stat">
            <div class="stat-label">P90 偏差</div>
            <div class="stat-value">{{ pct(shadow.p90AbsDiffPct) }}</div>
          </div>
        </div>
        <ul class="gov-notes">
          <li>
            线上模型 <b>{{ shadow.primaryModel || 'lgbm' }}</b> 照常返回，
            候选模型 <b>{{ shadow.shadowModel || '未启用' }}</b> 在独立线程打分，只记录差异、不影响响应。
          </li>
          <li>偏差越大说明「换模型」越不是无痛操作，必须先过影子验证再上线。</li>
        </ul>
      </el-card>
    </div>

    <!-- ============ 版本与阶段 ============ -->
    <el-card shadow="never" class="gov-card">
      <div class="list-toolbar">
        <div class="section-title">版本注册表</div>
        <span class="muted">更新于 {{ registry.updatedAt || '-' }}</span>
      </div>
      <el-table :data="models" size="small" v-loading="loading">
        <el-table-column prop="model" label="模型" width="80" />
        <el-table-column label="阶段" width="110">
          <template #default="{ row }">
            <el-tag size="small" effect="light" :type="row.stage === 'production' ? 'success' : 'warning'">
              {{ row.stage }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="activeVersion" label="线上版本" min-width="180" />
        <el-table-column label="R²(log)" width="100">
          <template #default="{ row }">{{ row.r2 == null ? '-' : row.r2.toFixed(4) }}</template>
        </el-table-column>
        <el-table-column label="MAE(log)" width="100">
          <template #default="{ row }">{{ row.mae == null ? '-' : row.mae.toFixed(4) }}</template>
        </el-table-column>
        <el-table-column label="体积" width="90">
          <template #default="{ row }">{{ row.sizeMB == null ? '-' : row.sizeMB + ' MB' }}</template>
        </el-table-column>
        <el-table-column prop="trainedAt" label="训练时间" width="160" />
        <el-table-column label="数据版本" width="180">
          <template #default="{ row }">
            <el-tooltip
              v-if="row.dataVersion"
              content="该模型训练时所用的数据集版本；指标变化时可据此区分是模型改动还是数据替换"
              placement="top"
            >
              <span class="data-version">{{ row.dataVersion }}</span>
            </el-tooltip>
            <span v-else class="muted">未记录</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="210">
          <template #default="{ row }">
            <el-select
              v-if="(row.versions || []).length > 1"
              v-model="promoteTarget[row.model]"
              size="mini"
              placeholder="切换版本"
              class="version-select"
            >
              <el-option
                v-for="v in row.versions"
                :key="v.version"
                :label="v.version + (v.version === row.activeVersion ? '（当前）' : '')"
                :value="v.version"
              />
            </el-select>
            <el-button
              link
              type="primary"
              size="small"
              :disabled="(row.versions || []).length < 2 || !promoteTarget[row.model]"
              @click="promote(row)"
            >切换</el-button>
            <el-button
              link
              type="warning"
              size="small"
              :disabled="(row.versions || []).length < 2"
              @click="rollback(row)"
            >回滚</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <app-empty compact title="注册表为空" description="点击「同步注册表」扫描 model_cache" />
        </template>
      </el-table>
    </el-card>

    <!-- ============ 影子打分明细 ============ -->
    <el-card shadow="never" class="gov-card">
      <div class="list-toolbar">
        <div class="section-title">最近影子打分记录</div>
        <span class="muted">共 {{ shadow.count || 0 }} 条，展示最近 {{ (shadow.recent || []).length }} 条</span>
      </div>
      <el-table :data="shadow.recent || []" size="small">
        <el-table-column prop="ts" label="时间" width="165" />
        <el-table-column label="线上 / 候选" width="150">
          <template #default="{ row }">{{ row.primaryModel }} → {{ row.shadowModel }}</template>
        </el-table-column>
        <el-table-column label="线上预测" width="120">
          <template #default="{ row }">{{ fmtNum(row.primary) }}</template>
        </el-table-column>
        <el-table-column label="候选预测" width="120">
          <template #default="{ row }">{{ fmtNum(row.shadow) }}</template>
        </el-table-column>
        <el-table-column label="偏差" width="100">
          <template #default="{ row }">
            <span :class="Math.abs(row.diffPct) > 20 ? 'tone-bad' : 'tone-ok'">
              {{ (row.diffPct > 0 ? '+' : '') + row.diffPct.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="traceId" label="traceId" min-width="150" show-overflow-tooltip />
        <template #empty>
          <app-empty compact title="还没有影子打分记录" description="先在「热度预测」页跑几次预测" />
        </template>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import modelApi from '@/api/model'
import AppEmpty from '@/components/AppEmpty'
import predictApi from '@/api/predict'

export default {
  name: 'ModelGovernance',
  components: { AppEmpty },
  data () {
    return {
      models: [],
      registry: {},
      shadow: {},
      engine: {},
      loading: false,
      syncing: false,
      promoteTarget: {}
    }
  },
  computed: {
    engineStatusText () {
      const s = this.engine.status || 'DISABLED'
      if (s === 'UP') return '服务正常'
      if (s === 'DEGRADED') return '已降级（熔断中）'
      return '未启用（走 CLI）'
    },
    engineTag () {
      const s = this.engine.status || 'DISABLED'
      if (s === 'UP') return 'success'
      if (s === 'DEGRADED') return 'warning'
      return 'info'
    }
  },
  created () {
    this.loadAll()
  },
  methods: {
    loadAll () {
      this.loading = true
      modelApi.list().then(re => {
        const d = re.response || {}
        this.registry = d
        this.models = d.models || []
        this.loading = false
      }).catch(() => { this.loading = false })
      modelApi.shadow(10).then(re => { this.shadow = re.response || {} }).catch(() => {})
      predictApi.engine().then(re => { this.engine = re.response || {} }).catch(() => {})
    },
    sync () {
      this.syncing = true
      modelApi.sync().then(() => {
        this.syncing = false
        this.$message.success('注册表已同步')
        this.loadAll()
      }).catch(() => {
        this.syncing = false
        this.$message.error('同步失败，请查看后端日志')
      })
    },
    promote (row) {
      const version = this.promoteTarget[row.model]
      if (!version) return
      modelApi.promote(row.model, version).then(() => {
        this.$message.success(row.model + ' 已切换到版本 ' + version)
        this.loadAll()
      }).catch(() => this.$message.error('切换失败：该版本不存在'))
    },
    rollback (row) {
      modelApi.rollback(row.model).then(() => {
        this.$message.success(row.model + ' 已回滚到上一版本')
        this.loadAll()
      }).catch(() => this.$message.error('回滚失败：' + row.model + ' 只有一个版本'))
    },
    pct (v) {
      return v == null ? '-' : v.toFixed(2) + '%'
    },
    fmtNum (v) {
      return v == null ? '-' : Math.round(v).toLocaleString()
    }
  }
}
</script>

<style lang="scss" scoped>
.model-page {
  .page-head {
    margin-bottom: 16px;
  }
}

.gov-grid {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.gov-card {
  flex: 1;
  min-width: 0;
  margin-bottom: 16px;

  .section-title {
    margin-bottom: 12px;
  }
}

.gov-card:last-child {
  margin-bottom: 0;
}

.engine-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.shadow-stats {
  display: flex;
  gap: 18px;
  margin-bottom: 10px;
}

.stat {
  .stat-label {
    font-size: 11.5px;
    color: #94a3b8;
    margin-bottom: 2px;
  }

  .stat-value {
    font-size: 19px;
    font-weight: 700;
    color: #1e293b;
  }
}

.gov-notes {
  margin: 0;
  padding-left: 18px;

  li {
    font-size: 12.5px;
    line-height: 1.85;
    color: #64748b;
  }

  .err {
    color: #dc2626;
    word-break: break-all;
  }
}

.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;

  .section-title {
    margin-bottom: 0;
  }
}

.version-select {
  width: 150px;
  margin-right: 6px;
}

.tone-warn {
  color: #d97706;
}

.tone-ok {
  color: #16a34a;
}

.tone-bad {
  color: #dc2626;
  font-weight: 700;
}

.muted {
  font-size: 12px;
  color: #94a3b8;
}

/* 数据版本标记：等宽字体，便于与版本号对照 */
.data-version {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 11.5px;
  color: #4f46e5;
  background: #f4f3ff;
  border: 1px solid #e4e1fb;
  border-radius: 4px;
  padding: 1px 6px;
}
</style>
