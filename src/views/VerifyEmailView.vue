<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { CheckCircle2, MailCheck, RefreshCw } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const status = ref('checking')
const error = ref('')
const waitingApproval = ref(false)
const accountActive = ref(false)

onMounted(async () => {
  const token = new URLSearchParams(window.location.hash.slice(1)).get('token')
  // Сразу скрываем токен из адресной строки: он не останется в истории браузера.
  window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
  if (!token) {
    status.value = 'error'
    error.value = 'В ссылке нет кода подтверждения. Запросите новое письмо.'
    return
  }
  try {
    const result = await auth.verifyEmail(token)
    waitingApproval.value = result.needsApproval
    accountActive.value = result.user.accountStatus === 'active'
    status.value = 'success'
  } catch (requestError) {
    status.value = 'error'
    error.value = requestError.message
  }
})

function continueToAccount() {
  router.push(accountActive.value ? '/dashboard' : '/login')
}
</script>

<template>
  <main class="verify-page">
    <section class="verify-card">
      <template v-if="status === 'checking'">
        <RefreshCw class="spin icon" :size="32" />
        <h1>Подтверждаем почту…</h1>
        <p>Проверяем ссылку и готовим ваш кабинет.</p>
      </template>
      <template v-else-if="status === 'success'">
        <CheckCircle2 class="icon success" :size="38" />
        <span class="eyebrow">Почта подтверждена</span>
        <h1>
          {{
            waitingApproval
              ? 'Заявка передана команде'
              : accountActive
                ? 'Добро пожаловать в Cogito!'
                : 'Почта подтверждена'
          }}
        </h1>
        <p v-if="waitingApproval">
          Команда Light Hearts проверит вашу заявку репетитора. Мы откроем вход после подтверждения.
        </p>
        <p v-else-if="accountActive">Адрес подтверждён, а вход в личный кабинет уже открыт.</p>
        <p v-else>Адрес подтверждён, но аккаунт недоступен. Обратитесь к координатору.</p>
        <button class="primary-action" @click="continueToAccount">
          {{ accountActive ? 'Открыть кабинет' : 'Перейти ко входу' }}
        </button>
      </template>
      <template v-else>
        <MailCheck class="icon warning" :size="38" />
        <span class="eyebrow">Нужна новая ссылка</span>
        <h1>Не получилось подтвердить почту</h1>
        <p>{{ error }}</p>
        <RouterLink class="primary-action" to="/check-email">Отправить новую ссылку</RouterLink>
        <RouterLink class="back-link" to="/login">Вернуться ко входу</RouterLink>
      </template>
    </section>
  </main>
</template>

<style scoped>
.verify-page {
  display: grid;
  min-height: 100vh;
  padding: 24px;
  background: linear-gradient(135deg, #f8f5fc, #f1ecfb);
  place-items: center;
}
.verify-card {
  width: min(100%, 480px);
  padding: 42px 34px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 24px;
  box-shadow: var(--shadow);
  text-align: center;
}
.icon {
  margin-bottom: 17px;
  color: var(--primary);
}
.icon.success {
  color: #4f906b;
}
.icon.warning {
  color: #af8035;
}
.spin {
  animation: spin 1s linear infinite;
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
.verify-card h1 {
  margin: 12px 0 9px;
  font-size: 27px;
  letter-spacing: -0.8px;
}
.verify-card p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}
.primary-action {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 43px;
  margin: 24px auto 0;
  padding: 0 15px;
  border: 0;
  border-radius: 12px;
  color: #fff;
  background: var(--primary);
  font-size: 12px;
  font-weight: 800;
}
.primary-action:hover {
  background: var(--primary-dark);
}
.back-link {
  display: inline-block;
  margin-top: 15px;
  color: var(--primary-dark);
  font-size: 11px;
  font-weight: 800;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 520px) {
  .verify-page {
    padding: 15px;
  }
  .verify-card {
    padding: 34px 22px;
  }
  .verify-card h1 {
    font-size: 24px;
  }
}
</style>
