<template>
  <!-- 品牌标识：短视频（播放三角）+ 热度上升（递增柱），使用 currentColor 以便随主题着色 -->
  <svg
    class="brand-mark-svg"
    viewBox="0 0 32 32"
    xmlns="http://www.w3.org/2000/svg"
    fill="currentColor"
    aria-hidden="true"
    focusable="false">
    <path d="M4.1 11.2c0-1.26 1.36-2.05 2.46-1.42l7.96 4.55a1.63 1.63 0 0 1 0 2.83l-7.96 4.55A1.63 1.63 0 0 1 4.1 20.31V11.2Z" />
    <rect x="17.6" y="18.2" width="2.7" height="3.6" rx="1.35" opacity=".5" />
    <rect x="21.4" y="14.6" width="2.7" height="7.2" rx="1.35" opacity=".76" />
    <rect x="25.2" y="10.4" width="2.7" height="11.4" rx="1.35" />
  </svg>
</template>

<script>
export default {
  name: 'BrandMark'
}
</script>

<style scoped>
.brand-mark-svg {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
