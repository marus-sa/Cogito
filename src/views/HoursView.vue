<script setup>
import { computed, reactive, ref } from 'vue'
import { CheckCircle2, Clock3, FileVideo, Image, Plus, Upload } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useLessonsStore } from '../stores/lessons'
import { useMessagesStore } from '../stores/messages'
import BaseButton from '../components/BaseButton.vue'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import StatCard from '../components/StatCard.vue'

const auth = useAuthStore()
const lessons = useLessonsStore()
const messages = useMessagesStore()
const modalOpen = ref(false)
const report = reactive({ student: '', date: '', duration: '', topic: '', videoLink: '' })
const tutorMode = computed(() => auth.roleKey === 'tutor')
const entries = computed(() => lessons.reviewLessons)

function durationMinutes(value) {
  const text = String(value || '').toLowerCase()
  const hours = Number(text.match(/(\d+(?:[.,]\d+)?)\s*ч/)?.[1]?.replace(',', '.') || 0)
  const minutes = Number(text.match(/(\d+(?:[.,]\d+)?)\s*мин/)?.[1]?.replace(',', '.') || 0)
  if (hours || minutes) return Math.round(hours * 60 + minutes)

  const fallback = Number(text.match(/\d+(?:[.,]\d+)?/)?.[0]?.replace(',', '.'))
  return Number.isFinite(fallback) ? Math.round(fallback) : 0
}

function formatHours(minutes) {
  if (!minutes) return '0 ч'
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (!hours) return `${rest} мин`
  return rest ? `${hours} ч ${rest} мин` : `${hours} ч`
}

const totalMinutes = computed(() => entries.value.reduce((sum, item) => sum + durationMinutes(item.duration), 0))
const approvedMinutes = computed(() => entries.value
  .filter((item) => item.status === 'Проверено')
  .reduce((sum, item) => sum + durationMinutes(item.duration), 0))
const pendingMinutes = computed(() => entries.value
  .filter((item) => item.status === 'Ожидает проверки')
  .reduce((sum, item) => sum + durationMinutes(item.duration), 0))

function statusClass(status) {
  if (status === 'Проверено') return 'success'
  if (status === 'Ожидает проверки') return 'warning'
  return 'danger'
}

function resetReport() {
  Object.assign(report, { student: '', date: '', duration: '', topic: '', videoLink: '' })
}

function safeVideoLink(value) {
  try {
    const url = new URL(String(value || '').trim())
    return ['http:', 'https:'].includes(url.protocol) ? url.href : ''
  } catch {
    return ''
  }
}

async function submit() {
  if (!report.student.trim() || !report.date || !report.duration || !report.topic.trim()) {
    messages.showToast('Заполните ученика, дату, длительность и тему занятия', 'error')
    return
  }

  const videoLink = safeVideoLink(report.videoLink)
  if (report.videoLink && !videoLink) {
    messages.showToast('Вставьте корректную ссылку на видеозапись', 'error')
    return
  }

  try {
    await lessons.addReview({ ...report, videoLink })
    modalOpen.value = false
    resetReport()
    messages.showToast('Отчёт отправлен на проверку')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
</script>

<template>
  <div class="page">
    <div class="page-heading">
      <div>
        <h1>{{ tutorMode ? 'Мои часы' : 'Волонтёрские часы' }}</h1>
        <p>{{ tutorMode ? 'Учтены часы из ваших отчётов о проведённых занятиях.' : 'Учтены часы из доступных вам отчётов о занятиях.' }}</p>
      </div>
      <BaseButton v-if="tutorMode" @click="modalOpen = true"><Plus :size="17" /> Добавить отчёт</BaseButton>
    </div>

    <section class="grid three-col">
      <StatCard label="Всего по отчётам" :value="formatHours(totalMinutes)" icon="Clock3" />
      <StatCard label="Подтверждено" :value="formatHours(approvedMinutes)" icon="CheckCircle2" tone="green" />
      <StatCard label="Ожидает проверки" :value="formatHours(pendingMinutes)" icon="FileVideo" tone="orange" />
    </section>

    <section class="card panel hours-list">
      <div class="section-title">
        <div>
          <h2>История отчётов</h2>
          <p class="muted tiny">Длительность берётся из каждого сохранённого отчёта.</p>
        </div>
        <span class="tag">{{ entries.length }}</span>
      </div>

      <div v-if="entries.length" class="table-wrap">
        <table>
          <thead>
            <tr><th>Занятие</th><th>Дата</th><th>Длительность</th><th>Материалы</th><th>Статус</th></tr>
          </thead>
          <tbody>
            <tr v-for="item in entries" :key="item.id">
              <td>
                <b>{{ item.topic || 'Тема не указана' }}</b>
                <small>{{ item.student || 'Ученик не указан' }}</small>
              </td>
              <td>{{ item.date || 'Не указана' }}</td>
              <td><b>{{ item.duration || 'Не указана' }}</b></td>
              <td>
                <span class="materials">
                  <FileVideo :size="14" :class="{ missing: !item.videoLink }" />
                  <Image :size="14" :class="{ missing: !item.shots }" />
                  <small>{{ item.videoLink ? 'Видео по ссылке' : item.shots ? 'Скриншоты отмечены' : 'Не отмечены' }}</small>
                </span>
              </td>
              <td><span :class="['tag', statusClass(item.status)]">{{ item.status }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState
        v-else
        title="Отчётов о занятиях пока нет"
        :text="tutorMode ? 'После проведения занятия добавьте первый отчёт — часы появятся здесь.' : 'Когда появятся доступные отчёты, часы будут рассчитаны автоматически.'"
      />
    </section>

    <BaseModal v-model="modalOpen" title="Отчёт о проведённом занятии" wide>
      <p class="modal-copy">После отправки отчёт появится у наставника или администратора для проверки.</p>
      <div class="form-grid">
        <div class="field"><label>Ученик</label><input v-model.trim="report.student" placeholder="Полное имя ученика" /></div>
        <div class="field"><label>Дата занятия</label><input v-model="report.date" type="date" /></div>
        <div class="field"><label>Длительность</label><select v-model="report.duration"><option disabled value="">Выберите длительность</option><option>45 мин</option><option>60 мин</option><option>90 мин</option></select></div>
        <div class="field"><label>Тема занятия</label><input v-model.trim="report.topic" placeholder="Кратко укажите тему" /></div>
        <div class="field full">
          <label>Ссылка на видеозапись в облаке <span class="optional">(необязательно)</span></label>
          <input v-model.trim="report.videoLink" type="url" inputmode="url" autocomplete="url" placeholder="https://drive.google.com/..." />
          <small class="field-hint">Подойдут Яндекс Диск, Google Диск и другие облака. Откройте доступ «Просмотр по ссылке».</small>
        </div>
      </div>
      <p class="files-note">Файлы в приложение не загружаются: вставьте ссылку на запись из Google Диска, Яндекс Диска или другого хранилища.</p>
      <template #footer>
        <BaseButton variant="outline" @click="modalOpen = false">Отмена</BaseButton>
        <BaseButton @click="submit"><Upload :size="15" /> Отправить отчёт</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.hours-list{margin-top:19px}.section-title p{margin:3px 0 0}.hours-list td b,.hours-list td small{display:block}.hours-list td b{font-size:11px}.hours-list td small{margin-top:3px;color:var(--text-secondary);font-size:10px}.materials{display:flex;align-items:center;gap:7px;color:#5b9b74}.materials small{margin:0!important}.materials .missing{color:#c38b8b}.modal-copy{margin:0 0 15px;color:var(--text-secondary);font-size:11px;line-height:1.5}.optional{color:var(--text-secondary);font-size:10px;font-weight:500}.field-hint{margin-top:-2px;color:var(--text-secondary);font-size:10px;line-height:1.4}.files-note{margin:16px 0 0;padding:11px 12px;border-radius:10px;color:#655b72;background:#faf8fd;font-size:10px;line-height:1.5}
</style>
