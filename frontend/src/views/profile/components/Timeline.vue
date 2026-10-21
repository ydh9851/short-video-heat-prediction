<template>
  <div class="block">
    <el-timeline>
      <el-timeline-item  placement="top" :timestamp="userInfo.lastActiveTime">
        <el-card>
          <h4>最后活动时间</h4>
          <p>{{ (userInfo.userName || '该账号') + ' 在本系统中的最后活动时间' }}</p>
        </el-card>
      </el-timeline-item>
      <el-timeline-item  placement="top" :timestamp="userInfo.createTime">
        <el-card>
          <h4>加入时间</h4>
          <p>{{ (userInfo.userName || '该账号') + ' 加入短视频热度预测与归因分析系统' }}</p>
        </el-card>
      </el-timeline-item>
    </el-timeline>
  </div>
</template>

<script>

export default {
  props: {
    userInfo: {
      type: Object,
      default: () => {
        return {
          realName: '',
          lastActiveTime: '',
          createTime: ''
        }
      }
    }
  }
}
</script>
