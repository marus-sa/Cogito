<script setup>
defineProps({ initials: { type: String, default: '?' }, color: { type: String, default: '#d9cdf5' }, size: { type: Number, default: 38 } })
</script>
<template><span class="avatar" :style="{ background: color, width: `${size}px`, height: `${size}px`, fontSize: `${Math.max(10, size * .29)}px` }">{{ initials }}</span></template>
<style scoped>.avatar { display: inline-grid; place-items: center; flex: 0 0 auto; color: #4b3d5d; border: 2px solid rgba(255,255,255,.8); border-radius: 50%; font-weight: 800; }</style>
