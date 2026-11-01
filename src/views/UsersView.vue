<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import { roles } from '../config'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import BaseButton from '../components/BaseButton.vue'

const auth = useAuthStore()
const messages = useMessagesStore()
const users = ref([])
const relationships = ref({ parents: [], mentors: [] })
const selectedId = ref('')
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const form = reactive({ role: 'student', accountStatus: 'active' })
const link = reactive({ kind: 'parent_student', firstId: '', secondId: '' })
const statuses = { active: 'Активен', pending: 'Ожидает проверки', blocked: 'Заблокирован' }
const selected = computed(() => users.value.find((user) => user.id === Number(selectedId.value)))
const firstRole = computed(() => (link.kind === 'parent_student' ? 'parent' : 'mentor'))
const secondRole = computed(() => (link.kind === 'parent_student' ? 'student' : 'tutor'))
const activeUsers = (role) =>
  users.value.filter(
    (user) => user.role === role && user.accountStatus === 'active' && user.emailVerified,
  )
const nameOf = (id) => users.value.find((user) => user.id === id)?.name || 'Участник недоступен'

async function load() {
  error.value = ''
  try {
    const [accounts, links] = await Promise.all([api('/admin/users'), api('/admin/relationships')])
    users.value = accounts.items
    relationships.value = links
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    loading.value = false
  }
}
function selectUser() {
  if (!selected.value) return
  form.role = selected.value.role
  form.accountStatus = selected.value.accountStatus
}
function resetLink() {
  link.firstId = ''
  link.secondId = ''
}
async function saveUser() {
  if (!selected.value || saving.value) return
  if (
    form.role !== selected.value.role &&
    !window.confirm(
      `Изменить роль ${selected.value.name} на «${roles[form.role].label}»? Все его сессии завершатся, а прежние связи пользователей будут сняты.`,
    )
  )
    return
  saving.value = true
  try {
    await api(`/admin/users/${selected.value.id}`, { method: 'PATCH', body: { ...form } })
    await load()
    selectUser()
    messages.showToast('Аккаунт обновлён')
  } catch (requestError) {
    messages.showToast(requestError.message, 'error')
  } finally {
    saving.value = false
  }
}
async function saveLink(kind, firstId, secondId, method = 'POST') {
  if (saving.value) return
  saving.value = true
  try {
    await api('/admin/relationships', {
      method,
      body: { kind, firstId: Number(firstId), secondId: Number(secondId) },
    })
    await load()
    messages.showToast(method === 'POST' ? 'Связь сохранена' : 'Связь снята')
  } catch (requestError) {
    messages.showToast(requestError.message, 'error')
  } finally {
    saving.value = false
  }
}
onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-heading">
      <div>
        <h1>Участники</h1>
        <p>Роли, доступ и связи между аккаунтами.</p>
      </div>
    </div>
    <p v-if="loading">Загружаем участников…</p>
    <p v-else-if="error" role="alert">
      {{ error }}
      <button @click="load">Повторить</button>
    </p>
    <template v-else>
      <section class="card panel">
        <h2>Доступ к аккаунту</h2>
        <p>
          Для наставника или второго администратора сначала создайте обычный аккаунт и подтвердите
          почту. Затем назначьте ему нужную роль здесь. Пароль остаётся у владельца аккаунта.
        </p>
        <form class="account-form" @submit.prevent="saveUser">
          <label>
            Участник
            <select v-model="selectedId" required @change="selectUser">
              <option value="" disabled>Выберите аккаунт</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.name }} · {{ user.email }} · {{ roles[user.role]?.label }}
              </option>
            </select>
          </label>
          <template v-if="selected">
            <p>{{ selected.emailVerified ? 'Почта подтверждена' : 'Почта ещё не подтверждена' }}</p>
            <label>
              Роль
              <select v-model="form.role" :disabled="selected.id === auth.profile?.id">
                <option v-for="(role, key) in roles" :key="key" :value="key">
                  {{ role.label }}
                </option>
              </select>
            </label>
            <label>
              Статус
              <select v-model="form.accountStatus" :disabled="selected.id === auth.profile?.id">
                <option v-for="(label, key) in statuses" :key="key" :value="key">
                  {{ label }}
                </option>
              </select>
            </label>
            <p>
              При блокировке или смене роли все сессии участника завершаются. Разблокировка не
              восстанавливает старые сессии — нужен новый вход.
            </p>
            <BaseButton type="submit" :loading="saving" :disabled="selected.id === auth.profile?.id">
              Сохранить доступ
            </BaseButton>
          </template>
        </form>
      </section>
      <section class="card panel">
        <h2>Связи участников</h2>
        <p>
          Связывайте родителя с ребёнком только после проверки их отношений. Имя ребёнка в профиле
          само по себе не даёт доступа к его данным.
        </p>
        <form
          class="account-form"
          @submit.prevent="saveLink(link.kind, link.firstId, link.secondId)"
        >
          <label>
            Тип связи
            <select v-model="link.kind" @change="resetLink">
              <option value="parent_student">Родитель — ученик</option>
              <option value="mentor_tutor">Наставник — репетитор</option>
            </select>
          </label>
          <label>
            {{ roles[firstRole].label }}
            <select v-model="link.firstId" required>
              <option value="" disabled>Выберите участника</option>
              <option v-for="user in activeUsers(firstRole)" :key="user.id" :value="user.id">
                {{ user.name }} · {{ user.email }}
              </option>
            </select>
          </label>
          <label>
            {{ roles[secondRole].label }}
            <select v-model="link.secondId" required>
              <option value="" disabled>Выберите участника</option>
              <option v-for="user in activeUsers(secondRole)" :key="user.id" :value="user.id">
                {{ user.name }} · {{ user.email }}
              </option>
            </select>
          </label>
          <BaseButton type="submit" :loading="saving">Добавить связь</BaseButton>
        </form>
        <h3>Родители и ученики</h3>
        <p v-if="!relationships.parents.length">Связей пока нет.</p>
        <div
          v-for="item in relationships.parents"
          :key="`${item.parent_id}-${item.student_id}`"
          class="link-row"
        >
          <span>{{ nameOf(item.parent_id) }} → {{ nameOf(item.student_id) }}</span>
          <BaseButton
            size="sm"
            variant="outline"
            :disabled="saving"
            @click="saveLink('parent_student', item.parent_id, item.student_id, 'DELETE')"
          >
            Снять связь
          </BaseButton>
        </div>
        <h3>Наставники и репетиторы</h3>
        <p v-if="!relationships.mentors.length">Связей пока нет.</p>
        <div
          v-for="item in relationships.mentors"
          :key="`${item.mentor_id}-${item.tutor_id}`"
          class="link-row"
        >
          <span>{{ nameOf(item.mentor_id) }} → {{ nameOf(item.tutor_id) }}</span>
          <BaseButton
            size="sm"
            variant="outline"
            :disabled="saving"
            @click="saveLink('mentor_tutor', item.mentor_id, item.tutor_id, 'DELETE')"
          >
            Снять связь
          </BaseButton>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.panel {
  margin-top: 20px;
}
p {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}
.account-form {
  display: grid;
  gap: 16px;
  margin: 20px 0;
  max-width: 680px;
}
label {
  display: grid;
  gap: 7px;
  font-size: 13px;
  font-weight: 700;
}
select {
  width: 100%;
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: white;
  color: var(--text-main);
}
.account-form .base-button {
  justify-self: start;
}
.link-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid var(--border);
  padding: 12px 0;
  font-size: 13px;
}
@media (max-width: 600px) {
  .link-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
