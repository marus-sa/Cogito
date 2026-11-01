import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/main.css'
import { useAuthStore } from './stores/auth'

const pinia = createPinia()
const app = createApp(App)
const auth = useAuthStore(pinia)

async function start() {
  await auth.restore()
  app.use(pinia)
  app.use(router)
  app.mount('#app')
}

start()
