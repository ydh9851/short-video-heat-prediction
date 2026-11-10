<template>
  <div class="case-bar">
    <el-popover v-if="current" placement="bottom-start" :width="320" trigger="hover">
      <template #reference>
        <div class="case-chip active">
          <span class="dot" />
          <span class="name">{{ current.name }}</span>
          <span class="clear" title="清除当前场景" @click.stop="onClear">×</span>
        </div>
      </template>
      <div class="case-detail">
        <div class="title">{{ current.name }}</div>
        <div class="row"><span class="k">模型</span><span class="v">{{ current.model || 'lgbm' }}</span></div>
        <div class="row"><span class="k">视频类别</span><span class="v">{{ current.videoCategory }}</span></div>
        <div class="row"><span class="k">作者粉丝数</span><span class="v">{{ formatFans(current.authorFans) }}</span></div>
        <div class="row">
          <span class="k">发布时间</span>
          <span class="v">{{ current.publishHour }}时 · 周{{ weekdayText(current.publishWeekday) }} · {{ current.publishMonth }}月</span>
        </div>
        <div class="actions">
          <el-button size="small" @click="goLibrary">切换场景</el-button>
          <el-button size="small" type="danger" plain @click="onClear">清除</el-button>
        </div>
      </div>
    </el-popover>
    <div v-else class="case-chip empty" title="选择分析场景后，预测/归因页将自动填充参数" @click="goLibrary">
      <span class="dot" />
      <span class="name">未选择场景</span>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'CaseBar',
  computed: {
    ...mapGetters(['currentCase']),
    current () {
      return this.currentCase
    }
  },
  methods: {
    goLibrary () {
      this.$router.push({ path: '/case/index' })
    },
    onClear () {
      this.$store.dispatch('caseStudy/clearCurrent')
    },
    formatFans (v) {
      const n = Number(v || 0)
      if (n >= 10000) return (n / 10000).toFixed(1).replace(/\.0$/, '') + ' 万'
      return String(n)
    },
    weekdayText (w) {
      // 算法侧 weekday 语义：0=周一 … 6=周日（pandas dt.weekday）
      return ['一', '二', '三', '四', '五', '六', '日'][Number(w || 0)] || w
    }
  }
}
</script>

<style lang="scss" scoped>
.case-bar {
  display: flex;
  align-items: center;
  margin-left: 12px;
}

.case-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border-radius: 14px;
  font-size: 12.5px;
  cursor: pointer;
  transition: background .2s, border-color .2s;

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  &.active {
    background: rgba(99, 102, 241, .1);
    border: 1px solid rgba(99, 102, 241, .35);
    color: #4f46e5;

    .dot { background: #6366f1; }

    .clear {
      margin-left: 2px;
      font-size: 14px;
      line-height: 1;
      color: #a5b4fc;
      &:hover { color: #ef4444; }
    }
  }

  &.empty {
    background: #f8fafc;
    border: 1px dashed #cbd5e1;
    color: #94a3b8;

    .dot { background: #cbd5e1; }

    &:hover {
      border-color: #6366f1;
      color: #6366f1;
      .dot { background: #6366f1; }
    }
  }

  .name {
    max-width: 160px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.case-detail {
  .title {
    font-size: 14px;
    font-weight: 600;
    color: #1e293b;
    margin-bottom: 8px;
  }
  .row {
    display: flex;
    justify-content: space-between;
    font-size: 12.5px;
    padding: 3px 0;
    .k { color: #94a3b8; }
    .v { color: #334155; font-weight: 500; }
  }
  .actions {
    margin-top: 10px;
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
}
</style>
