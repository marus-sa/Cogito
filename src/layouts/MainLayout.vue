<script setup>
import { onMounted, ref } from 'vue'
import AppSidebar from '../components/AppSidebar.vue'
import AppHeader from '../components/AppHeader.vue'
import { useLessonsStore } from '../stores/lessons'
import { useHomeworkStore } from '../stores/homework'
import { useMessagesStore } from '../stores/messages'
const mobileOpen = ref(false)
const lessons = useLessonsStore()
const homework = useHomeworkStore()
const messages = useMessagesStore()

onMounted(async () => {
  try {
    await Promise.all([lessons.loadLessons(), homework.loadHomework(), messages.loadNotifications()])
  } catch {
    messages.showToast('Не получилось обновить данные с сервера', 'error')
  }
})
</script>
<template>
  <div class="app-shell">
    <AppSidebar :mobile-open="mobileOpen" @close="mobileOpen = false" />
    <div class="main-area"><AppHeader @menu="mobileOpen = true" /><main class="content"><RouterView /></main></div>
  </div>
</template>
<style scoped>
.main-area { min-height: 100vh; margin-left: 264px; }.content { padding: 30px 32px 45px; }@media(max-width:850px){.main-area{margin-left:0}.content{padding:24px 18px 36px}}@media(max-width:450px){.content{padding:18px 13px 30px}}
</style>
