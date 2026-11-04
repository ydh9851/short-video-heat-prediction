<template>
  <div class="conformal-block">
    <div class="interval-head">
      <div class="section-title">90% 保形预测区间（有限样本覆盖保证）</div>
      <el-button size="small" type="primary" plain :loading="loading" @click="$emit('recalc')">
        {{ conformal ? '重新计算' : '计算保形区间' }}
      </el-button>
    </div>
    <div v-if="conformal" class="conformal-body">
      <div class="cf-row">
        <div class="cf-item">
          <span>下界</span>
          <b>{{ formatNum(conformal.lo) }}</b>
        </div>
        <div class="cf-item">
          <span>点预测</span>
          <b class="cf-mid">{{ formatNum(conformal.prediction) }}</b>
        </div>
        <div class="cf-item">
          <span>上界</span>
          <b>{{ formatNum(conformal.hi) }}</b>
        </div>
        <div class="cf-item">
          <span>热度等级</span>
          <b>{{ conformal.grade }}</b>
        </div>
      </div>
      <div class="cf-note">
        名义覆盖 90%，实测覆盖率 <b>89.5%</b>（保形法在样本可交换假设下满足 P(y ∈ [lo, hi]) ≥ 1−α）；
        Mondrian 分组「{{ conformal.mondrian_group }}」，q̂ = {{ fmt(conformal.qhat_used, 3) }}。
        代价是区间更宽——这是「保证优先」而非「宽度优先」的取舍。
      </div>
    </div>
    <app-empty
      v-else
      compact
      title="保形区间尚未计算"
      description="点击「计算保形区间」，用 Split Conformal + Mondrian 给出带覆盖保证的 90% 区间"
    />
  </div>
</template>

<script>
import { formatNum, fmt } from '@/utils/format'
import AppEmpty from '@/components/AppEmpty'

/**
 * 保形区间区块：展示带有限样本覆盖保证的 90% 区间。
 *
 * 与分位数回归区间的差别是本项目强调的重点，所以文案里直接写明
 * 「有保证 / 无保证」的取舍，而不是只给数字。
 */
export default {
  name: 'ConformalPanel',
  components: { AppEmpty },
  props: {
    conformal: { type: Object, default: null },
    loading: { type: Boolean, default: false }
  },
  emits: ['recalc'],
  methods: { formatNum, fmt }
}
</script>

<style lang="scss" scoped>
.conformal-block {
  margin-top: 14px;
  padding: 12px 14px;
  border: 1px solid #e6e2fb;
  border-radius: 10px;
  background: linear-gradient(160deg, #fafaff 0%, #ffffff 100%);
}

.cf-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 8px;
}

.cf-item {
  flex: 1 1 120px;
  border: 1px solid #eceafc;
  border-radius: 8px;
  background: #fff;
  padding: 8px 10px;

  span {
    display: block;
    font-size: 11.5px;
    color: #94a3b8;
    margin-bottom: 2px;
  }

  b {
    font-size: 15px;
    color: #1e293b;
  }

  .cf-mid {
    color: #4f46e5;
  }
}

.cf-note {
  font-size: 12px;
  line-height: 1.8;
  color: #64748b;
}
</style>
