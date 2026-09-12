import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/styles/main.css'
import { useAuthStore } from './stores/auth'

const pinia = createPinia()
const app = createApp(App)
const auth = useAuthStore(pinia)

// Сначала проверяем сохранённый вход. Тогда после обновления страницы
// пользователь не увидит короткий переход на экран авторизации.
auth.restore().finally(() => {
  app.use(pinia).use(router).mount('#app')
})
