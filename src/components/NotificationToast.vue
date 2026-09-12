<script setup>
import { storeToRefs } from 'pinia'
import { CheckCircle2, CircleAlert } from 'lucide-vue-next'
import { useMessagesStore } from '../stores/messages'
const { toast } = storeToRefs(useMessagesStore())
</script>
<template>
  <Transition name="toast">
    <div v-if="toast" class="toast" :class="toast.type" role="status">
      <CheckCircle2 v-if="toast.type === 'success'" :size="19" /><CircleAlert v-else :size="19" />
      {{ toast.text }}
    </div>
  </Transition>
</template>
<style scoped>
.toast { position: fixed; z-index: 150; right: 24px; bottom: 24px; display: flex; align-items: center; gap: 9px; max-width: min(390px, calc(100vw - 32px)); padding: 14px 16px; color: #fff; background: #5b876e; border-radius: 14px; box-shadow: var(--shadow); font-size: 13px; font-weight: 700; }.toast.error { background: #b96767; }.toast-enter-active,.toast-leave-active { transition: .25s ease; }.toast-enter-from,.toast-leave-to { opacity: 0; transform: translateY(12px); }@media(max-width:600px){.toast{right:16px;bottom:16px;}}</style>
