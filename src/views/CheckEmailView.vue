<script setup>
import { ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { MailCheck } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()
const email = ref(typeof route.query.email === 'string' ? route.query.email : '')
const sending = ref(false)
const result = ref('')
const error = ref('')

async function resend() {
  if (!/^\S+@\S+\.\S+$/.test(email.value)) {
    error.value = 'Введите корректный адрес электронной почты.'
    return
  }
  sending.value = true
  error.value = ''
  result.value = ''
  try {
    const response = await auth.resendEmailVerification(email.value)
    result.value = response.deliveryAvailable
      ? 'Если этот адрес ожидает подтверждения, новая ссылка отправлена.'
      : 'Почтовый сервис пока не подключён. Попробуйте немного позже.'
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <main class="check-page">
    <section class="check-card">
      <MailCheck :size="38" />
      <span class="eyebrow">Подтверждение регистрации</span>
      <h1>Отправить ссылку ещё раз</h1>
      <p>
        Введите почту, указанную при регистрации. Из соображений безопасности мы не сообщим, есть ли
        такой аккаунт.
      </p>
      <form @submit.prevent="resend">
        <label>
          Электронная почта
          <input
            v-model.trim="email"
            type="email"
            autocomplete="email"
            placeholder="name@example.ru"
          />
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="result" class="result">{{ result }}</p>
        <button class="primary-action" :disabled="sending">
          {{ sending ? 'Отправляем…' : 'Отправить ссылку' }}
        </button>
      </form>
      <RouterLink class="back-link" to="/login">Вернуться ко входу</RouterLink>
    </section>
  </main>
</template>

<style scoped>
.check-page {
  display: grid;
  min-height: 100vh;
  padding: 24px;
  background: linear-gradient(135deg, #f8f5fc, #f1ecfb);
  place-items: center;
}
.check-card {
  width: min(100%, 480px);
  padding: 42px 34px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 24px;
  box-shadow: var(--shadow);
  text-align: center;
}
.check-card > svg {
  margin-bottom: 17px;
  color: var(--primary);
}
.eyebrow {
  display: inline-block;
  padding: 5px 9px;
  color: var(--primary-dark);
  background: var(--primary-extra-light);
  border-radius: 100px;
  font-size: 10px;
  font-weight: 800;
}
.check-card h1 {
  margin: 12px 0 9px;
  font-size: 27px;
  letter-spacing: -0.8px;
}
.check-card > p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}
.check-card form {
  margin-top: 24px;
  text-align: left;
}
.check-card label {
  display: grid;
  gap: 7px;
  color: #61586d;
  font-size: 11px;
  font-weight: 800;
}
.check-card input {
  width: 100%;
  min-height: 43px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 11px;
  color: var(--text-main);
  font: inherit;
  background: #fff;
}
.check-card input:focus {
  outline: 2px solid rgba(120, 87, 190, 0.18);
  border-color: var(--primary);
}
.primary-action {
  width: 100%;
  min-height: 43px;
  margin-top: 16px;
  border: 0;
  border-radius: 12px;
  color: #fff;
  background: var(--primary);
  font-size: 12px;
  font-weight: 800;
}
.primary-action:hover:not(:disabled) {
  background: var(--primary-dark);
}
.primary-action:disabled {
  opacity: 0.65;
}
.error,
.result {
  margin: 10px 0 0;
  font-size: 11px;
  line-height: 1.5;
}
.error {
  color: #ad5d5d;
}
.result {
  color: #4f896a;
}
.back-link {
  display: inline-block;
  margin-top: 17px;
  color: var(--primary-dark);
  font-size: 11px;
  font-weight: 800;
}
@media (max-width: 520px) {
  .check-page {
    padding: 15px;
  }
  .check-card {
    padding: 34px 22px;
  }
  .check-card h1 {
    font-size: 24px;
  }
}
</style>
