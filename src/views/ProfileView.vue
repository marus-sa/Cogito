<script setup>
import { computed, reactive, ref } from 'vue'
import { Bell, Check, Clock3, Mail, Pencil, Save, UserRound } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import UserAvatar from '../components/UserAvatar.vue'
import BaseButton from '../components/BaseButton.vue'

const auth = useAuthStore()
const messages = useMessagesStore()
const editing = ref(false)
const parts = auth.user.name.split(' ')
const form = reactive({
  firstName: parts[0],
  lastName: parts.slice(1).join(' '),
  email: auth.user.email || '',
  grade: auth.user.grade || '',
  subjects: auth.user.subjects || '',
  time: auth.user.availableTime || '',
})
const notices = reactive([{ label: 'Напоминания о занятиях', on: true }, { label: 'Новые домашние задания', on: true }, { label: 'Результаты проверки', on: true }, { label: 'Новые сообщения', on: true }, { label: 'Уведомления по электронной почте', on: false }])
const details = computed(() => auth.roleKey === 'parent'
  ? [{ label: 'Ребёнок', value: auth.user.childName || 'Не указан' }, { label: 'Предмет', value: form.subjects || 'Не указан' }, { label: 'Удобное время', value: form.time || 'Не указано' }]
  : [{ label: 'Класс', value: form.grade || 'Не указан' }, { label: auth.roleKey === 'tutor' ? 'Предметы' : 'Предмет', value: form.subjects || 'Не указан' }, { label: 'Удобное время', value: form.time || 'Не указано' }])
async function save() {
  try {
    await auth.updateProfile({
      firstName: form.firstName,
      lastName: form.lastName,
      email: form.email,
      grade: form.grade,
      subjects: form.subjects,
      time: form.time,
    })
    editing.value = false
    messages.showToast('Изменения профиля сохранены')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
</script>
<template>
  <div class="page"><div class="page-heading"><div><h1>Профиль</h1><p>Ваши данные и настройки уведомлений.</p></div><BaseButton v-if="!editing" variant="outline" @click="editing = true"><Pencil :size="16" /> Редактировать</BaseButton><BaseButton v-else @click="save"><Save :size="16" /> Сохранить</BaseButton></div>
    <div class="profile-grid"><section class="card profile-summary"><div class="cover"></div><div class="person-block"><UserAvatar :initials="auth.user.initials" :color="auth.user.color" :size="78" /><button v-if="editing" class="avatar-edit" @click="messages.showToast('Фото можно будет загрузить после подключения сервера')"><Pencil :size="13" /></button><h2>{{ auth.user.name }}</h2><span class="tag">{{ auth.roleLabel }}</span><p>{{ auth.user.description }}</p></div><div class="profile-contact"><span><Mail :size="15" /> {{ form.email }}</span><span><Clock3 :size="15" /> {{ form.time }}</span></div></section><section class="card panel"><div class="section-title"><h2>Основные данные</h2><UserRound :size="18" class="accent" /></div><div v-if="editing" class="form-grid"><div class="field"><label>Имя</label><input v-model="form.firstName" /></div><div class="field"><label>Фамилия</label><input v-model="form.lastName" /></div><div class="field full"><label>Email</label><input v-model="form.email" type="email" /></div><div class="field"><label>Класс</label><input v-model="form.grade" /></div><div class="field"><label>Предметы</label><input v-model="form.subjects" /></div><div class="field full"><label>Удобное время</label><input v-model="form.time" /></div></div><div v-else class="details"><div v-for="detail in details" :key="detail.label"><span>{{ detail.label }}</span><b>{{ detail.value }}</b></div></div></section></div>
    <section class="card panel notice-settings"><div class="section-title"><div><h2>Настройки уведомлений</h2><p class="muted tiny">Выберите, о каких событиях нужно напоминать.</p></div><Bell :size="18" class="accent" /></div><label v-for="notice in notices" :key="notice.label" class="toggle-row"><span><b>{{ notice.label }}</b><small>{{ notice.on ? 'Уведомления включены' : 'Уведомления выключены' }}</small></span><input v-model="notice.on" type="checkbox" /><i></i></label></section>
  </div>
</template>
<style scoped>
.profile-grid{display:grid;grid-template-columns:minmax(270px,.8fr) minmax(360px,1.2fr);gap:19px}.profile-summary{overflow:hidden;text-align:center}.cover{height:85px;background:linear-gradient(135deg,#e2d7f7,#cbb9ef)}.person-block{position:relative;padding:0 22px 20px}.person-block :deep(.avatar){margin-top:-39px;box-shadow:0 0 0 5px #fff}.person-block h2{margin:11px 0 6px;font-size:18px}.person-block p{margin:10px 0 0;color:var(--text-secondary);font-size:10px}.avatar-edit{position:absolute;top:13px;left:calc(50% + 25px);display:grid;place-items:center;width:27px;height:27px;border:2px solid #fff;border-radius:50%;color:#fff;background:var(--primary)}.profile-contact{display:grid;gap:10px;padding:15px 21px;border-top:1px solid var(--border);text-align:left}.profile-contact span{display:flex;align-items:center;gap:7px;color:var(--text-secondary);font-size:10px}.accent{color:var(--primary)}.details{display:grid;gap:16px;padding-top:3px}.details>div{padding-bottom:12px;border-bottom:1px solid var(--border)}.details>div:last-child{padding-bottom:0;border-bottom:0}.details span,.details b{display:block}.details span{color:var(--text-secondary);font-size:10px}.details b{margin-top:4px;font-size:12px}.notice-settings{margin-top:19px;max-width:760px}.toggle-row{position:relative;display:flex;align-items:center;justify-content:space-between;padding:14px 0;border-top:1px solid var(--border);cursor:pointer}.toggle-row span b,.toggle-row span small{display:block}.toggle-row span b{font-size:11px}.toggle-row span small{margin-top:3px;color:var(--text-secondary);font-size:9px}.toggle-row input{position:absolute;opacity:0}.toggle-row i{width:35px;height:20px;border-radius:12px;background:#d7d1dc;transition:.2s}.toggle-row i::after{display:block;width:16px;height:16px;margin:2px;background:#fff;border-radius:50%;content:'';transition:.2s}.toggle-row input:checked+i{background:var(--primary)}.toggle-row input:checked+i::after{transform:translateX(15px)}@media(max-width:720px){.profile-grid{grid-template-columns:1fr}.profile-summary{max-width:none}.notice-settings{margin-top:19px}}
</style>
