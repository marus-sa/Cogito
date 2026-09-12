<script setup>
defineProps({ value: { type: Number, default: 0 }, color: { type: String, default: 'var(--primary)' }, showLabel: { type: Boolean, default: true } })
</script>
<template>
  <div class="progress-wrap">
    <div class="track"><span :style="{ width: `${Math.min(100, value)}%`, background: color }"></span></div>
    <small v-if="showLabel">{{ value }}%</small>
  </div>
</template>
<style scoped>
.progress-wrap { display: flex; align-items: center; gap: 10px; }
.track { height: 8px; flex: 1; overflow: hidden; background: #ece9f1; border-radius: 100px; }
.track span { display: block; height: 100%; border-radius: inherit; transition: width .45s ease; }
small { color: var(--text-secondary); font-size: 11px; font-weight: 800; }
</style>
