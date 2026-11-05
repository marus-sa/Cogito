<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import AppSidebar from './components/AppSidebar.vue'
import AppHeader from './components/AppHeader.vue'
import { useLessonsStore } from './stores/lessons'
import { useHomeworkStore } from './stores/homework'
import { useMessagesStore } from './stores/messages'
const mobileOpen = ref(false)
const lessons = useLessonsStore()
const homework = useHomeworkStore()
const messages = useMessagesStore()
const auth = useAuthStore()
const router = useRouter()

function sessionExpired() {
  auth.clearLogin()
  router.replace('/login')
}

async function checkSession() {
  if (document.visibilityState !== 'visible') return
  const previousUser = auth.profile?.id
  const previousRole = auth.roleKey
  if (!(await auth.restore())) return router.replace('/login')
  // Другой аккаунт мог войти в соседней вкладке этого же браузера.
  if (previousUser !== auth.profile?.id || previousRole !== auth.roleKey) {
    window.location.reload()
  }
}

onMounted(async () => {
  window.addEventListener('cogito:session-expired', sessionExpired)
  window.addEventListener('pageshow', checkSession)
  document.addEventListener('visibilitychange', checkSession)
  try {
    await Promise.all([
      lessons.loadLessons(),
      homework.loadHomework(),
    ])
  } catch {
    messages.showToast('Не получилось обновить данные с сервера', 'error')
  }
})
onUnmounted(() => {
  window.removeEventListener('cogito:session-expired', sessionExpired)
  window.removeEventListener('pageshow', checkSession)
  document.removeEventListener('visibilitychange', checkSession)
})
</script>
<template>
  <div class="app-shell">
    <AppSidebar :mobile-open="mobileOpen" @close="mobileOpen = false" />
    <div class="main-area">
      <AppHeader @menu="mobileOpen = true" />
      <main class="content"><RouterView /></main>
    </div>
  </div>
</template>
<style scoped>
.main-area {
  min-height: 100vh;
  margin-left: 264px;
}
.content {
  padding: 30px 32px 45px;
}
@media (max-width: 850px) {
  .main-area {
    margin-left: 0;
  }
  .content {
    padding: 24px 18px 36px;
  }
}
@media (max-width: 450px) {
  .content {
    padding: 18px 13px 30px;
  }
}
</style>
