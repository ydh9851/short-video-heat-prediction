<template>
  <div class="scenario-tray-root">
    <!-- 收起态托盘 -->
    <transition name="tray-slide">
      <div v-if="items.length && !isScreen" class="compare-tray">
        <div class="tray-head">
          <span class="tray-icon">⇄</span>
          <span class="tray-title">场景对比</span>
          <span class="tray-count">{{ items.length }}/3</span>
          <span class="tray-spacer" />
          <el-button link size="small" @click="clearAll">清空</el-button>
        </div>
        <div class="tray-body">
          <div v-for="it in items" :key="it.id" class="tray-chip" :title="it.name">
            <span class="chip-name">{{ it.name }}</span>
            <span class="chip-remove" @click="removeItem(it.id)">×</span>
          </div>
        </div>
        <el-button
          type="primary"
          size="small"
          class="tray-compare"
          :disabled="items.length < 2"
          @click="openCompare">
          开始对比{{ items.length > 1 ? `（${items.length}）` : '' }}
        </el-button>
        <div v-if="items.length < 2" class="tray-tip">再选择 {{ 2 - items.length }} 个场景即可对比</div>
      </div>
    </transition>

    <!-- 对比弹窗 -->
    <el-dialog v-model="visible" title="场景对比" width="1080px" top="6vh" append-to-body>
      <div v-loading="loading" class="compare-wrap">
        <div v-if="loadError" class="load-error">{{ loadError }}</div>
        <div v-else-if="compareItems.length" class="compare-table">
          <div class="compare-row head">
            <div class="compare-label">指标</div>
            <div v-for="it in compareItems" :key="it.id" class="compare-cell head-cell">
              <div class="head-name">{{ it.name }}</div>
              <div class="head-tags">
                <el-tag size="small" effect="plain">{{ (it.model || 'lgbm').toUpperCase() }}</el-tag>
                <el-tag v-if="it.error" size="small" type="danger" effect="light">计算失败</el-tag>
              </div>
              <div class="head-actions">
                <el-button link type="primary" size="small" @click="viewAttribution(it)">查看归因</el-button>
                <el-button link type="danger" size="small" @click="removeItem(it.id)">移出</el-button>
              </div>
            </div>
          </div>
          <div v-for="row in compareRows" :key="row.key" class="compare-row">
            <div class="compare-label">{{ row.label }}</div>
            <div
              v-for="it in compareItems"
              :key="it.id"
              class="compare-cell"
              :class="cellClass(it, row)">
              {{ cellValue(it, row) }}
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <span class="compare-meta">{{ result.generatedAt ? '生成于 ' + result.generatedAt : '' }}</span>
        <el-button @click="visible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { mapState } from 'vuex'
import caseApi from '@/api/case'

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

export default {
  name: 'ScenarioCompareTray',
  data () {
    return {
      visible: false,
      loading: false,
      loadError: '',
      result: {}
    }
  },
  computed: {
    ...mapState('caseCompare', ['items']),
    compareItems () {
      return this.result.items || []
    },
    isScreen () {
      return (this.$route.path || '').startsWith('/screen')
    },
    compareRows () {
      return [
        { label: '预测热度', key: 'prediction' },
        { label: '90% 区间', key: 'interval' },
        { label: '热度等级', key: 'grade' },
        { label: '视频类别', key: 'videoCategory' },
        { label: '粉丝数', key: 'authorFans' },
        { label: '发布时间', key: 'publishTime' },
        { label: '相对基准', key: 'delta' },
        { label: '计算状态', key: 'status' }
      ]
    }
  },
  methods: {
    openCompare () {
      if (this.items.length < 2) return
      this.visible = true
      this.loadError = ''
      this.result = {}
      this.loading = true
      caseApi.compare(this.items.map(i => i.id)).then(re => {
        this.result = re.response || {}
      }).catch(() => {
        this.loadError = '对比计算失败，请稍后重试（首次计算可能需要预热模型）'
      }).finally(() => {
        this.loading = false
      })
    },
    removeItem (id) {
      this.$store.dispatch('caseCompare/remove', id)
      if (this.items.length < 2) {
        this.visible = false
      } else if (this.visible) {
        // 已打开的对比结果同步剔除该列，避免重新触发耗时的区间计算
        this.result = {
          ...this.result,
          items: this.compareItems.filter(i => i.id !== id)
        }
      }
    },
    clearAll () {
      this.$store.dispatch('caseCompare/clear')
      this.visible = false
    },
    viewAttribution (item) {
      // 把对比列还原为当前场景，归因页直接复用参数
      this.$store.dispatch('caseStudy/setCurrent', {
        id: item.id,
        name: item.name,
        model: item.model,
        videoCategory: item.videoCategory,
        authorFans: item.authorFans,
        publishHour: item.publishHour,
        publishWeekday: item.publishWeekday,
        publishMonth: item.publishMonth
      })
      this.visible = false
      this.$router.push('/attribution')
    },
    cellValue (item, row) {
      if (row.key === 'status') {
        return item.error ? `失败：${item.error}` : '成功'
      }
      if (item.error) {
        return '—'
      }
      switch (row.key) {
        case 'prediction':
          return item.prediction == null ? '—' : this.fmtNum(item.prediction)
        case 'interval':
          return item.lo == null || item.hi == null
            ? '—'
            : `${this.fmtNum(item.lo)} ~ ${this.fmtNum(item.hi)}`
        case 'grade':
          return item.grade || '—'
        case 'videoCategory':
          return item.videoCategory || '—'
        case 'authorFans':
          return this.fmtFans(item.authorFans)
        case 'publishTime':
          return `${WEEKDAYS[Number(item.publishWeekday || 0)] || '—'} ${item.publishHour}:00 · ${item.publishMonth}月`
        case 'delta': {
          const base = this.compareItems[0]
          if (item.prediction == null || !base || base.prediction == null) return '—'
          if (base.id === item.id) return '基准'
          const pct = (item.prediction - base.prediction) / base.prediction * 100
          return `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`
        }
        default:
          return '—'
      }
    },
    cellClass (item, row) {
      return {
        'cell-strong': row.key === 'prediction',
        'cell-error': row.key === 'status' && !!item.error,
        'cell-up': row.key === 'delta' && !item.error && this.deltaValue(item) > 0,
        'cell-down': row.key === 'delta' && !item.error && this.deltaValue(item) < 0
      }
    },
    deltaValue (item) {
      const base = this.compareItems[0]
      if (item.prediction == null || !base || base.prediction == null || base.id === item.id) return 0
      return item.prediction - base.prediction
    },
    fmtNum (v) {
      const n = Number(v)
      return isFinite(n) ? Math.round(n).toLocaleString('en-US') : '—'
    },
    fmtFans (v) {
      const n = Number(v || 0)
      if (n >= 10000) return `${(n / 10000).toFixed(1).replace(/\.0$/, '')} 万`
      return String(n)
    }
  }
}
</script>

<style lang="scss" scoped>
.scenario-tray-root {
  position: fixed;
  right: 24px;
  /* 抬高一档，避免与右下角「回到顶部」按钮重叠 */
  bottom: 96px;
  z-index: 1500;
  pointer-events: none;
}

.compare-tray {
  width: 300px;
  padding: 12px;
  background: #fff;
  border: 1px solid #e4e9f2;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.16);
  pointer-events: auto;
}

.tray-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.tray-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 13px;
  font-weight: 700;
}

.tray-title {
  font-size: 13px;
  font-weight: 600;
  color: #1f2a44;
}

.tray-count {
  font-size: 12px;
  color: #8a93a6;
}

.tray-spacer {
  flex: 1;
}

.tray-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.tray-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  background: #f8faff;
  border: 1px solid #e8ecf6;
  border-radius: 8px;
}

.chip-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: #334155;
}

.chip-remove {
  flex: 0 0 auto;
  color: #94a3b8;
  cursor: pointer;
  font-size: 15px;
  line-height: 1;

  &:hover { color: #ef4444; }
}

.tray-compare {
  width: 100%;
}

.tray-tip {
  margin-top: 6px;
  font-size: 11px;
  color: #94a3b8;
  text-align: center;
}

.tray-slide-enter-active,
.tray-slide-leave-active {
  transition: all 0.22s ease;
}

.tray-slide-enter-from,
.tray-slide-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

/* ---------- 对比弹窗 ---------- */
.compare-wrap {
  min-height: 180px;
}

.load-error {
  padding: 48px 0;
  text-align: center;
  color: #ef4444;
  font-size: 13px;
}

.compare-table {
  width: 100%;
  border: 1px solid #e8ecf6;
  border-radius: 10px;
  overflow: hidden;
}

.compare-row {
  display: flex;
  border-bottom: 1px solid #eef1f8;

  &:last-child { border-bottom: none; }

  &.head {
    background: #f8faff;
  }
}

.compare-label {
  flex: 0 0 110px;
  padding: 12px 14px;
  background: #fbfcff;
  border-right: 1px solid #eef1f8;
  font-size: 12px;
  color: #8a93a6;
  display: flex;
  align-items: center;
}

.compare-cell {
  flex: 1;
  min-width: 0;
  padding: 12px 14px;
  border-right: 1px solid #eef1f8;
  font-size: 13px;
  color: #334155;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  word-break: break-all;

  &:last-child { border-right: none; }

  &.cell-strong {
    font-size: 20px;
    font-weight: 700;
    color: #4338ca;
  }

  &.cell-error { color: #ef4444; font-size: 12px; }
  &.cell-up { color: #16a34a; font-weight: 600; }
  &.cell-down { color: #dc2626; font-weight: 600; }
}

.head-cell {
  gap: 4px;
}

.head-name {
  font-size: 13px;
  font-weight: 600;
  color: #1f2a44;
  margin-bottom: 2px;
}

.head-tags {
  display: flex;
  gap: 4px;
  margin-bottom: 2px;
}

.head-actions {
  display: flex;
  gap: 2px;
}

.compare-meta {
  float: left;
  line-height: 32px;
  font-size: 12px;
  color: #94a3b8;
}
</style>
