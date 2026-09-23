<script setup>
import { onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, ShieldCheck } from 'lucide-vue-next'
import { api } from '../api'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const form = reactive({ firstName: '', lastName: '', email: '', password: '', confirm: '' })
const available = ref(false)
const loading = ref(true)
const submitting = ref(false)
const error = ref('')

onMounted(async () => {
  try {
    const result = await api('/setup/local-admin')
    available.value = result.available
  } catch {
    available.value = false
  } finally {
    loading.value = false
  }
})

async function createAdmin() {
  error.value = ''
  if (!form.firstName || !form.lastName || !/^\S+@\S+\.\S+$/.test(form.email)) {
    error.value = 'Укажите имя, фамилию и корректную почту.'
    return
  }
  if (form.password.length < 12) {
    error.value = 'Придумайте пароль длиной не менее 12 символов.'
    return
  }
  if (form.password !== form.confirm) {
    error.value = 'Пароли не совпадают.'
    return
  }

  submitting.value = true
  try {
    const result = await api('/setup/local-admin', { method: 'POST', body: JSON.stringify(form) })
    auth.setLogin(result.user)
    router.push('/dashboard')
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="setup-page">
    <header><RouterLink to="/login" class="back"><ArrowLeft :size="17" /> К входу</RouterLink><span class="brand">✦ <b>Cogito</b></span></header>
    <main class="setup-card">
      <div class="icon"><ShieldCheck :size="29" /></div>
      <template v-if="loading"><h1>Проверяем настройку…</h1></template>
      <template v-else-if="available"><span class="eyebrow">Только для этого компьютера</span><h1>Создать первого администратора</h1><p>Форма доступна, пока на этом локальном запуске нет администратора. Если вы уже зарегистрировались с этой почтой, этот аккаунт станет администраторским. Пароль останется только в приложении.</p><form class="form-grid" @submit.prevent="createAdmin"><div class="field"><label>Имя</label><input v-model.trim="form.firstName" autocomplete="given-name" /></div><div class="field"><label>Фамилия</label><input v-model.trim="form.lastName" autocomplete="family-name" /></div><div class="field full"><label>Электронная почта</label><input v-model.trim="form.email" type="email" autocomplete="email" placeholder="name@example.ru" /></div><div class="field"><label>Пароль</label><input v-model="form.password" type="password" autocomplete="new-password" placeholder="Минимум 12 символов" /></div><div class="field"><label>Повторите пароль</label><input v-model="form.confirm" type="password" autocomplete="new-password" /></div><p v-if="error" class="error full">{{ error }}</p><button class="primary-action full" :disabled="submitting">{{ submitting ? 'Создаём…' : 'Создать админ-аккаунт' }} <ArrowRight :size="16" /></button></form></template>
      <template v-else><h1>Администратор уже настроен</h1><p>Войдите с почтой и паролем администратора на странице входа.</p><RouterLink class="primary-action" to="/login">Ко входу <ArrowRight :size="16" /></RouterLink></template>
    </main>
  </div>
</template>

<style scoped>
.setup-page{min-height:100vh;padding:24px;background:linear-gradient(135deg,#f8f5fc,#f1ecfb)}header{display:flex;align-items:center;justify-content:space-between;max-width:680px;margin:0 auto 24px}.back{display:inline-flex;align-items:center;gap:6px;color:var(--primary-dark);font-size:12px;font-weight:800}.brand{color:var(--primary);font-size:17px}.brand b{color:var(--text-main)}.setup-card{width:min(100%,620px);margin:8vh auto;padding:34px 42px;background:#fff;border:1px solid var(--border);border-radius:24px;box-shadow:var(--shadow);text-align:center}.icon{display:grid;place-items:center;width:62px;height:62px;margin:0 auto 17px;color:var(--primary-dark);background:var(--primary-extra-light);border-radius:20px}.eyebrow{display:inline-block;padding:5px 9px;color:var(--primary-dark);background:var(--primary-extra-light);border-radius:100px;font-size:10px;font-weight:800}.setup-card h1{margin:11px 0 8px;font-size:26px;letter-spacing:-.7px}.setup-card>p{max-width:450px;margin:0 auto;color:var(--text-secondary);font-size:12px;line-height:1.6}.form-grid{margin-top:25px;text-align:left}.field label{display:block;margin-bottom:6px;color:var(--text-secondary);font-size:10px;font-weight:800}.field input{width:100%;min-height:42px;padding:0 11px;border:1px solid var(--border);border-radius:10px;outline:0;font:inherit;font-size:12px}.field input:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-extra-light)}.error{margin:3px 0 0;color:#ae5b5b;font-size:11px;text-align:center}.primary-action{display:inline-flex;align-items:center;justify-content:center;gap:7px;min-height:42px;margin-top:22px;padding:0 15px;border:0;border-radius:11px;color:#fff;background:var(--primary);font-size:12px;font-weight:800}.form-grid .primary-action{width:100%;margin-top:6px}.primary-action:disabled{opacity:.7}@media(max-width:600px){.setup-page{padding:15px}.setup-card{margin:5vh auto;padding:28px 19px}.setup-card h1{font-size:23px}}
</style>
