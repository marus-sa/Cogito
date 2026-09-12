<script setup>
import { computed, reactive, ref } from 'vue'
import { CheckCircle2, Clock3, FileVideo, Image, Plus, Upload } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import { useLessonsStore } from '../stores/lessons'
import StatCard from '../components/StatCard.vue'
import BaseButton from '../components/BaseButton.vue'
import BaseModal from '../components/BaseModal.vue'

const auth = useAuthStore()
const messages = useMessagesStore()
const lessons = useLessonsStore()
const modalOpen = ref(false)
const report = reactive({ student: 'Анна Смирнова', date: '1 августа', start: '18:00', end: '19:00', duration: '60 мин', topic: 'Линейные уравнения', comment: '', video: '', startShot: '', endShot: '' })
const tutorMode = computed(() => auth.roleKey === 'tutor')
const entries = computed(() => lessons.lessons.filter((item) => item.status === 'Проведено'))
function pickFile(event, field) { report[field] = event.target.files?.[0]?.name || '' }
async function submit() {
  try {
    await lessons.addReview({
      tutor: auth.user.name,
      tutorInitials: auth.user.initials,
      student: report.student,
      date: report.date,
      duration: report.duration,
      topic: report.topic,
      video: report.video,
      shots: report.startShot && report.endShot,
    })
    modalOpen.value = false
    messages.showToast('Отчёт отправлен наставнику. Часы ожидают проверки.')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
</script>
<template>
  <div class="page"><div class="page-heading"><div><h1>{{ tutorMode ? 'Мои часы' : 'Волонтёрские часы' }}</h1><p>{{ tutorMode ? 'Учитывайте проведённые занятия и отслеживайте их проверку.' : 'Следите за подтверждёнными часами команды.' }}</p></div><BaseButton v-if="tutorMode" @click="modalOpen = true"><Plus :size="17" /> Занятие проведено</BaseButton></div>
    <section class="grid three-col"><StatCard label="За текущий месяц" :value="tutorMode ? '14,5 ч' : '427 ч'" icon="Clock3" /><StatCard label="Подтверждено" :value="tutorMode ? '12 ч' : '394 ч'" icon="CheckCircle2" tone="green" /><StatCard label="Ожидает проверки" :value="tutorMode ? '2,5 ч' : '33 ч'" icon="FileVideo" tone="orange" /></section>
    <section class="card panel hours-list"><div class="section-title"><h2>История занятий</h2><span class="muted tiny">Часы рассчитываются автоматически</span></div><div class="table-wrap"><table><thead><tr><th>Занятие</th><th>Дата и время</th><th>Длительность</th><th>Материалы</th><th>Статус</th></tr></thead><tbody><tr v-for="item in entries" :key="item.id"><td><b>{{ item.subject }}</b><small>{{ item.student }} · {{ item.topic }}</small></td><td>{{ item.date }}<small>{{ item.time }}</small></td><td><b>{{ item.duration }}</b></td><td><span class="materials"><FileVideo :size="14" :class="{ missing: !item.materials }" /> <Image :size="14" :class="{ missing: !item.materials }" /></span></td><td><span :class="['tag', item.materials ? 'success' : 'warning']">{{ item.materials ? 'Проверено' : 'Ожидает проверки' }}</span></td></tr></tbody></table></div></section>
    <BaseModal v-model="modalOpen" title="Отчёт о проведённом занятии" wide><p class="modal-copy">После отправки часы будут автоматически рассчитаны и направлены наставнику на проверку.</p><div class="form-grid"><div class="field"><label>Ученик</label><select v-model="report.student"><option>Анна Смирнова</option><option>Данил Мельников</option></select></div><div class="field"><label>Дата</label><input v-model="report.date" /></div><div class="field"><label>Время начала</label><input v-model="report.start" /></div><div class="field"><label>Время окончания</label><input v-model="report.end" /></div><div class="field"><label>Длительность</label><select v-model="report.duration"><option>45 мин</option><option>60 мин</option><option>90 мин</option></select></div><div class="field"><label>Тема занятия</label><input v-model="report.topic" /></div><div class="field full"><label>Комментарий</label><textarea v-model="report.comment" placeholder="Кратко опишите, как прошло занятие…" /></div></div><div class="uploads"><label><FileVideo :size="19" /><span><b>Видеозапись</b><small>{{ report.video || 'Выберите тестовый файл' }}</small></span><input type="file" @change="pickFile($event, 'video')" /></label><label><Image :size="19" /><span><b>Скриншот начала</b><small>{{ report.startShot || 'Выберите тестовый файл' }}</small></span><input type="file" @change="pickFile($event, 'startShot')" /></label><label><Image :size="19" /><span><b>Скриншот конца</b><small>{{ report.endShot || 'Выберите тестовый файл' }}</small></span><input type="file" @change="pickFile($event, 'endShot')" /></label></div><template #footer><BaseButton variant="outline" @click="modalOpen = false">Отмена</BaseButton><BaseButton @click="submit"><Upload :size="15" /> Отправить отчёт</BaseButton></template></BaseModal>
  </div>
</template>
<style scoped>
.hours-list{margin-top:19px}.hours-list td b,.hours-list td small{display:block}.hours-list td b{font-size:11px}.hours-list td small{margin-top:3px;color:var(--text-secondary);font-size:10px}.materials{display:flex;gap:7px;color:#5b9b74}.materials .missing{color:#c38b8b}.modal-copy{margin:0 0 15px;color:var(--text-secondary);font-size:11px;line-height:1.5}.uploads{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}.uploads label{display:flex;align-items:center;gap:8px;min-height:61px;padding:9px;border:1px dashed #cfc2e8;border-radius:12px;color:var(--primary-dark);background:#fbf9ff;cursor:pointer}.uploads input{display:none}.uploads b,.uploads small{display:block}.uploads b{font-size:10px}.uploads small{max-width:120px;margin-top:3px;overflow:hidden;color:var(--text-secondary);font-size:8px;text-overflow:ellipsis;white-space:nowrap}@media(max-width:600px){.uploads{grid-template-columns:1fr}.uploads small{max-width:230px}}
</style>
