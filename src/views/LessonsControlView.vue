<script setup>
import { computed, ref } from 'vue'
import { CheckCircle2, CircleAlert, FileVideo, Image, MessageSquareText, Search, XCircle } from 'lucide-vue-next'
import { useLessonsStore } from '../stores/lessons'
import { useMessagesStore } from '../stores/messages'
import BaseButton from '../components/BaseButton.vue'
import BaseModal from '../components/BaseModal.vue'
import UserAvatar from '../components/UserAvatar.vue'

const lessons = useLessonsStore()
const messages = useMessagesStore()
const status = ref('Все статусы')
const material = ref('Все материалы')
const selected = ref(null)
const modalOpen = ref(false)
const filtered = computed(() => lessons.reviewLessons.filter((item) => (status.value === 'Все статусы' || item.status === status.value) && (material.value === 'Все материалы' || (material.value === 'Есть материалы' ? item.video && item.shots : !item.video || !item.shots))))
const tagClass = (item) => item.status === 'Проверено' ? 'success' : item.status === 'Нужно исправить' || item.status === 'Отклонено' ? 'danger' : 'warning'
function open(item) { selected.value = item; modalOpen.value = true }
async function verify(result) {
  try {
    await lessons.verifyLesson(selected.value.id, result)
    modalOpen.value = false
    const text = result === 'Проверено' ? 'Занятие проверено, часы подтверждены' : 'Отчёт возвращён на доработку'
    messages.showToast(text, result === 'Проверено' ? 'success' : 'error')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
</script>
<template>
  <div class="page"><div class="page-heading"><div><h1>Контроль занятий</h1><p>Проверяйте отчёты, материалы и качество проведённых уроков.</p></div><span class="tag warning"><CircleAlert :size="14" /> 5 ожидают проверки</span></div>
    <section class="filters-card card"><div class="control-filters"><label><span>Репетитор</span><select><option>Все репетиторы</option><option>Мария Иванова</option></select></label><label><span>Ученик</span><select><option>Все ученики</option><option>Анна Смирнова</option></select></label><label><span>Статус</span><select v-model="status"><option>Все статусы</option><option>Ожидает проверки</option><option>Проверено</option><option>Нужно исправить</option><option>Отклонено</option></select></label><label><span>Материалы</span><select v-model="material"><option>Все материалы</option><option>Есть материалы</option><option>Нет материалов</option></select></label></div></section>
    <section class="card panel review-table"><div class="section-title"><h2>Занятия</h2><span class="muted tiny">{{ filtered.length }} найдено</span></div><div class="table-wrap"><table><thead><tr><th>Репетитор</th><th>Ученик</th><th>Дата занятия</th><th>Длительность</th><th>Материалы</th><th>Статус проверки</th><th></th></tr></thead><tbody><tr v-for="item in filtered" :key="item.id"><td><div class="table-person"><UserAvatar :initials="item.tutorInitials" color="#d9cdf5" :size="30" /><span><strong>{{ item.tutor }}</strong><span>Репетитор</span></span></div></td><td>{{ item.student }}</td><td>{{ item.date }}</td><td>{{ item.duration }}</td><td><span class="material-icons"><FileVideo :size="16" :class="{ absent: !item.video }" /><Image :size="16" :class="{ absent: !item.shots }" /></span></td><td><span :class="['tag', tagClass(item)]">{{ item.status }}</span></td><td><button class="review-button" @click="open(item)">Открыть</button></td></tr></tbody></table></div><div v-if="!filtered.length" class="empty-compact">Ничего не найдено. Измените параметры фильтра.</div></section>
    <BaseModal v-model="modalOpen" title="Проверка занятия" wide><template v-if="selected"><section class="lesson-summary"><div><span>Дата</span><b>{{ selected.date }}</b></div><div><span>Участники</span><b>{{ selected.tutor }} · {{ selected.student }}</b></div><div><span>Длительность</span><b>{{ selected.duration }}</b></div></section><div class="detail-block"><h3>Тема занятия</h3><p>{{ selected.topic }}</p><h3>Комментарий репетитора</h3><p>Ученица активно работала, разобрали основные ошибки и закрепили тему практическими задачами.</p></div><div class="files"><button :class="{ missing: !selected.video }" @click="messages.showToast(selected.video ? 'Видеозапись открыта' : 'Видеозапись не приложена', selected.video ? 'success' : 'error')"><FileVideo :size="19" /><span><b>Видеозапись</b><small>{{ selected.video ? 'lesson_30-07.mp4' : 'Не приложена' }}</small></span></button><button :class="{ missing: !selected.shots }" @click="messages.showToast(selected.shots ? 'Скриншоты открыты' : 'Скриншоты не приложены', selected.shots ? 'success' : 'error')"><Image :size="19" /><span><b>Скриншоты</b><small>{{ selected.shots ? 'Начало и конец занятия' : 'Не приложены' }}</small></span></button></div><div class="field"><label>Обратная связь репетитору</label><textarea placeholder="Оставьте комментарий или рекомендацию…" /></div></template><template #footer><BaseButton variant="danger" @click="verify('Нужно исправить')"><XCircle :size="15" /> Запросить исправления</BaseButton><BaseButton @click="verify('Проверено')"><CheckCircle2 :size="15" /> Подтвердить часы</BaseButton></template></BaseModal>
  </div>
</template>
<style scoped>
.filters-card{margin-bottom:19px;padding:14px 18px}.control-filters{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.control-filters label{display:grid;gap:5px}.control-filters span{color:var(--text-secondary);font-size:10px;font-weight:700}.control-filters select{min-height:35px;padding:0 8px;border:1px solid var(--border);border-radius:9px;color:#62596d;background:#fff;font-size:11px}.review-table td{font-size:11px}.material-icons{display:flex;gap:7px;color:#5d9f77}.material-icons .absent{color:#c78b8b}.review-button{min-height:30px;padding:0 9px;border:1px solid var(--border);border-radius:8px;color:var(--primary-dark);background:#fff;font-size:10px;font-weight:800}.review-button:hover{background:var(--primary-extra-light)}.lesson-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:12px;background:#faf8fd;border-radius:12px}.lesson-summary span,.lesson-summary b{display:block}.lesson-summary span{color:var(--text-secondary);font-size:9px}.lesson-summary b{margin-top:4px;font-size:10px}.detail-block{margin:17px 0}.detail-block h3{margin:14px 0 5px;font-size:11px}.detail-block p{margin:0;color:#60566c;font-size:11px;line-height:1.6}.files{display:flex;gap:10px;margin-bottom:16px}.files button{display:flex;align-items:center;gap:8px;flex:1;padding:10px;border:1px solid #d8ceeC;border-radius:11px;color:var(--primary-dark);background:#fbf9ff;text-align:left}.files button.missing{color:#aa6a6a;border-color:#edcdcd;background:#fff8f8}.files b,.files small{display:block}.files b{font-size:10px}.files small{margin-top:3px;color:var(--text-secondary);font-size:9px}@media(max-width:760px){.control-filters{grid-template-columns:repeat(2,1fr)}.lesson-summary{grid-template-columns:1fr}.files{flex-direction:column}}@media(max-width:400px){.control-filters{grid-template-columns:1fr}}
</style>
