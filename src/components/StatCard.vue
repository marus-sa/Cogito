<script setup>
import { computed } from 'vue'
import * as Icons from 'lucide-vue-next'
const props = defineProps({ label: String, value: [String, Number], detail: String, icon: { type: String, default: 'Sparkles' }, tone: { type: String, default: 'purple' } })
const iconComponent = computed(() => Icons[props.icon] || Icons.Sparkles)
</script>
<template>
  <article class="stat-card card card-hover">
    <div class="stat-top"><span :class="['stat-icon', tone]"><component :is="iconComponent" :size="19" /></span><span v-if="detail" class="detail">{{ detail }}</span></div>
    <div class="value">{{ value }}</div>
    <div class="label">{{ label }}</div>
  </article>
</template>
<style scoped>
.stat-card { min-height: 143px; padding: 18px; }
.stat-top { display: flex; align-items: center; justify-content: space-between; }
.stat-icon { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 13px; }
.stat-icon.purple { color: var(--primary-dark); background: var(--primary-extra-light); }.stat-icon.green { color: #4a8965; background: #e7f4ed; }.stat-icon.orange { color: #ae8035; background: #fcf3e2; }.stat-icon.rose { color: #b56871; background: #faecef; }
.detail { color: #538d6b; font-size: 11px; font-weight: 800; }
.value { margin-top: 15px; font-size: 27px; letter-spacing: -1px; font-weight: 800; }.label { margin-top: 2px; color: var(--text-secondary); font-size: 12px; }
</style>
