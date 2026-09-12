<script setup>
import { X } from 'lucide-vue-next'

defineProps({ modelValue: Boolean, title: String, wide: Boolean })
defineEmits(['update:modelValue'])
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="modelValue" class="modal-backdrop" @mousedown.self="$emit('update:modelValue', false)">
        <section class="modal" :class="{ wide }" role="dialog" aria-modal="true" :aria-label="title">
          <header class="modal-head">
            <h2>{{ title }}</h2>
            <button class="close" aria-label="Закрыть" @click="$emit('update:modelValue', false)"><X :size="19" /></button>
          </header>
          <div class="modal-body"><slot /></div>
          <footer v-if="$slots.footer" class="modal-footer"><slot name="footer" /></footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop { position: fixed; z-index: 100; inset: 0; display: grid; place-items: center; padding: 20px; background: rgba(45, 34, 65, .36); backdrop-filter: blur(3px); }
.modal { width: min(100%, 520px); max-height: min(760px, calc(100vh - 40px)); overflow: auto; background: #fff; border-radius: 22px; box-shadow: 0 25px 70px rgba(38, 27, 63, .28); }
.modal.wide { width: min(100%, 700px); }
.modal-head { display: flex; align-items: center; justify-content: space-between; gap: 15px; padding: 20px 22px 15px; border-bottom: 1px solid var(--border); }
.modal-head h2 { margin: 0; font-size: 18px; letter-spacing: -.3px; }
.close { display: grid; place-items: center; width: 35px; height: 35px; border: 0; border-radius: 10px; color: var(--text-secondary); background: #f6f4f9; }
.close:hover { color: var(--text-main); background: var(--primary-extra-light); }
.modal-body { padding: 20px 22px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 9px; padding: 15px 22px 20px; }
.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
@media (max-width: 480px) { .modal-backdrop { padding: 10px; } .modal-head, .modal-body { padding-left: 17px; padding-right: 17px; } .modal-footer { padding-left: 17px; padding-right: 17px; } }
</style>
