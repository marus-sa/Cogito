<script setup>
import { computed } from 'vue'
const props = defineProps({ values: { type: Array, default: () => [] }, labels: { type: Array, default: () => [] }, color: { type: String, default: '#8267c7' } })
const points = computed(() => props.values.map((value, index) => ({ left: `${(index / Math.max(1, props.values.length - 1)) * 100}%`, top: `${100 - value}%`, value })))
const links = computed(() => props.values.slice(0, -1).map((value, index) => {
  const next = props.values[index + 1]
  const width = 100 / Math.max(1, props.values.length - 1)
  const height = next - value
  const length = Math.sqrt(width ** 2 + height ** 2)
  return { left: `${(index / Math.max(1, props.values.length - 1)) * 100}%`, top: `${100 - value}%`, width: `${length}%`, transform: `rotate(${Math.atan2(-height, width) * 180 / Math.PI}deg)` }
}))
</script>
<template>
  <div class="chart">
    <div class="grid-line l1"></div><div class="grid-line l2"></div><div class="grid-line l3"></div>
    <i v-for="(link, index) in links" :key="`link-${index}`" class="line" :style="{ ...link, background: color }"></i>
    <span v-for="(point, index) in points" :key="index" class="point" :style="{ left: point.left, top: point.top, borderColor: color }" :aria-label="`${labels[index]}: ${point.value}%`"><em>{{ point.value }}</em></span>
  </div>
  <div class="labels"><span v-for="label in labels" :key="label">{{ label }}</span></div>
</template>
<style scoped>
.chart { position: relative; height: 165px; margin: 20px 10px 5px; border-left: 1px solid var(--border); border-bottom: 1px solid var(--border); }.grid-line { position: absolute; left: 0; width: 100%; border-top: 1px dashed #eeeaf3; }.l1 { top: 25%; }.l2 { top: 50%; }.l3 { top: 75%; }.point { position: absolute; z-index: 2; display: block; width: 10px; height: 10px; border: 3px solid; border-radius: 50%; background: #fff; transform: translate(-50%, -50%); }.point:hover em { opacity: 1; transform: translate(-50%, -4px); }.point em { position: absolute; bottom: 11px; left: 50%; padding: 3px 5px; color: #fff; background: var(--text-main); border-radius: 5px; font-size: 9px; font-style: normal; opacity: 0; transform: translate(-50%, 1px); transition: .15s; }.line { position: absolute; z-index: 1; height: 2px; transform-origin: 0 50%; }.labels { display: flex; justify-content: space-between; gap: 4px; margin: 0 10px; color: var(--text-secondary); font-size: 9px; }.labels span { white-space: nowrap; }
</style>
