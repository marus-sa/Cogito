<script setup>
import { computed, reactive, ref } from 'vue'
import { CalendarDays, ChevronLeft, ChevronRight, Clock3, ExternalLink, MapPin, Plus, RotateCcw, XCircle } from 'lucide-vue-next'
import { useLessonsStore } from '../stores/lessons'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import BaseButton from '../components/BaseButton.vue'
import BaseModal from '../components/BaseModal.vue'

const lessons = useLessonsStore()
const auth = useAuthStore()
const messages = useMessagesStore()
const mode = ref('Неделя')
const modalOpen = ref(false)
const newLesson = reactive({ student: 'Анна Смирнова', tutor: 'Мария Иванова', subject: 'Математика', date: '5 августа', time: '16:00–17:00', duration: '60 мин', link: 'https://telemost.yandex.ru', topic: 'Новое занятие', comment: '' })
const canCreate = computed(() => ['tutor', 'mentor', 'admin'].includes(auth.roleKey))
const statusClass = (status) => ({ 'Проведено': 'success', 'Отменено': 'danger', 'Перенесено': 'warning' }[status] || '')
async function createLesson() {
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
    <div class="page-heading"><div><h1>Расписание</h1><p>Планируйте занятия и оставайтесь в курсе всех встреч.</p></div><BaseButton v-if="canCreate" @click="modalOpen = true"><Plus :size="17" /> Создать занятие</BaseButton></div>
    <section class="schedule card"><div class="schedule-head"><div class="mode-tabs"><button v-for="item in ['День','Неделя','Месяц']" :key="item" :class="{ active: mode === item }" @click="mode = item">{{ item }}</button></div><div class="calendar-nav"><button aria-label="Предыдущий период"><ChevronLeft :size="17" /></button><b>{{ mode === 'День' ? '1 августа 2026' : mode === 'Неделя' ? '27 июля — 2 августа 2026' : 'Август 2026' }}</b><button aria-label="Следующий период"><ChevronRight :size="17" /></button></div></div>
      <div class="week-wrap"><div class="week-grid"><div class="time-col"><span></span><span v-for="time in ['15:00','16:00','17:00','18:00','19:00']" :key="time">{{ time }}</span></div><div v-for="day in [{d:'Пн',n:'27'},{d:'Вт',n:'28'},{d:'Ср',n:'29'},{d:'Чт',n:'30'},{d:'Пт',n:'31'},{d:'Сб',n:'1'},{d:'Вс',n:'2'}]" :key="day.n" class="day-col" :class="{ today: day.n === '1' }"><header><span>{{ day.d }}</span><b>{{ day.n }}</b></header><div class="day-body"><span v-for="i in 5" :key="i" class="line"></span><article v-if="day.n === '1'" class="calendar-item today-item"><b>Математика</b><small>18:00 · Анна</small></article><article v-if="day.n === '2'" class="calendar-item secondary-item"><b>Информатика</b><small>16:30 · Данил</small></article></div></div></div></div>
    </section>
    <section class="card panel lesson-list"><div class="section-title"><h2>{{ mode === 'День' ? 'Занятия сегодня' : 'Ближайшие занятия' }}</h2><span class="muted tiny">{{ lessons.lessons.length }} в списке</span></div><article v-for="item in lessons.lessons" :key="item.id" class="lesson-card"><div class="lesson-date"><CalendarDays :size="18" /><span>{{ item.date }}</span></div><div class="lesson-content"><span :class="['tag', statusClass(item.status)]">{{ item.status }}</span><h3>{{ item.subject }} <small>· {{ item.topic }}</small></h3><p><b>{{ item.student }}</b> · репетитор {{ item.tutor }}</p><div><span><Clock3 :size="13" /> {{ item.time }} · {{ item.duration }}</span><a v-if="item.link && item.status === 'Запланировано'" :href="item.link" target="_blank"><ExternalLink :size="13" /> Онлайн-занятие</a></div></div><div v-if="canCreate && item.status === 'Запланировано'" class="lesson-controls"><button title="Перенести" @click="moveLesson(item)"><RotateCcw :size="16" /></button><button title="Отменить" @click="cancelLesson(item)"><XCircle :size="16" /></button><a v-if="item.link" :href="item.link" target="_blank" title="Открыть занятие"><ExternalLink :size="16" /></a></div></article></section>
    <BaseModal v-model="modalOpen" title="Новое занятие" wide><div class="form-grid"><div class="field"><label>Ученик</label><select v-model="newLesson.student"><option>Анна Смирнова</option><option>Данил Мельников</option><option>Полина Кравцова</option></select></div><div class="field"><label>Репетитор</label><input v-model="newLesson.tutor" /></div><div class="field"><label>Предмет</label><input v-model="newLesson.subject" /></div><div class="field"><label>Дата</label><input v-model="newLesson.date" /></div><div class="field"><label>Время</label><input v-model="newLesson.time" /></div><div class="field"><label>Длительность</label><select v-model="newLesson.duration"><option>45 мин</option><option>60 мин</option><option>90 мин</option></select></div><div class="field full"><label>Ссылка на онлайн-занятие</label><input v-model="newLesson.link" type="url" /></div><div class="field full"><label>Тема и комментарий</label><textarea v-model="newLesson.topic" placeholder="Например, линейные уравнения" /></div></div><template #footer><BaseButton variant="outline" @click="modalOpen = false">Отмена</BaseButton><BaseButton @click="createLesson">Создать занятие</BaseButton></template></BaseModal>
  </div>
</template>
<style scoped>
.schedule{overflow:hidden}.schedule-head{display:flex;align-items:center;justify-content:space-between;gap:15px;padding:17px 21px;border-bottom:1px solid var(--border)}.mode-tabs{display:flex;padding:3px;background:#f4f1f8;border-radius:10px}.mode-tabs button{min-height:30px;padding:0 12px;border:0;border-radius:8px;color:var(--text-secondary);background:transparent;font-size:11px;font-weight:800}.mode-tabs button.active{color:var(--primary-dark);background:#fff;box-shadow:0 2px 5px rgba(51,35,77,.08)}.calendar-nav{display:flex;align-items:center;gap:11px}.calendar-nav button{display:grid;place-items:center;width:29px;height:29px;border:0;border-radius:8px;color:var(--text-secondary);background:transparent}.calendar-nav button:hover{background:var(--primary-extra-light)}.calendar-nav b{font-size:11px}.week-wrap{overflow-x:auto}.week-grid{display:grid;grid-template-columns:56px repeat(7,minmax(104px,1fr));min-width:785px;padding:0 13px 16px}.time-col,.day-col{display:grid;grid-template-rows:49px repeat(5,55px)}.time-col>span{padding:7px 3px;color:#9b93a5;font-size:9px}.day-col{border-left:1px solid #eeeaf3}.day-col header{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;color:var(--text-secondary);font-size:9px}.day-col header b{display:grid;place-items:center;width:23px;height:23px;border-radius:50%;font-size:11px}.day-col.today header{color:var(--primary-dark)}.day-col.today header b{color:#fff;background:var(--primary)}.day-body{position:relative;grid-row:2/-1}.line{display:block;height:55px;border-top:1px solid #f1eef5}.calendar-item{position:absolute;z-index:1;left:6px;right:5px;display:block;min-height:43px;padding:7px;border-radius:7px;font-size:9px}.calendar-item b,.calendar-item small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.calendar-item b{font-size:9px}.calendar-item small{margin-top:2px}.today-item{top:165px;color:#584179;background:#e9dffd;border-left:3px solid var(--primary)}.secondary-item{top:80px;color:#40657c;background:#e7f1f7;border-left:3px solid #83b3cd}.lesson-list{margin-top:20px}.lesson-card{display:flex;align-items:center;gap:18px;padding:17px 3px;border-top:1px solid var(--border)}.lesson-date{display:grid;justify-items:center;gap:4px;width:70px;color:var(--primary-dark);font-size:9px;font-weight:800}.lesson-content{min-width:0;flex:1}.lesson-content h3{margin:5px 0 3px;font-size:13px}.lesson-content h3 small{color:var(--text-secondary);font-weight:600}.lesson-content p{margin:0;color:var(--text-secondary);font-size:10px}.lesson-content>div{display:flex;gap:14px;margin-top:7px;color:var(--text-secondary);font-size:10px}.lesson-content>div span,.lesson-content>div a{display:flex;align-items:center;gap:4px}.lesson-content>div a{color:var(--primary-dark);font-weight:800}.lesson-controls{display:flex;gap:6px}.lesson-controls button,.lesson-controls a{display:grid;place-items:center;width:32px;height:32px;border:1px solid var(--border);border-radius:9px;color:var(--text-secondary);background:#fff}.lesson-controls button:hover,.lesson-controls a:hover{color:var(--primary-dark);background:var(--primary-extra-light)}.lesson-controls button:last-child:hover{color:#b15d5d;background:#fff5f5}@media(max-width:640px){.schedule-head{align-items:flex-start;flex-direction:column;padding:14px}.calendar-nav b{font-size:10px}.lesson-card{align-items:flex-start;gap:10px}.lesson-date{width:43px}.lesson-content>div{flex-wrap:wrap}.lesson-controls{flex-direction:column}.lesson-content h3{font-size:12px}}
</style>
