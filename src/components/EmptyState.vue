<script setup>
import { Inbox } from 'lucide-vue-next'
defineProps({ title: { type: String, default: 'Здесь пока пусто' }, text: { type: String, default: 'Новые данные появятся здесь совсем скоро.' } })
</script>
<template>
  <div class="empty-state">
    <span><Inbox :size="25" /></span>
    <strong>{{ title }}</strong>
    <p>{{ text }}</p>
    <slot />
  </div>
</template>
<style scoped>
.empty-state { padding: 38px 20px; text-align: center; color: var(--text-secondary); }
.empty-state > span { display: grid; place-items: center; width: 54px; height: 54px; margin: 0 auto 12px; color: var(--primary); background: var(--primary-extra-light); border-radius: 18px; }
.empty-state strong { display: block; color: var(--text-main); }
.empty-state p { max-width: 290px; margin: 6px auto 16px; font-size: 12px; line-height: 1.55; }
</style>
