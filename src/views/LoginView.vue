<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowRight, BookOpenCheck, Eye, EyeOff, HeartHandshake, ShieldCheck } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { roles } from '../data/mockData'
import { api } from '../api'

const router = useRouter()
const auth = useAuthStore()
const form = reactive({ email: '', password: '', role: 'student', remember: true })
const errors = reactive({ email: '', password: '' })
const showPassword = ref(false)
const isSubmitting = ref(false)
const localSetupAvailable = ref(false)
const adminResetAvailable = ref(false)
const roleOptions = Object.entries(roles)
const selectedRole = computed(() => roles[form.role])

onMounted(async () => {
  const [localSetup, adminReset] = await Promise.allSettled([
    api('/setup/local-admin'),
    api('/auth/admin-password-reset'),
  ])

  if (localSetup.status === 'fulfilled') localSetupAvailable.value = localSetup.value.available
  if (adminReset.status === 'fulfilled') adminResetAvailable.value = adminReset.value.available
})

function validate() {
  errors.email = !form.email ? 'Введите электронную почту' : !/^\S+@\S+\.\S+$/.test(form.email) ? 'Проверьте формат электронной почты' : ''
  errors.password = !form.password ? 'Введите пароль' : form.password.length < 6 ? 'Пароль должен содержать не менее 6 символов' : ''
  return !errors.email && !errors.password
}
async function login() {
  if (!validate()) return
  isSubmitting.value = true
  errors.email = ''

  try {
    await auth.login(form.email, form.password, form.role, form.remember)
    router.push('/dashboard')
  } catch (error) {
    errors.email = error.message
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <section class="welcome-panel">
      <div class="auth-brand"><span class="brand-mark"><i></i><i></i></span><span><b>Cogito</b><small>Платформа Light Hearts</small></span></div>
      <div class="welcome-copy"><span class="eyebrow"><HeartHandshake :size="15" /> Учимся вместе, растём вместе</span><h1>Всё важное для обучения — <em>в одном месте</em></h1><p>Расписание, цели, домашние задания и поддержка команды Light Hearts — бережно собраны для вас.</p></div>
      <div class="feature-list"><div><span><BookOpenCheck :size="19" /></span><p><b>Понятный учебный путь</b><small>Небольшие шаги к большой цели</small></p></div><div><span><ShieldCheck :size="19" /></span><p><b>Надёжная поддержка</b><small>Репетитор, родитель и наставник рядом</small></p></div></div>
      <footer>© 2026 Light Hearts · Образование с заботой</footer>
    </section>
    <main class="login-panel">
      <form class="login-card" novalidate @submit.prevent="login">
        <div><h2>С возвращением!</h2><p>Войдите, чтобы продолжить свой путь в Cogito.</p></div>
        <div class="demo-role"><label>Моя роль в проекте</label><div class="role-select"><button v-for="[key, role] in roleOptions" :key="key" type="button" :class="{ active: form.role === key }" @click="form.role = key">{{ role.label }}</button></div><small>Выберите роль, которая была указана при регистрации или приглашении.</small></div>
        <div class="field"><label for="email">Электронная почта</label><input id="email" v-model.trim="form.email" type="email" placeholder="name@example.ru" @blur="validate" /><span v-if="errors.email" class="error-text">{{ errors.email }}</span></div>
        <div class="field"><label for="password">Пароль</label><div class="password-field"><input id="password" v-model="form.password" :type="showPassword ? 'text' : 'password'" placeholder="Не менее 6 символов" @blur="validate" /><button type="button" :aria-label="showPassword ? 'Скрыть пароль' : 'Показать пароль'" @click="showPassword = !showPassword"><EyeOff v-if="showPassword" :size="17" /><Eye v-else :size="17" /></button></div><span v-if="errors.password" class="error-text">{{ errors.password }}</span></div>
        <div class="login-options"><label class="check"><input v-model="form.remember" type="checkbox" /><span></span>Запомнить меня</label><span class="forgot">Не получается войти? Напишите координатору.</span></div>
        <button class="submit" type="submit" :disabled="isSubmitting">{{ isSubmitting ? 'Входим…' : `Войти как ${selectedRole.label.toLowerCase()}` }}<ArrowRight v-if="!isSubmitting" :size="17" /></button>
        <p class="register-link">Впервые в Cogito? <RouterLink to="/register">Создать аккаунт</RouterLink></p><p v-if="localSetupAvailable" class="setup-link">Это ваш первый запуск? <RouterLink to="/setup-admin">Создать локального администратора</RouterLink></p><p v-if="adminResetAvailable" class="setup-link">Не удаётся войти администратором? <RouterLink to="/admin-reset">Сбросить доступ</RouterLink></p>
      </form>
    </main>
  </div>
</template>

<style scoped>
.auth-page { display: grid; grid-template-columns: minmax(420px, 1.05fr) minmax(450px, .95fr); min-height: 100vh; }.welcome-panel { position: relative; display: flex; flex-direction: column; min-height: 100vh; padding: 44px clamp(38px, 7vw, 104px); overflow: hidden; color: #fff; background: linear-gradient(140deg, #765bc0, #9c83d3); }.welcome-panel::after,.welcome-panel::before{position:absolute;content:'';border-radius:50%;background:rgba(255,255,255,.08)}.welcome-panel::before{width:430px;height:430px;right:-160px;bottom:-155px}.welcome-panel::after{width:180px;height:180px;top:115px;left:-110px}.auth-brand { position: relative; z-index: 1; display: flex; align-items: center; gap: 12px; }.auth-brand b { display: block; font-size: 24px; letter-spacing: -1px; }.auth-brand small { display: block; margin-top: -2px; color: #e6dcfb; font-size: 10px; font-weight: 700; }.brand-mark{position:relative;display:block;width:35px;height:31px}.brand-mark i{position:absolute;top:5px;width:19px;height:19px;border-radius:8px 9px 8px 2px;background:#fff;transform:rotate(45deg)}.brand-mark i:last-child{right:0;background:#f5cbd5;transform:rotate(45deg) scale(.73)}.welcome-copy { position: relative; z-index: 1; max-width: 510px; margin: auto 0; }.eyebrow { display: inline-flex; align-items: center; gap: 7px; padding: 8px 11px; color: #f7f2ff; background: rgba(255,255,255,.13); border-radius: 100px; font-size: 11px; font-weight: 800; }.welcome-copy h1 { margin: 22px 0 17px; font-size: clamp(35px, 4vw, 56px); line-height: 1.07; letter-spacing: -2.1px; }.welcome-copy h1 em { color: #f8dce4; font-style: normal; }.welcome-copy p { max-width: 460px; color: #eee9fb; font-size: 15px; line-height: 1.75; }.feature-list { position: relative; z-index: 1; display: flex; gap: 30px; margin: auto 0 40px; }.feature-list > div { display: flex; align-items: center; gap: 10px; }.feature-list span { display: grid; place-items: center; width: 37px; height: 37px; color: var(--primary-dark); background: rgba(255,255,255,.85); border-radius: 11px; }.feature-list p { margin: 0; }.feature-list b,.feature-list small { display: block; }.feature-list b { font-size: 11px; }.feature-list small { margin-top: 2px; color: #eae2f9; font-size: 9px; }.welcome-panel footer { position: relative; z-index: 1; color: #e4dbf5; font-size: 10px; }.login-panel { display: grid; place-items: center; padding: 35px; background: #fcfbfe; }.login-card { width: min(100%, 400px); display: grid; gap: 18px; }.login-card h2 { margin: 0; font-size: 27px; letter-spacing: -.9px; }.login-card > div:first-child p { margin: 6px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.55; }.demo-role { display: grid; gap: 8px; padding: 13px; border: 1px solid var(--border); border-radius: 15px; background: #fcfaff; }.demo-role > label { color: #51495f; font-size: 11px; font-weight: 800; }.role-select { display: flex; flex-wrap: wrap; gap: 5px; }.role-select button { min-height: 28px; padding: 0 8px; border: 1px solid transparent; border-radius: 8px; color: #72697f; background: #f3eff8; font-size: 10px; font-weight: 800; }.role-select button.active { color: var(--primary-dark); border-color: #cfbfef; background: #e8def9; }.demo-role small { color: var(--text-secondary); font-size: 9px; }.password-field { position: relative; }.password-field input { padding-right: 42px; }.password-field button { position: absolute; top: 5px; right: 5px; display: grid; place-items: center; width: 33px; height: 33px; border: 0; border-radius: 9px; color: var(--text-secondary); background: transparent; }.password-field button:hover { color: var(--primary-dark); background: var(--primary-extra-light); }.login-options { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: -3px; }.check { display: inline-flex; align-items: center; gap: 7px; color: var(--text-secondary); font-size: 11px; cursor: pointer; }.check input { position: absolute; opacity: 0; }.check span { display: inline-block; width: 15px; height: 15px; border: 1px solid #cfc7da; border-radius: 4px; background: #fff; }.check input:checked + span { border-color: var(--primary); background: var(--primary); box-shadow: inset 0 0 0 3px #fff; }.forgot { border: 0; color: var(--primary-dark); background: transparent; font-size: 11px; font-weight: 800; }.submit { display: inline-flex; align-items: center; justify-content: center; gap: 9px; min-height: 45px; border: 0; border-radius: 13px; color: #fff; background: var(--primary); box-shadow: 0 6px 13px rgba(98,70,168,.2); font-size: 13px; font-weight: 800; }.submit:hover:not(:disabled) { background: var(--primary-dark); }.submit:disabled { opacity: .7; }.register-link,.demo-note { margin: 0; text-align: center; }.register-link { color: var(--text-secondary); font-size: 12px; }.register-link a { color: var(--primary-dark); font-weight: 800; }.demo-note { color: #9a91a6; font-size: 10px; }
@media(max-width:850px){.auth-page{grid-template-columns:1fr}.welcome-panel{display:none}.login-panel{min-height:100vh;padding:28px 20px}}@media(max-width:390px){.login-panel{padding:24px 16px}.login-card{gap:15px}.login-card h2{font-size:24px}}
</style>
<style scoped>
.setup-link { margin: -10px 0 0; color: var(--text-secondary); font-size: 10px; text-align: center; }
.setup-link a { color: var(--primary-dark); font-weight: 800; }
</style>
