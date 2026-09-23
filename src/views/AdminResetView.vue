<script setup>
import { onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowLeft, ArrowRight, KeyRound, ShieldCheck } from 'lucide-vue-next'
import { api } from '../api'

const form = reactive({ email: '', token: '', password: '', confirm: '' })
const available = ref(false)
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const success = ref(false)

onMounted(async () => {
  try {
    const result = await api('/auth/admin-password-reset')
    available.value = result.available === true
  } catch {
    available.value = false
  } finally {
    loading.value = false
  }
})

function validate() {
  if (!/^\S+@\S+\.\S+$/.test(form.email)) {
    error.value = 'Укажите корректную электронную почту.'
    return false
  }
  if (!form.token) {
    error.value = 'Введите токен сброса.'
    return false
  }
  if (form.password.length < 12) {
    error.value = 'Новый пароль должен содержать не менее 12 символов.'
    return false
  }
  if (form.password !== form.confirm) {
    error.value = 'Пароли не совпадают.'
    return false
  }
  return true
}

async function resetAdmin() {
  error.value = ''
  if (!validate()) return

  submitting.value = true
  try {
    await api('/auth/admin-password-reset', {
      method: 'POST',
      body: JSON.stringify({
        email: form.email,
        token: form.token,
        newPassword: form.password,
      }),
    })

    form.email = ''
    form.token = ''
    form.password = ''
    form.confirm = ''
    success.value = true
  } catch (requestError) {
    error.value = requestError.message || 'Не удалось обновить доступ. Проверьте данные и попробуйте ещё раз.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="reset-page">
    <header>
      <RouterLink to="/login" class="back"><ArrowLeft :size="17" /> К входу</RouterLink>
      <span class="brand">✦ <b>Cogito</b></span>
    </header>

    <main class="reset-card">
      <div class="icon"><KeyRound :size="28" /></div>
      <template v-if="loading">
        <h1>Проверяем доступность сброса…</h1>
      </template>
      <template v-else-if="success">
        <div class="success-icon"><ShieldCheck :size="29" /></div>
        <h1>Пароль обновлён</h1>
        <p>Теперь войдите в Cogito с указанной почтой и новым паролем.</p>
        <RouterLink class="primary-action" to="/login">Перейти ко входу <ArrowRight :size="16" /></RouterLink>
      </template>
      <template v-else-if="available">
        <span class="eyebrow"><ShieldCheck :size="13" /> Защищённый сброс</span>
        <h1>Обновить доступ администратора</h1>
        <p>Укажите почту, с которой будете входить как администратор, токен сброса и новый пароль. Токен скрыт в поле ввода.</p>

        <form class="form-grid" novalidate @submit.prevent="resetAdmin">
          <div class="field full">
            <label for="reset-email">Почта для входа администратора</label>
            <input id="reset-email" v-model.trim="form.email" type="email" autocomplete="email" placeholder="name@example.ru" />
          </div>
          <div class="field full">
            <label for="reset-token">Токен сброса</label>
            <input id="reset-token" v-model="form.token" type="password" autocomplete="off" placeholder="Введите токен" />
          </div>
          <div class="field">
            <label for="reset-password">Новый пароль</label>
            <input id="reset-password" v-model="form.password" type="password" autocomplete="new-password" placeholder="Не менее 12 символов" />
          </div>
          <div class="field">
            <label for="reset-confirm">Повторите пароль</label>
            <input id="reset-confirm" v-model="form.confirm" type="password" autocomplete="new-password" placeholder="Повторите пароль" />
          </div>
          <p v-if="error" class="error full" role="alert">{{ error }}</p>
          <button class="primary-action full" type="submit" :disabled="submitting">
            {{ submitting ? 'Обновляем…' : 'Обновить пароль' }} <ArrowRight v-if="!submitting" :size="16" />
          </button>
        </form>
      </template>
      <template v-else>
        <h1>Сброс сейчас недоступен</h1>
        <p>Попросите владельца проекта создать новый токен сброса или войдите с действующими данными.</p>
        <RouterLink class="primary-action" to="/login">Ко входу <ArrowRight :size="16" /></RouterLink>
      </template>
    </main>
  </div>
</template>

<style scoped>
.reset-page { min-height: 100vh; padding: 24px; background: linear-gradient(135deg, #f8f5fc, #f1ecfb); }
header { display: flex; align-items: center; justify-content: space-between; max-width: 680px; margin: 0 auto 24px; }
.back { display: inline-flex; align-items: center; gap: 6px; color: var(--primary-dark); font-size: 12px; font-weight: 800; }
.brand { color: var(--primary); font-size: 17px; }
.brand b { color: var(--text-main); }
.reset-card { width: min(100%, 620px); margin: 8vh auto; padding: 34px 42px; background: #fff; border: 1px solid var(--border); border-radius: 24px; box-shadow: var(--shadow); text-align: center; }
.icon { display: grid; place-items: center; width: 62px; height: 62px; margin: 0 auto 17px; color: var(--primary-dark); background: var(--primary-extra-light); border-radius: 20px; }
.success-icon { display: grid; place-items: center; width: 62px; height: 62px; margin: 0 auto 17px; color: #478363; background: #e8f5ee; border-radius: 20px; }
.eyebrow { display: inline-flex; align-items: center; gap: 5px; padding: 5px 9px; color: var(--primary-dark); background: var(--primary-extra-light); border-radius: 100px; font-size: 10px; font-weight: 800; }
.reset-card h1 { margin: 11px 0 8px; font-size: 26px; letter-spacing: -.7px; }
.reset-card > p { max-width: 465px; margin: 0 auto; color: var(--text-secondary); font-size: 12px; line-height: 1.6; }
.form-grid { margin-top: 25px; text-align: left; }
.field label { display: block; margin-bottom: 6px; color: var(--text-secondary); font-size: 10px; font-weight: 800; }
.field input { width: 100%; min-height: 42px; padding: 0 11px; border: 1px solid var(--border); border-radius: 10px; outline: 0; font: inherit; font-size: 12px; }
.field input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-extra-light); }
.error { margin: 3px 0 0; color: #ae5b5b; font-size: 11px; text-align: center; }
.primary-action { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 42px; margin-top: 22px; padding: 0 15px; border: 0; border-radius: 11px; color: #fff; background: var(--primary); font-size: 12px; font-weight: 800; }
.form-grid .primary-action { width: 100%; margin-top: 6px; }
.primary-action:disabled { opacity: .7; cursor: wait; }
@media (max-width: 600px) { .reset-page { padding: 15px; } .reset-card { margin: 5vh auto; padding: 28px 19px; } .reset-card h1 { font-size: 23px; } }
</style>
