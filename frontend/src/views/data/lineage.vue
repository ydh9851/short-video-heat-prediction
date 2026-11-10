<template>
  <div class="app-container">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">数据血缘</div>
        <div class="page-desc">
          把「原始文件 → 规范化数据集 → 数据集版本 → 模型版本」串成一条可读链路：
          数据版本来自 <code>dataset_versions.json</code> 的 SHA-256 指纹登记，
          模型侧读取注册表中线上版本记录的 <code>dataVersion</code>，据此判断模型是否仍使用当前数据集。
        </div>
      </div>
      <div class="page-head-actions">
        <el-select v-model="platform" style="width:180px" @change="load">
          <el-option
            v-for="p in platforms"
            :key="p.platform"
            :label="p.displayName + (p.available ? '' : '（未导入）')"
            :value="p.platform" />
        </el-select>
        <el-button :loading="loading" @click="load">刷新</el-button>
        <el-button plain @click="$router.push('/data/index')">返回数据管理</el-button>
      </div>
    </div>

    <!-- ============ 汇总条 ============ -->
    <div class="summary-strip" v-loading="loading">
      <div v-for="s in summaryItems" :key="s.label" class="summary-item">
        <div class="summary-label">{{ s.label }}</div>
        <div class="summary-value" :class="s.tone">{{ s.value }}</div>
      </div>
    </div>

    <!-- ============ 血缘链路 ============ -->
    <el-card shadow="never" class="lineage-card" v-loading="loading">
      <div class="list-toolbar">
        <div class="section-title">血缘链路</div>
        <el-tag
          size="small"
          :type="summary.chainComplete ? 'success' : 'warning'"
          effect="dark">
          {{ summary.chainComplete ? '链路完整' : '链路待补全' }}
        </el-tag>
      </div>
      <div class="lineage-flow">
        <div v-for="(node, i) in nodes" :key="node.key" class="flow-item">
          <div class="flow-node" :class="node.ok ? 'ok' : 'warn'">
            <div class="node-head">
              <span class="node-step">{{ i + 1 }}</span>
              <span class="node-title">{{ node.title }}</span>
              <span class="status-dot" :class="node.ok ? 'ok' : 'warn'" />
            </div>
            <div v-for="row in node.rows" :key="row.label" class="node-row">
              <span class="row-label">{{ row.label }}</span>
              <span class="row-value" :title="row.value">{{ row.value || '—' }}</span>
            </div>
          </div>
          <div v-if="i < nodes.length - 1" class="flow-arrow">→</div>
        </div>
      </div>
      <div class="muted lineage-hint">
        <template v-if="lineage.updatedAt">数据集注册表更新于 {{ lineage.updatedAt }}。</template>
        版本指纹用于判断数据是否被替换：指纹不变则复用同一版本，模型指标变化可归因于模型改动而非数据。
      </div>
    </el-card>

    <el-row :gutter="16">
      <!-- ============ 版本时间线 ============ -->
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="list-card timeline-card">
          <div class="list-toolbar">
            <div class="section-title">数据集版本时间线</div>
            <el-tag size="small" type="info">{{ versionList.length }} 个版本</el-tag>
          </div>
          <div v-if="versionList.length" class="timeline-wrap">
            <el-timeline>
              <el-timeline-item
                v-for="v in versionTimeline"
                :key="v.version"
                :timestamp="v.registeredAt"
                placement="top"
                :type="v.current ? 'success' : 'primary'">
                <div class="version-card">
                  <div class="version-head">
                    <b>{{ v.version }}</b>
                    <el-tag v-if="v.current" size="small" type="success" effect="dark">当前</el-tag>
                    <el-tag v-if="!v.matchesProcessed" size="small" type="warning" effect="plain">与当前数据集文件不一致</el-tag>
                  </div>
                  <div class="version-meta">
                    指纹 <code>{{ v.fingerprint || '—' }}</code> · {{ fmtInt(v.rows) }} 行 · {{ v.file || '—' }}
                  </div>
                  <div
                    v-if="v.heatMedian != null || v.heatP90 != null || v.categoryCount != null"
                    class="version-meta">
                    <template v-if="v.heatMedian != null">热度中位数 {{ fmtInt(v.heatMedian) }}</template>
                    <template v-if="v.heatP90 != null"> · P90 {{ fmtInt(v.heatP90) }}</template>
                    <template v-if="v.categoryCount != null"> · {{ v.categoryCount }} 类别</template>
                  </div>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>
          <app-empty
            v-else
            title="暂无数据集版本"
            description="导入并登记数据集后，版本记录会出现在这里" />
        </el-card>
      </el-col>

      <!-- ============ 模型版本对照 ============ -->
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="list-card">
          <div class="list-toolbar">
            <div class="section-title">模型版本对照</div>
            <span class="muted">
              {{ summary.linkedModelCount || 0 }} / {{ summary.modelCount || 0 }} 个模型的线上版本使用当前数据集版本
            </span>
          </div>
          <el-table :data="modelList" size="small" v-loading="loading">
            <el-table-column prop="model" label="模型" width="80" />
            <el-table-column prop="activeVersion" label="线上版本" min-width="185" show-overflow-tooltip />
            <el-table-column prop="featureVersion" label="特征版本" width="88" />
            <el-table-column prop="dataVersion" label="数据版本" min-width="165" show-overflow-tooltip />
            <el-table-column label="数据版本匹配" width="110">
              <template #default="{ row }">
                <el-tag size="small" :type="row.dataLinked ? 'success' : 'warning'" effect="light">
                  {{ row.dataLinked ? '匹配' : '不一致' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="可加载" width="88">
              <template #default="{ row }">
                <el-tag size="small" :type="row.loadable ? 'success' : 'info'" effect="plain">
                  {{ row.loadable ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="R²" width="88">
              <template #default="{ row }">{{ row.r2 == null ? '—' : row.r2.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="MAE" width="88">
              <template #default="{ row }">{{ row.mae == null ? '—' : row.mae.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column prop="trainedAt" label="训练时间" width="165" />
            <template #empty>
              <app-empty
                compact
                title="暂无模型版本"
                description="模型注册表为空或尚未同步" />
            </template>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import dataApi from '@/api/data'
import AppEmpty from '@/components/AppEmpty'

export default {
  name: 'DataLineage',
  components: { AppEmpty },
  data () {
    return {
      loading: false,
      platforms: [],
      platform: '',
      lineage: {}
    }
  },
  computed: {
    summary () {
      return this.lineage.summary || {}
    },
    versionList () {
      return this.lineage.versions || []
    },
    // 时间线倒序：最近登记的版本在最上方
    versionTimeline () {
      return this.versionList.slice().reverse()
    },
    modelList () {
      return this.lineage.models || []
    },
    summaryItems () {
      return [
        { label: '数据集版本', value: this.summary.versionCount || 0, tone: '' },
        { label: '模型数量', value: this.summary.modelCount || 0, tone: '' },
        {
          label: '已关联模型',
          value: this.summary.linkedModelCount || 0,
          tone: this.summary.linkedModelCount ? 'ok' : 'warn'
        },
        {
          label: '链路状态',
          value: this.summary.chainComplete ? '完整' : '待补全',
          tone: this.summary.chainComplete ? 'ok' : 'warn'
        }
      ]
    },
    nodes () {
      const raw = this.lineage.raw || {}
      const proc = this.lineage.processed || {}
      const current = this.versionList.find(v => v.current) || {}
      return [
        {
          key: 'raw',
          title: '原始文件',
          ok: !!raw.exists,
          rows: [
            { label: '文件', value: raw.path || '—' },
            { label: '体积', value: raw.sizeMB == null ? '—' : raw.sizeMB + ' MB' },
            { label: '更新时间', value: raw.modifiedAt || '—' }
          ]
        },
        {
          key: 'processed',
          title: '规范化数据集',
          ok: !!proc.exists,
          rows: [
            { label: '文件', value: proc.path || '—' },
            { label: '样本量', value: proc.rows ? this.fmtInt(proc.rows) + ' 行' : '—' },
            { label: '类别 / 跨度', value: (proc.categoryCount || 0) + ' 类 · ' + (proc.timeStart || '—') + ' ~ ' + (proc.timeEnd || '—') }
          ]
        },
        {
          key: 'version',
          title: '数据集版本',
          ok: this.versionList.length > 0,
          rows: [
            { label: '当前版本', value: this.lineage.currentVersion || '—' },
            { label: '版本数', value: this.versionList.length + ' 个' },
            { label: '指纹', value: current.fingerprint || '—' }
          ]
        },
        {
          key: 'model',
          title: '模型版本',
          ok: (this.summary.linkedModelCount || 0) > 0,
          rows: [
            { label: '线上模型', value: (this.summary.modelCount || 0) + ' 个' },
            { label: '数据版本匹配', value: (this.summary.linkedModelCount || 0) + ' 个' },
            { label: '链路', value: this.summary.chainComplete ? '完整可追溯' : '待补全' }
          ]
        }
      ]
    }
  },
  created () {
    this.bootstrap()
  },
  methods: {
    fmtInt (v) {
      const n = Number(v)
      return isFinite(n) ? n.toLocaleString('en-US') : (v || '—')
    },
    bootstrap () {
      dataApi.platforms().then(re => {
        const d = re.response || {}
        this.platforms = d.platforms || []
        this.platform = d.defaultPlatform || (this.platforms[0] && this.platforms[0].platform) || 'douyin'
        this.load()
      }).catch(() => {
        this.platforms = []
        this.platform = 'douyin'
        this.load()
      })
    },
    load () {
      if (!this.platform) return
      this.loading = true
      dataApi.lineage(this.platform).then(re => {
        this.lineage = re.response || {}
      }).catch(() => {
        this.lineage = {}
      }).finally(() => {
        this.loading = false
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;

  .summary-item {
    padding: 12px 16px;
    background: #fff;
    border: 1px solid #e8ecf4;
    border-radius: 10px;
  }

  .summary-label {
    font-size: 12px;
    color: #8a93a6;
    margin-bottom: 6px;
  }

  .summary-value {
    font-size: 22px;
    font-weight: 700;
    color: #1f2a44;

    &.ok { color: #16a34a; }
    &.warn { color: #d97706; }
  }
}

.lineage-card {
  margin-bottom: 16px;
}

.lineage-flow {
  display: flex;
  align-items: stretch;
  gap: 8px;
  padding: 6px 0 10px;
  overflow-x: auto;
}

.flow-item {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 220px;
}

.flow-node {
  flex: 1;
  min-height: 128px;
  padding: 12px 14px;
  background: #fafbff;
  border: 1px solid #e8ecf4;
  border-radius: 10px;
  transition: box-shadow 0.2s ease;

  &:hover {
    box-shadow: 0 6px 18px rgba(99, 102, 241, 0.12);
  }

  &.ok { border-color: rgba(52, 211, 153, 0.55); }
  &.warn { border-color: rgba(251, 191, 36, 0.65); background: #fffdf5; }
}

.node-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.node-step {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #6366f1;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
}

.node-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: #1f2a44;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;

  &.ok { background: #22c55e; }
  &.warn { background: #f59e0b; }
}

.node-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
  line-height: 1.9;
}

.row-label {
  flex: 0 0 62px;
  color: #8a93a6;
}

.row-value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #334155;
}

.flow-arrow {
  flex: 0 0 22px;
  text-align: center;
  color: #a5b4fc;
  font-size: 18px;
}

.lineage-hint {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.7;
}

.timeline-card {
  min-height: 320px;
}

.timeline-wrap {
  max-height: 520px;
  overflow-y: auto;
  padding-top: 6px;
}

.version-card {
  padding: 10px 12px;
  background: #fafbff;
  border: 1px solid #eef1f8;
  border-radius: 8px;
}

.version-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
  color: #1f2a44;
}

.version-meta {
  font-size: 12px;
  color: #64748b;
  line-height: 1.8;

  code {
    padding: 1px 4px;
    background: #eef2ff;
    border-radius: 4px;
    color: #4338ca;
  }
}

@media (max-width: 992px) {
  .summary-strip {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
