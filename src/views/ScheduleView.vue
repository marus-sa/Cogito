<script setup>
import { computed, reactive, ref } from 'vue'
import { CalendarDays, Clock3, ExternalLink, Plus, RotateCcw, XCircle } from 'lucide-vue-next'
import { useLessonsStore } from '../stores/lessons'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import BaseButton from '../components/BaseButton.vue'
import BaseModal from '../components/BaseModal.vue'

const lessons = useLessonsStore()
const auth = useAuthStore()
const messages = useMessagesStore()
const modalOpen = ref(false)
const newLesson = reactive({ student: '', tutor: '', subject: '', date: '', time: '', duration: '60 мин', link: '', topic: '' })
const canCreate = computed(() => ['tutor', 'mentor', 'admin'].includes(auth.roleKey))
const plannedCount = computed(() => lessons.lessons.filter((item) => item.status === 'Запланировано').length)
const lessonGroups = computed(() => {
  const groups = new Map()
  lessons.lessons.forEach((item) => {
    const date = item.date?.trim() || 'Дата не указана'
    if (!groups.has(date)) groups.set(date, [])
    groups.get(date).push(item)
  })
  return [...groups].map(([date, items]) => ({ date, items }))
})
const statusClass = (status) => ({ 'Проведено': 'success', 'Отменено': 'danger', 'Перенесено': 'warning' }[status] || '')

function resetNewLesson() {
  Object.assign(newLesson, { student: '', tutor: '', subject: '', date: '', time: '', duration: '60 мин', link: '', topic: '' })
}

function openCreateModal() {
  resetNewLesson()
  modalOpen.value = true
}

async function createLesson() {
  if (!newLesson.student.trim()) {
    messages.showToast('Укажите ученика из зарегистрированных пользователей', 'error')
    return
  }
  if (auth.roleKey !== 'tutor' && !newLesson.tutor.trim()) {
    messages.showToast('Укажите репетитора из зарегистрированных пользователей', 'error')
    return
  }
  if (!newLesson.subject.trim() || !newLesson.date || !newLesson.time.trim()) {
    messages.showToast('Заполните предмет, дату и время занятия', 'error')
    return
  }
  try {
    await lessons.addLesson(newLesson)
    modalOpen.value = false
    messages.showToast('Занятие добавлено в расписание')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}

async function cancelLesson(item) {
  try {
    await lessons.updateStatus(item.id, 'Отменено')
    messages.showToast('Занятие отменено', 'error')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}

async function moveLesson(item) {
  try {
    await lessons.updateStatus(item.id, 'Перенесено')
    messages.showToast('Занятие отмечено как перенесённое')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
</script>

<template>
  <div class="page">
    <div class="page-heading">
      <div><h1>Расписание</h1><p>Здесь отображаются только занятия, которые созданы в приложении.</p></div>
      <BaseButton v-if="canCreate" @click="openCreateModal"><Plus :size="17" /> Создать занятие</BaseButton>
    </div>

    <section class="schedule card">
      <div class="schedule-head">
        <div><h2>Календарь занятий</h2><p class="muted tiny">{{ plannedCount }} запланировано</p></div>
      </div>
      <div v-if="lessonGroups.length" class="calendar-groups">
        <section v-for="group in lessonGroups" :key="group.date" class="calendar-group">
          <h3>{{ group.date }}</h3>
          <div class="calendar-items">
            <article v-for="item in group.items" :key="item.id" :class="['calendar-item', statusClass(item.status)]">
              <span class="calendar-time">{{ item.time || 'Время не указано' }}</span>
              <div><b>{{ item.subject || 'Предмет не указан' }}</b><small>{{ item.student || 'Ученик не указан' }} · {{ item.tutor || 'Репетитор не указан' }}</small></div>
              <span :class="['tag', statusClass(item.status)]">{{ item.status }}</span>
            </article>
          </div>
        </section>
      </div>
      <div v-else class="empty-schedule"><CalendarDays :size="26" /><b>Занятий пока нет</b><p>После создания занятия оно появится здесь и в списке ниже.</p></div>
    </section>

    <section class="card panel lesson-list">
      <div class="section-title"><h2>Все занятия</h2><span class="muted tiny">{{ lessons.lessons.length }} в списке</span></div>
      <div v-if="lessons.lessons.length">
        <article v-for="item in lessons.lessons" :key="item.id" class="lesson-card">
          <div class="lesson-date"><CalendarDays :size="18" /><span>{{ item.date || 'Дата не указана' }}</span></div>
          <div class="lesson-content">
            <span :class="['tag', statusClass(item.status)]">{{ item.status }}</span>
            <h3>{{ item.subject || 'Предмет не указан' }} <small v-if="item.topic">· {{ item.topic }}</small></h3>
            <p><b>{{ item.student || 'Ученик не указан' }}</b> · репетитор {{ item.tutor || 'не указан' }}</p>
            <div><span><Clock3 :size="13" /> {{ item.time || 'Время не указано' }} · {{ item.duration || 'Длительность не указана' }}</span><a v-if="item.link && item.status === 'Запланировано'" :href="item.link" target="_blank" rel="noopener"><ExternalLink :size="13" /> Онлайн-занятие</a></div>
          </div>
          <div v-if="canCreate && item.status === 'Запланировано'" class="lesson-controls">
            <button title="Перенести" @click="moveLesson(item)"><RotateCcw :size="16" /></button>
            <button title="Отменить" @click="cancelLesson(item)"><XCircle :size="16" /></button>
            <a v-if="item.link" :href="item.link" target="_blank" rel="noopener" title="Открыть занятие"><ExternalLink :size="16" /></a>
          </div>
        </article>
      </div>
      <div v-else class="empty-compact">Создайте первое занятие, чтобы оно появилось в расписании.</div>
    </section>

    <BaseModal v-model="modalOpen" title="Новое занятие" wide>
      <div class="form-grid">
        <div class="field"><label>Ученик</label><input v-model.trim="newLesson.student" autocomplete="off" placeholder="Полное имя ученика" /></div>
        <div class="field"><label>Репетитор</label><input v-if="auth.roleKey === 'tutor'" :value="auth.user.name" disabled /><input v-else v-model.trim="newLesson.tutor" placeholder="Полное имя репетитора" /></div>
        <div class="field"><label>Предмет</label><input v-model.trim="newLesson.subject" placeholder="Название предмета" /></div>
        <div class="field"><label>Дата</label><input v-model="newLesson.date" type="date" /></div>
        <div class="field"><label>Время</label><input v-model.trim="newLesson.time" placeholder="Укажите время" /></div>
        <div class="field"><label>Длительность</label><select v-model="newLesson.duration"><option>45 мин</option><option>60 мин</option><option>90 мин</option></select></div>
        <div class="field full"><label>Ссылка на онлайн-занятие</label><input v-model.trim="newLesson.link" type="url" placeholder="https://" /></div>
        <div class="field full"><label>Тема занятия</label><textarea v-model.trim="newLesson.topic" placeholder="Коротко опишите тему" /></div>
      </div>
      <template #footer><BaseButton variant="outline" @click="modalOpen = false">Отмена</BaseButton><BaseButton @click="createLesson">Создать занятие</BaseButton></template>
    </BaseModal>
  </div>
</template>

<style scoped>
.schedule{overflow:hidden}.schedule-head{display:flex;align-items:center;justify-content:space-between;gap:15px;padding:17px 21px;border-bottom:1px solid var(--border)}.schedule-head h2{margin:0;font-size:14px}.schedule-head p{margin:4px 0 0}.calendar-groups{display:grid;gap:0;padding:4px 20px 18px}.calendar-group{padding:15px 0;border-bottom:1px solid var(--border)}.calendar-group:last-child{border-bottom:0}.calendar-group h3{margin:0 0 10px;color:var(--text-secondary);font-size:11px}.calendar-items{display:grid;gap:8px}.calendar-item{display:grid;grid-template-columns:110px minmax(0,1fr) auto;align-items:center;gap:12px;padding:11px 12px;border:1px solid #e3dcef;border-left:3px solid var(--primary);border-radius:10px;background:#fbf9ff}.calendar-item.success{border-left-color:#5d9f77;background:#f6fbf7}.calendar-item.warning{border-left-color:#bc8739;background:#fffbf4}.calendar-item.danger{border-left-color:#bd7070;background:#fff8f8}.calendar-time{color:var(--primary-dark);font-size:11px;font-weight:800}.calendar-item b,.calendar-item small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.calendar-item b{font-size:11px}.calendar-item small{margin-top:3px;color:var(--text-secondary);font-size:10px}.empty-schedule{display:grid;justify-items:center;gap:7px;padding:42px 20px;color:var(--text-secondary);text-align:center}.empty-schedule svg{color:var(--primary)}.empty-schedule b{color:var(--text-main);font-size:13px}.empty-schedule p{max-width:280px;margin:0;font-size:11px;line-height:1.5}.lesson-list{margin-top:20px}.lesson-card{display:flex;align-items:center;gap:18px;padding:17px 3px;border-top:1px solid var(--border)}.lesson-date{display:grid;justify-items:center;gap:4px;width:80px;color:var(--primary-dark);font-size:9px;font-weight:800;text-align:center}.lesson-content{min-width:0;flex:1}.lesson-content h3{margin:5px 0 3px;font-size:13px}.lesson-content h3 small{color:var(--text-secondary);font-weight:600}.lesson-content p{margin:0;color:var(--text-secondary);font-size:10px}.lesson-content>div{display:flex;gap:14px;margin-top:7px;color:var(--text-secondary);font-size:10px}.lesson-content>div span,.lesson-content>div a{display:flex;align-items:center;gap:4px}.lesson-content>div a{color:var(--primary-dark);font-weight:800}.lesson-controls{display:flex;gap:6px}.lesson-controls button,.lesson-controls a{display:grid;place-items:center;width:32px;height:32px;border:1px solid var(--border);border-radius:9px;color:var(--text-secondary);background:#fff}.lesson-controls button:hover,.lesson-controls a:hover{color:var(--primary-dark);background:var(--primary-extra-light)}.lesson-controls button:last-child:hover{color:#b15d5d;background:#fff5f5}.empty-compact{padding:25px 0 6px;color:var(--text-secondary);font-size:12px;text-align:center}@media(max-width:640px){.schedule-head{padding:14px}.calendar-groups{padding:4px 14px 14px}.calendar-item{grid-template-columns:1fr;gap:5px}.calendar-item>.tag{justify-self:start}.lesson-card{align-items:flex-start;gap:10px}.lesson-date{width:58px}.lesson-content>div{flex-wrap:wrap}.lesson-controls{flex-direction:column}.lesson-content h3{font-size:12px}}
</style>
