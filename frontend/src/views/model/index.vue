<template>
  <div class="app-container model-page">
    <div class="page-head">
      <div class="page-head-main">
        <div class="page-title">模型治理</div>
        <div class="page-desc">
          参考 MLflow Model Registry 的「版本 + 阶段 + 灰度」模型：模型重训即产生新版本，
          上线前先做预演（候选版本与线上版本并行打分对比），确认无跳变后再切换，出问题可一键回滚；
          漂移监控持续回答「数据分布是否还稳定」。
        </div>
      </div>
      <div class="page-head-actions">
        <el-button size="small" type="primary" :loading="syncing" @click="sync">同步注册表</el-button>
      </div>
    </div>

    <!-- ============ 引擎 / 影子 / 漂移 ============ -->
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
          <li>影子用真实流量验证，预演用历史采样验证，两者互补。</li>
        </ul>
      </el-card>

      <el-card shadow="never" class="gov-card">
        <div class="list-toolbar drift-head">
          <div class="section-title">漂移监控（PSI / KS）</div>
          <el-button size="mini" type="primary" plain :loading="driftRunning" @click="runDrift">
            {{ driftRunning ? '检测中…' : '运行漂移检测' }}
          </el-button>
        </div>
        <template v-if="drift">
          <el-alert
            v-if="drift.maxPsi >= 0.25"
            type="error"
            :closable="false"
            class="drift-alert"
            :title="`检测到显著漂移：${drift.worstPlatform || '-'} / ${drift.worstFeature || '-'}，建议复核数据并评估重训`"
          />
          <el-alert
            v-else-if="drift.maxPsi >= 0.1"
            type="warning"
            :closable="false"
            class="drift-alert"
            :title="`存在中等漂移：${drift.worstPlatform || '-'} / ${drift.worstFeature || '-'}，建议关注`"
          />
          <div class="shadow-stats">
            <div class="stat">
              <div class="stat-label">最大 PSI</div>
              <div class="stat-value" :class="drift.maxPsi >= 0.25 ? 'tone-bad' : (drift.maxPsi >= 0.1 ? 'tone-warn' : 'tone-ok')">
                {{ drift.maxPsi == null ? '-' : drift.maxPsi.toFixed(3) }}
              </div>
            </div>
            <div class="stat">
              <div class="stat-label">稳定特征占比</div>
              <div class="stat-value">{{ drift.stableRatio == null ? '-' : (drift.stableRatio * 100).toFixed(0) + '%' }}</div>
            </div>
            <div class="stat">
              <div class="stat-label">漂移最严重</div>
              <div class="stat-value drift-worst">{{ drift.worstPlatform || '-' }}</div>
            </div>
          </div>
          <ul class="gov-notes">
            <li>
              以 <b>{{ drift.referenceCn || '抖音' }}</b> 为基准分布，对比各平台 {{ driftDetailCount }} 项「平台 × 特征」的 PSI/KS；
              PSI &lt; 0.1 稳定，0.1~0.25 中等，≥ 0.25 显著。
            </li>
            <li class="muted">最近检测：{{ fmtTime(drift.createTime) }}</li>
          </ul>
        </template>
        <app-empty v-else compact title="还没有漂移报告" description="点击「运行漂移检测」生成首份报告" />
      </el-card>
    </div>

    <!-- ============ 版本与阶段 ============ -->
    <el-card shadow="never" class="gov-card">
      <div class="list-toolbar">
        <div class="section-title">版本注册表</div>
        <span class="muted">更新于 {{ registry.updatedAt || '-' }}；切换前默认要求通过上线预演</span>
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
        <el-table-column label="线上版本" min-width="200">
          <template #default="{ row }">
            <span>{{ row.activeVersion || '-' }}</span>
            <el-tag
              v-if="row.activeVersion && row.activeArtifactAvailable === false"
              type="danger"
              size="small"
              effect="plain"
              class="artifact-tag"
            >归档缺失，请重新同步</el-tag>
          </template>
        </el-table-column>
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
        <el-table-column label="数据版本" width="170">
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
        <el-table-column label="操作" width="300">
          <template #default="{ row }">
            <el-select
              v-if="(row.versions || []).length > 1"
              v-model="promoteTarget[row.model]"
              size="mini"
              placeholder="切换版本"
              class="version-select"
              @change="v => onTargetChange(row.model, v)"
            >
              <el-option
                v-for="v in row.versions"
                :key="v.version"
                :label="v.version + (v.version === row.activeVersion ? '（当前）' : '') + (v.artifactAvailable ? '' : '（无归档）')"
                :value="v.version"
                :disabled="!v.artifactAvailable"
              />
            </el-select>
            <el-tag
              v-if="rehearsalTag(row)"
              size="small"
              effect="plain"
              :type="rehearsalTag(row).type"
              class="rehearsal-tag"
            >{{ rehearsalTag(row).text }}</el-tag>
            <el-button
              link
              type="primary"
              size="small"
              :disabled="!canPromote(row)"
              :loading="rehearsalRunning[row.model]"
              @click="rehearse(row)"
            >预演</el-button>
            <el-button
              link
              type="primary"
              size="small"
              :disabled="!canPromote(row)"
              @click="promote(row)"
            >切换</el-button>
            <el-button
              link
              type="warning"
              size="small"
              :disabled="!canRollback(row)"
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

    <!-- ============ 预演报告对话框 ============ -->
    <el-dialog
      v-model="rehearsalDialog.visible"
      width="640px"
      :title="`上线预演报告：${rehearsalDialog.model} ${rehearsalDialog.version}`"
      destroy-on-close
    >
      <div v-loading="rehearsalDialog.loading">
        <template v-if="rehearsalDialog.report">
          <div class="rehearsal-summary">
            <el-tag :type="rehearsalDialog.report.passed ? 'success' : 'danger'" effect="dark" size="medium">
              {{ rehearsalDialog.report.passed ? '预演通过，允许上线' : '预演未通过' }}
            </el-tag>
            <span class="muted">
              线上 {{ rehearsalDialog.report.activeVersion }} vs 候选 {{ rehearsalDialog.report.candidateVersion }}，
              采样 {{ rehearsalDialog.report.sampleSize }} 条
            </span>
          </div>
          <div class="rehearsal-metrics">
            <div class="metric">
              <div class="metric-label">平均绝对偏差</div>
              <div class="metric-value">{{ pct(rehearsalDialog.report.meanAbsDiffPct) }}</div>
              <div class="metric-th">阈值 ≤ 10%</div>
            </div>
            <div class="metric">
              <div class="metric-label">相关性（log）</div>
              <div class="metric-value">{{ rehearsalDialog.report.pearsonCorr }}</div>
              <div class="metric-th">阈值 ≥ 0.95</div>
            </div>
            <div class="metric">
              <div class="metric-label">头部 10% 重合</div>
              <div class="metric-value">{{ overlap(rehearsalDialog.report.top10Overlap) }}</div>
              <div class="metric-th">阈值 ≥ 70%</div>
            </div>
            <div class="metric">
              <div class="metric-label">P90 偏差</div>
              <div class="metric-value">{{ pct(rehearsalDialog.report.p90AbsDiffPct) }}</div>
              <div class="metric-th">参考</div>
            </div>
          </div>
          <template v-if="worstCases.length">
            <div class="section-title worst-title">偏差最大样本（人工复核用）</div>
            <el-table :data="worstCases" size="small">
              <el-table-column label="类别" width="90">
                <template #default="{ row }">{{ row.input.category }}</template>
              </el-table-column>
              <el-table-column label="粉丝数" width="110">
                <template #default="{ row }">{{ fmtNum(row.input.fans) }}</template>
              </el-table-column>
              <el-table-column label="线上预测" width="110">
                <template #default="{ row }">{{ fmtNum(row.activePrediction) }}</template>
              </el-table-column>
              <el-table-column label="候选预测" width="110">
                <template #default="{ row }">{{ fmtNum(row.candidatePrediction) }}</template>
              </el-table-column>
              <el-table-column label="偏差">
                <template #default="{ row }">
                  <span :class="Math.abs(row.diffPct) > 20 ? 'tone-bad' : 'tone-warn'">
                    {{ (row.diffPct > 0 ? '+' : '') + row.diffPct.toFixed(2) }}%
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </template>
        </template>
        <app-empty v-else compact title="暂无预演报告" description="关闭后点击「预演」运行" />
      </div>
      <template #footer>
        <el-button size="small" @click="rehearsalDialog.visible = false">关闭</el-button>
        <el-button
          v-if="rehearsalDialog.report && rehearsalDialog.report.passed"
          size="small"
          type="primary"
          @click="promoteAfterRehearsal"
        >立即切换</el-button>
      </template>
    </el-dialog>
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
      drift: null,
      driftRunning: false,
      loading: false,
      syncing: false,
      promoteTarget: {},
      rehearsalMap: {},
      rehearsalRunning: {},
      rehearsalDialog: { visible: false, loading: false, report: null, model: '', version: '' }
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
    },
    driftDetailCount () {
      return ((this.drift && this.drift.detail) || []).length
    },
    worstCases () {
      const r = this.rehearsalDialog.report
      return (r && r.detail && r.detail.worstCases) || []
    }
  },
  created () {
    this.loadAll()
  },
  beforeUnmount () {
    this.clearPoll()
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
      this.loadDrift()
    },
    loadDrift () {
      modelApi.driftLatest().then(re => { this.drift = re.response || null }).catch(() => {})
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
    // ---------------- 漂移检测 ----------------
    runDrift () {
      this.driftRunning = true
      modelApi.driftRun().then(re => {
        const jobId = re.response && re.response.jobId
        this.$message.info('漂移检测已提交，正在执行…')
        this.pollJob(jobId, () => {
          this.driftRunning = false
          this.$message.success('漂移检测完成')
          this.loadDrift()
        }, err => {
          this.driftRunning = false
          this.$message.error('漂移检测失败：' + (err || '请查看后端日志'))
        })
      }).catch(() => { this.driftRunning = false })
    },
    // ---------------- 上线预演 ----------------
    onTargetChange (model, version) {
      if (!version) return
      modelApi.rehearsalLatest(model, version).then(re => {
        this.rehearsalMap[model] = re.response || null
      }).catch(() => {
        this.rehearsalMap[model] = null
      })
    },
    rehearsalTag (row) {
      const version = this.promoteTarget[row.model]
      if (!version) return null
      const r = this.rehearsalMap[row.model]
      if (!r || r.candidateVersion !== version) return null
      if (r.activeVersion !== row.activeVersion) {
        return { type: 'info', text: '预演已过期' }
      }
      return r.passed ? { type: 'success', text: '预演通过' } : { type: 'danger', text: '预演未通过' }
    },
    rehearse (row) {
      const version = this.promoteTarget[row.model]
      if (!version) return
      this.rehearsalRunning[row.model] = true
      modelApi.rehearsalRun(row.model, version).then(re => {
        const jobId = re.response && re.response.jobId
        this.$message.info('预演已提交：候选版本与线上版本并行打分中…')
        this.pollJob(jobId, () => {
          this.rehearsalRunning[row.model] = false
          this.openRehearsalReport(row.model, version, row.activeVersion)
        }, err => {
          this.rehearsalRunning[row.model] = false
          this.$message.error('预演失败：' + (err || '请查看后端日志'))
        })
      }).catch(() => {
        this.rehearsalRunning[row.model] = false
      })
    },
    openRehearsalReport (model, version, activeVersion) {
      this.rehearsalDialog = { visible: true, loading: true, report: null, model, version }
      modelApi.rehearsalLatest(model, version).then(re => {
        this.rehearsalDialog.loading = false
        this.rehearsalDialog.report = re.response || null
        this.rehearsalMap[model] = this.rehearsalDialog.report
      }).catch(() => {
        this.rehearsalDialog.loading = false
      })
    },
    promoteAfterRehearsal () {
      const { model, version } = this.rehearsalDialog
      this.rehearsalDialog.visible = false
      this.doPromote(model, version, false)
    },
    // ---------------- 版本切换 / 回滚 ----------------
    selectedVersion (row) {
      return (row.versions || []).find(v => v.version === this.promoteTarget[row.model]) || null
    },
    // 只有归档文件存在且不是当前版本的版本才能上线；缺失归档的历史版本只可查看
    canPromote (row) {
      const v = this.selectedVersion(row)
      return !!v && v.artifactAvailable !== false && v.version !== row.activeVersion
    },
    canRollback (row) {
      return (row.versions || []).some(v => v.artifactAvailable !== false && v.version !== row.activeVersion)
    },
    promote (row) {
      const version = this.promoteTarget[row.model]
      if (!version) return
      this.doPromote(row.model, version, false)
    },
    doPromote (model, version, force) {
      modelApi.promote(model, version, force).then(() => {
        this.$message.success(model + ' 已切换到版本 ' + version + '，派生缓存已失效')
        this.loadAll()
      }).catch(e => {
        // 409：预演门禁拦截（未预演 / 未通过 / 预演过期），提示可强制上线
        if (e && e.code === 409) {
          this.$confirm(e.message + '。仍要强制切换吗？', '上线预演门禁', {
            confirmButtonText: '强制切换',
            cancelButtonText: '取消',
            type: 'warning'
          }).then(() => {
            this.doPromote(model, version, true)
          }).catch(() => {})
          return
        }
        this.$message.error('切换失败：该版本不存在或归档文件缺失')
      })
    },
    rollback (row) {
      modelApi.rollback(row.model).then(() => {
        this.$message.success(row.model + ' 已回滚到上一版本，派生缓存已失效')
        this.loadAll()
      }).catch(() => this.$message.error('回滚失败：没有可用的历史归档版本'))
    },
    // ---------------- 任务轮询 ----------------
    pollJob (jobId, onDone, onFailed) {
      this.clearPoll()
      let ticks = 0
      this._pollTimer = setInterval(() => {
        ticks += 1
        if (ticks > 120) { // 最长 6 分钟（3s × 120）
          this.clearPoll()
          onFailed('轮询超时')
          return
        }
        modelApi.job(jobId).then(re => {
          const job = re.response || {}
          if (job.status === 'DONE') {
            this.clearPoll()
            onDone(job)
          } else if (job.status === 'FAILED') {
            this.clearPoll()
            onFailed(job.errorMsg)
          }
        }).catch(() => {})
      }, 3000)
    },
    clearPoll () {
      if (this._pollTimer) {
        clearInterval(this._pollTimer)
        this._pollTimer = null
      }
    },
    // ---------------- 格式化 ----------------
    pct (v) {
      return v == null ? '-' : v.toFixed(2) + '%'
    },
    overlap (v) {
      return v == null ? '-' : (v * 100).toFixed(0) + '%'
    },
    fmtNum (v) {
      return v == null ? '-' : Math.round(v).toLocaleString()
    },
    fmtTime (v) {
      if (v == null) return '-'
      const d = typeof v === 'number' ? new Date(v) : new Date(String(v).replace(' ', 'T'))
      if (Number.isNaN(d.getTime())) return String(v)
      const p = n => String(n).padStart(2, '0')
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
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
  width: 130px;
  margin-right: 6px;
}

.rehearsal-tag {
  margin-right: 4px;
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

/* 归档缺失提醒：紧跟线上版本展示，避免用户误以为该版本可回滚 */
.artifact-tag {
  margin-left: 8px;
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

/* 漂移监控 */
.drift-head {
  margin-bottom: 10px;
}

.drift-alert {
  margin-bottom: 10px;
}

.drift-worst {
  font-size: 15px !important;
}

/* 预演报告 */
.rehearsal-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.rehearsal-metrics {
  display: flex;
  gap: 12px;
  margin-bottom: 14px;
}

.metric {
  flex: 1;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px 12px;

  .metric-label {
    font-size: 11.5px;
    color: #94a3b8;
    margin-bottom: 4px;
  }

  .metric-value {
    font-size: 18px;
    font-weight: 700;
    color: #1e293b;
  }

  .metric-th {
    font-size: 11px;
    color: #b6c2d2;
    margin-top: 2px;
  }
}

.worst-title {
  margin: 4px 0 8px;
}
</style>
