<script setup>
import { computed, ref } from 'vue'
import { CheckCircle2, CircleAlert, ExternalLink, FileVideo, Image, XCircle } from 'lucide-vue-next'
import { useLessonsStore } from '../stores/lessons'
import { useMessagesStore } from '../stores/messages'
import BaseButton from '../components/BaseButton.vue'
import BaseModal from '../components/BaseModal.vue'
import UserAvatar from '../components/UserAvatar.vue'

const lessons = useLessonsStore()
const messages = useMessagesStore()
const status = ref('Все статусы')
const material = ref('Все материалы')
const tutor = ref('Все репетиторы')
const student = ref('Все ученики')
const selected = ref(null)
const modalOpen = ref(false)

const tutors = computed(() => [...new Set(lessons.reviewLessons.map((item) => item.tutor).filter(Boolean))].sort())
const students = computed(() => [...new Set(lessons.reviewLessons.map((item) => item.student).filter(Boolean))].sort())
const pendingCount = computed(() => lessons.reviewLessons.filter((item) => item.status === 'Ожидает проверки').length)
function videoLink(item) {
  try {
    const url = new URL(String(item?.videoLink || '').trim())
    return ['http:', 'https:'].includes(url.protocol) ? url.href : ''
  } catch {
    return ''
  }
}

const hasMaterials = (item) => Boolean(videoLink(item) || item.shots)
const filtered = computed(() => lessons.reviewLessons.filter((item) => {
  const statusMatches = status.value === 'Все статусы' || item.status === status.value
  const materialMatches = material.value === 'Все материалы'
    || (material.value === 'Есть материалы' ? hasMaterials(item) : !hasMaterials(item))
  return statusMatches
    && materialMatches
    && (tutor.value === 'Все репетиторы' || item.tutor === tutor.value)
    && (student.value === 'Все ученики' || item.student === student.value)
}))
const tagClass = (item) => item.status === 'Проверено' ? 'success' : item.status === 'Нужно исправить' || item.status === 'Отклонено' ? 'danger' : 'warning'

function open(item) {
  selected.value = item
  modalOpen.value = true
}

async function verify(result) {
  if (!selected.value) return
  try {
    await lessons.verifyLesson(selected.value.id, result)
    selected.value = lessons.reviewLessons.find((item) => item.id === selected.value.id) || selected.value
    modalOpen.value = false
    const text = result === 'Проверено' ? 'Занятие проверено, часы подтверждены' : 'Отчёт возвращён на доработку'
    messages.showToast(text, result === 'Проверено' ? 'success' : 'error')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
</script>

<template>
  <div class="page">
    <div class="page-heading">
      <div>
        <h1>Контроль занятий</h1>
        <p>Проверяйте реальные отчёты, которые отправили репетиторы.</p>
      </div>
      <span class="tag warning"><CircleAlert :size="14" /> {{ pendingCount }} ожидают проверки</span>
    </div>

    <section class="filters-card card">
      <div class="control-filters">
        <label><span>Репетитор</span><select v-model="tutor"><option>Все репетиторы</option><option v-for="name in tutors" :key="name">{{ name }}</option></select></label>
        <label><span>Ученик</span><select v-model="student"><option>Все ученики</option><option v-for="name in students" :key="name">{{ name }}</option></select></label>
        <label><span>Статус</span><select v-model="status"><option>Все статусы</option><option>Ожидает проверки</option><option>Проверено</option><option>Нужно исправить</option><option>Отклонено</option></select></label>
        <label><span>Материалы</span><select v-model="material"><option>Все материалы</option><option>Есть материалы</option><option>Нет материалов</option></select></label>
      </div>
    </section>

    <section class="card panel review-table">
      <div class="section-title"><h2>Отчёты по занятиям</h2><span class="muted tiny">{{ filtered.length }} найдено</span></div>
      <div v-if="filtered.length" class="table-wrap">
        <table>
          <thead><tr><th>Репетитор</th><th>Ученик</th><th>Дата занятия</th><th>Длительность</th><th>Материалы</th><th>Статус проверки</th><th></th></tr></thead>
          <tbody>
            <tr v-for="item in filtered" :key="item.id">
              <td><div class="table-person"><UserAvatar :initials="item.tutorInitials" color="#d9cdf5" :size="30" /><span><strong>{{ item.tutor }}</strong><span>Репетитор</span></span></div></td>
              <td>{{ item.student }}</td>
              <td>{{ item.date || 'Не указана' }}</td>
              <td>{{ item.duration || 'Не указана' }}</td>
              <td><span class="material-icons"><FileVideo :size="16" :class="{ absent: !videoLink(item) }" /><Image :size="16" :class="{ absent: !item.shots }" /></span></td>
              <td><span :class="['tag', tagClass(item)]">{{ item.status }}</span></td>
              <td><button class="review-button" @click="open(item)">Открыть</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-compact">
        {{ lessons.reviewLessons.length ? 'По выбранным фильтрам отчётов нет.' : 'Репетиторы ещё не отправили отчёты на проверку.' }}
      </div>
    </section>

    <BaseModal v-model="modalOpen" title="Проверка занятия" wide>
      <template v-if="selected">
        <section class="lesson-summary">
          <div><span>Дата</span><b>{{ selected.date || 'Не указана' }}</b></div>
          <div><span>Участники</span><b>{{ selected.tutor }} · {{ selected.student }}</b></div>
          <div><span>Длительность</span><b>{{ selected.duration || 'Не указана' }}</b></div>
        </section>
        <div class="detail-block">
          <h3>Тема занятия</h3>
          <p>{{ selected.topic || 'Репетитор не указал тему занятия.' }}</p>
          <template v-if="selected.comment">
            <h3>Комментарий репетитора</h3>
            <p>{{ selected.comment }}</p>
          </template>
        </div>
        <div class="files" aria-label="Материалы занятия">
          <div class="video-file" :class="{ missing: !videoLink(selected) }">
            <FileVideo :size="19" />
            <span>
              <b>Видеозапись</b>
              <template v-if="videoLink(selected)">
                <a class="video-url" :href="videoLink(selected)" target="_blank" rel="noopener noreferrer">{{ videoLink(selected) }}</a>
              </template>
              <small v-else>Ссылка не добавлена</small>
            </span>
            <a v-if="videoLink(selected)" class="open-video" :href="videoLink(selected)" target="_blank" rel="noopener noreferrer"><ExternalLink :size="14" /> Открыть видео</a>
          </div>
          <div :class="{ missing: !selected.shots }"><Image :size="19" /><span><b>Скриншоты</b><small>{{ selected.shots ? 'Приложены к отчёту' : 'Не приложены' }}</small></span></div>
        </div>
      </template>
      <template #footer>
        <BaseButton variant="danger" @click="verify('Нужно исправить')"><XCircle :size="15" /> Запросить исправления</BaseButton>
        <BaseButton @click="verify('Проверено')"><CheckCircle2 :size="15" /> Подтвердить часы</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.filters-card{margin-bottom:19px;padding:14px 18px}.control-filters{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.control-filters label{display:grid;gap:5px}.control-filters span{color:var(--text-secondary);font-size:10px;font-weight:700}.control-filters select{min-height:35px;padding:0 8px;border:1px solid var(--border);border-radius:9px;color:#62596d;background:#fff;font-size:11px}.review-table td{font-size:11px}.material-icons{display:flex;gap:7px;color:#5d9f77}.material-icons .absent{color:#c78b8b}.review-button{min-height:30px;padding:0 9px;border:1px solid var(--border);border-radius:8px;color:var(--primary-dark);background:#fff;font-size:10px;font-weight:800}.review-button:hover{background:var(--primary-extra-light)}.empty-compact{padding:24px 0 6px;color:var(--text-secondary);font-size:12px;text-align:center}.lesson-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:12px;background:#faf8fd;border-radius:12px}.lesson-summary span,.lesson-summary b{display:block}.lesson-summary span{color:var(--text-secondary);font-size:9px}.lesson-summary b{margin-top:4px;font-size:10px}.detail-block{margin:17px 0}.detail-block h3{margin:14px 0 5px;font-size:11px}.detail-block p{margin:0;color:#60566c;font-size:11px;line-height:1.6}.files{display:flex;gap:10px;margin-bottom:5px}.files>div{display:flex;align-items:center;gap:8px;flex:1;min-width:0;padding:10px;border:1px solid #d8ceec;border-radius:11px;color:var(--primary-dark);background:#fbf9ff}.files>div.missing{color:#aa6a6a;border-color:#edcdcd;background:#fff8f8}.files b,.files small{display:block}.files b{font-size:10px}.files small{margin-top:3px;color:var(--text-secondary);font-size:9px}.video-file>span{min-width:0;flex:1}.video-url{display:block;overflow:hidden;margin-top:3px;color:var(--primary-dark);font-size:9px;line-height:1.35;text-decoration:underline;text-overflow:ellipsis;white-space:nowrap}.open-video{display:inline-flex;align-items:center;justify-content:center;gap:4px;flex:0 0 auto;min-height:30px;padding:0 8px;border-radius:8px;color:#fff;background:var(--primary);font-size:9px;font-weight:800;white-space:nowrap}.open-video:hover{background:var(--primary-dark)}@media(max-width:760px){.control-filters{grid-template-columns:repeat(2,1fr)}.lesson-summary{grid-template-columns:1fr}.files{flex-direction:column}}@media(max-width:400px){.control-filters{grid-template-columns:1fr}.video-file{align-items:flex-start!important;flex-wrap:wrap}.video-file>span{width:calc(100% - 28px);flex:0 0 calc(100% - 28px)}.open-video{width:100%}}
</style>
