<script setup>
import { LoaderCircle } from 'lucide-vue-next'

defineProps({
  variant: { type: String, default: 'primary' },
  size: { type: String, default: 'md' },
  loading: Boolean,
  block: Boolean,
  type: { type: String, default: 'button' },
})
</script>

<template>
  <button :type="type" class="base-button" :class="[`is-${variant}`, `is-${size}`, { 'is-block': block }]" :disabled="loading">
    <LoaderCircle v-if="loading" :size="16" class="spin" />
    <slot v-else />
  </button>
</template>

<style scoped>
.base-button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; border: 1px solid transparent; border-radius: 12px; font-weight: 800; transition: .2s ease; white-space: nowrap; }
.base-button:focus-visible { outline: 3px solid rgba(130, 103, 199, .28); outline-offset: 2px; }
.is-md { min-height: 42px; padding: 0 15px; font-size: 13px; }
.is-sm { min-height: 34px; padding: 0 11px; font-size: 12px; }
.is-primary { color: #fff; background: var(--primary); box-shadow: 0 4px 9px rgba(98, 70, 168, .17); }
.is-primary:hover:not(:disabled) { background: var(--primary-dark); transform: translateY(-1px); }
.is-secondary { color: var(--primary-dark); background: var(--primary-extra-light); }
.is-secondary:hover:not(:disabled) { background: var(--primary-light); }
.is-outline { color: #5e556b; background: #fff; border-color: var(--border); }
.is-outline:hover:not(:disabled) { color: var(--primary-dark); border-color: var(--primary-light); background: #fbf9ff; }
.is-danger { color: #b15959; background: #fff; border-color: #edcdcd; }
.is-danger:hover:not(:disabled) { background: #fff5f5; }
.is-ghost { color: var(--primary-dark); background: transparent; }
.is-ghost:hover:not(:disabled) { background: var(--primary-extra-light); }
.is-block { width: 100%; }
.base-button:disabled { cursor: not-allowed; opacity: .7; }
.spin { animation: rotate .8s linear infinite; }
@keyframes rotate { to { transform: rotate(360deg); } }
</style>
