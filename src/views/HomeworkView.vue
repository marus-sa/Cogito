<script setup>
import { computed, reactive, ref } from 'vue'
import {
  Check,
  CheckCheck,
  ExternalLink,
  FilePlus2,
  Link2,
  Paperclip,
  Plus,
  Send,
  Star,
} from 'lucide-vue-next'
import { useHomeworkStore } from '../stores/homework'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import { api } from '../api'
import { emptyHomework } from '../helpers'
import BaseButton from '../components/BaseButton.vue'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import HomeworkFiles from '../components/HomeworkFiles.vue'

const homeworkStore = useHomeworkStore()
const auth = useAuthStore()
const messages = useMessagesStore()
const tab = ref('Все')
const createOpen = ref(false)
const submitOpen = ref(false)
const gradeOpen = ref(false)
const detailsOpen = ref(false)
const selected = ref(null)
const assignments = ref([])
const loadingStudents = ref(false)
const studentsError = ref('')
const creating = ref(false)
const sending = ref(false)
const chosenFiles = ref([])
const canManageHomework = computed(() => ['tutor', 'mentor', 'admin'].includes(auth.roleKey))
const form = reactive(emptyHomework())
const submission = reactive({ comment: '', link: '' })
const grade = reactive({ score: null, comment: '', decision: 'accept' })
const statuses = ['Все', 'Новые', 'В работе', 'Сданы', 'Проверено', 'Просрочено']
const filtered = computed(() => homeworkByStatus(tab.value))

function homeworkByStatus(status) {
  if (status === 'Все') return homeworkStore.homework
  return homeworkStore.homework.filter((item) => item.status === status)
}

function statusClass(status) {
  const colors = { Проверено: 'success', Просрочено: 'danger', 'В работе': 'warning', Сданы: 'purple' }
  return colors[status] || 'gray'
}

const isHttpLink = (value) => /^https?:\/\//i.test(value || '')
const assignmentKey = (item) => `${item.studentId}:${item.tutorId}`

async function openCreate() {
  createOpen.value = true
  loadingStudents.value = true
  studentsError.value = ''
  try {
    const data = await api('/homework/students')
    assignments.value = data.items
  } catch (error) {
    assignments.value = []
    studentsError.value = error.message
  } finally {
    loadingStudents.value = false
  }
}

async function create() {
  if (creating.value) return
  if (!form.title.trim()) {
    messages.showToast('Укажите название задания', 'error')
    return
  }
  const assignment = assignments.value.find((item) => assignmentKey(item) === form.assignment)
  if (!assignment) {
    messages.showToast('Выберите ученика из списка', 'error')
    return
  }
  creating.value = true
  try {
    await homeworkStore.addHomework({
      ...form,
      studentId: assignment.studentId,
      tutorId: assignment.tutorId,
    })
    createOpen.value = false
    Object.assign(form, emptyHomework())
    messages.showToast('Домашнее задание создано')
  } catch (error) {
    messages.showToast(error.message, 'error')
  } finally {
    creating.value = false
  }
}

function submit(item) {
  selected.value = item
  chosenFiles.value = []
  Object.assign(submission, {
    comment: item.submissionComment || '',
    link: item.submissionLink || '',
  })
  submitOpen.value = true
}

async function sendWork() {
  if (sending.value) return
  const existing = selected.value.submissionFiles || []
  const files = [...existing, ...chosenFiles.value]
  if (files.length > 5) {
    messages.showToast('К одной работе можно прикрепить до 5 файлов', 'error')
    return
  }
  let totalSize = 0
  for (const file of files) totalSize += file.size
  if (totalSize > 8 * 1024 * 1024) {
    messages.showToast('Общий размер файлов — до 8 МБ. Большую работу можно отправить ссылкой.', 'error')
    return
  }
  sending.value = true
  try {
    const data = new FormData()
    data.append('comment', submission.comment)
    data.append('submissionLink', submission.link)
    for (const file of chosenFiles.value) data.append('files', file)
    await homeworkStore.submitHomework(selected.value.id, data)
    submitOpen.value = false
    messages.showToast('Работа отправлена репетитору')
  } catch (error) {
    messages.showToast(error.message, 'error')
  } finally {
    sending.value = false
  }
}

async function removeFile(file) {
  if (sending.value || !window.confirm(`Удалить файл «${file.name}» из этой работы?`)) return
  sending.value = true
  try {
    selected.value = await homeworkStore.removeFile(selected.value.id, file.id)
  } catch (error) {
    messages.showToast(error.message, 'error')
  } finally {
    sending.value = false
  }
}

function review(item) {
  selected.value = item
  Object.assign(grade, { score: null, comment: item.reviewComment || '', decision: 'accept' })
  gradeOpen.value = true
}

async function gradeWork() {
  if (
    grade.decision === 'accept' &&
    (!Number.isFinite(Number(grade.score)) || Number(grade.score) < 0 || Number(grade.score) > 10)
  ) {
    messages.showToast('Укажите балл от 0 до 10', 'error')
    return
  }
  try {
    await homeworkStore.gradeHomework(selected.value.id, {
      decision: grade.decision,
      score: grade.decision === 'accept' ? `${grade.score} / 10` : '',
      comment: grade.comment,
    })
    gradeOpen.value = false
    messages.showToast(
      grade.decision === 'accept'
        ? 'Оценка и комментарий сохранены'
        : 'Работа возвращена на доработку',
    )
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}

function openDetails(item) {
  selected.value = item
  detailsOpen.value = true
}
</script>

<template>
  <div class="page">
    <div class="page-heading">
      <div>
        <h1>Домашние задания</h1>
        <p>Все задания, сроки и обратная связь от репетитора.</p>
      </div>
      <BaseButton v-if="canManageHomework" @click="openCreate">
        <Plus :size="17" />
        Задать домашнее задание
      </BaseButton>
    </div>
    <section class="tabs">
      <button
        v-for="name in statuses"
        :key="name"
        :class="{ active: tab === name }"
        @click="tab = name"
      >
        {{ name }}
        <span>{{ homeworkByStatus(name).length }}</span>
      </button>
    </section>

    <section v-if="filtered.length" class="homework-grid">
      <article v-for="item in filtered" :key="item.id" class="homework-card card card-hover">
        <header>
          <span :class="['tag', statusClass(item.status)]">{{ item.status }}</span>
          <span v-if="item.score" class="score">
            <Star :size="13" />
            {{ item.score }}
          </span>
        </header>
        <div class="subject-icon"><FilePlus2 :size="21" /></div>
        <p class="subject">{{ item.subject }}</p>
        <h2>{{ item.title }}</h2>
        <p class="description">{{ item.description }}</p>
        <div class="task-info">
          <span>
            Ученик
            <b>{{ item.student }}</b>
          </span>
          <span>
            Срок
            <b>{{ item.deadline }}</b>
          </span>
        </div>
        <div class="card-footer">
          <a
            v-if="isHttpLink(item.attachment)"
            class="attachment"
            :href="item.attachment"
            target="_blank"
            rel="noopener"
          >
            <Paperclip :size="13" />
            Материалы
          </a>
          <span v-else-if="item.attachment" class="attachment">
            <Paperclip :size="13" />
            {{ item.attachment }}
          </span>
          <span v-else class="muted tiny">Без материалов</span>
          <BaseButton
            v-if="canManageHomework && ['Сданы', 'В работе'].includes(item.status)"
            size="sm"
            @click="review(item)"
          >
            Проверить
          </BaseButton>
          <BaseButton
            v-else-if="!canManageHomework && ['Новые', 'В работе', 'Сданы'].includes(item.status)"
            size="sm"
            @click="submit(item)"
          >
            {{ item.status === 'Сданы' ? 'Изменить ответ' : 'Сдать работу' }}
          </BaseButton>
          <button v-else class="view-button" @click="openDetails(item)">Подробнее</button>
        </div>
      </article>
    </section>
    <section v-else class="card">
      <EmptyState
        title="В этой категории пока нет заданий"
        text="Попробуйте выбрать другую вкладку или создайте новое задание."
      />
    </section>

    <BaseModal v-model="createOpen" title="Новое домашнее задание" wide>
      <div class="form-grid">
        <div class="field">
          <label for="homework-student">Ученик</label>
          <select id="homework-student" v-model="form.assignment" :disabled="loadingStudents">
            <option value="" disabled>{{ loadingStudents ? 'Загрузка учеников…' : 'Выберите ученика' }}</option>
            <option v-for="item in assignments" :key="assignmentKey(item)" :value="assignmentKey(item)">
              {{ item.student }}{{ item.grade ? ` · ${item.grade} класс` : '' }}
              {{ auth.roleKey === 'tutor' ? '' : ` · Репетитор: ${item.tutor}` }}
            </option>
          </select>
          <small v-if="studentsError" class="field-note" role="alert">{{ studentsError }}</small>
          <small v-else-if="!loadingStudents && !assignments.length" class="field-note">
            Закреплённых учеников пока нет. Администратор может добавить связь «Ученик — репетитор» в «Участниках».
          </small>
        </div>
        <div class="field">
          <label>Предмет</label>
          <input v-model.trim="form.subject" placeholder="Например, математика" />
        </div>
        <div class="field full">
          <label>Название</label>
          <input v-model.trim="form.title" placeholder="Например, задачи на линейные уравнения" />
        </div>
        <div class="field full">
          <label>Описание</label>
          <textarea v-model="form.description" placeholder="Объясните, что нужно сделать…" />
        </div>
        <div class="field">
          <label>Срок</label>
          <input v-model.trim="form.deadline" placeholder="Например, 7 августа" />
        </div>
        <div class="field">
          <label>Максимальный балл</label>
          <input v-model.number="form.maxScore" type="number" min="1" max="100" />
        </div>
        <div class="field full">
          <label>
            <Link2 :size="15" />
            Ссылка на материалы
          </label>
          <input
            v-model.trim="form.attachment"
            type="url"
            placeholder="https://drive.google.com/..."
          />
          <small class="field-note">
            Добавьте Google Drive, Яндекс Диск или другую защищённую ссылку.
          </small>
        </div>
      </div>
      <template #footer>
        <BaseButton variant="outline" @click="createOpen = false">Отмена</BaseButton>
        <BaseButton :loading="creating" :disabled="loadingStudents || !form.assignment" @click="create">
          Создать задание
        </BaseButton>
      </template>
    </BaseModal>

    <BaseModal v-model="submitOpen" title="Сдать домашнее задание">
      <p class="modal-copy">
        Прикрепите файлы с выполненной работой, оставьте комментарий или добавьте ссылку.
      </p>
      <div class="field">
        <label>Комментарий</label>
        <textarea
          v-model="submission.comment"
          placeholder="Например, мне было сложно с заданием 8…"
        />
      </div>
      <div class="field">
        <label>
          <Link2 :size="15" />
          Ссылка на работу
        </label>
        <input
          v-model.trim="submission.link"
          type="url"
          placeholder="https://drive.google.com/..."
        />
        <small class="field-note">Можно прикрепить ссылку на фото, PDF или документ.</small>
      </div>
      <HomeworkFiles :files="selected?.submissionFiles || []" removable :busy="sending" @remove="removeFile" />
      <div class="field">
        <label for="homework-files">Файлы с работой</label>
        <input id="homework-files" type="file" multiple :disabled="sending"
          accept=".pdf,.docx,.txt,.jpg,.jpeg,.png,.webp,.heic,.heif"
          @change="chosenFiles = Array.from($event.target.files || [])" />
        <small class="field-note">PDF, DOCX, TXT и фото. До 5 файлов общим размером до 8 МБ. Большую работу отправьте ссылкой на диск.</small>
        <p v-for="(file, index) in chosenFiles" :key="index" class="field-note">{{ file.name }}</p>
      </div>
      <template #footer>
        <BaseButton variant="outline" @click="submitOpen = false">Отмена</BaseButton>
        <BaseButton :loading="sending" @click="sendWork">
          <Send :size="15" />
          Отправить
        </BaseButton>
      </template>
    </BaseModal>

    <BaseModal v-model="gradeOpen" title="Проверить работу">
      <p class="modal-copy">{{ selected?.title }} · {{ selected?.student }}</p>
      <HomeworkFiles :files="selected?.submissionFiles || []" />
      <p v-if="selected?.submissionComment" class="student-note">
        <b>Комментарий ученика:</b>
        {{ selected.submissionComment }}
      </p>
      <a
        v-if="isHttpLink(selected?.submissionLink)"
        class="submission-link"
        :href="selected.submissionLink"
        target="_blank"
        rel="noopener"
      >
        <ExternalLink :size="15" />
        Открыть выполненную работу
      </a>
      <div class="form-grid">
        <div class="field">
          <label>Решение</label>
          <select v-model="grade.decision">
            <option value="accept">Принять работу</option>
            <option value="revise">Вернуть на доработку</option>
          </select>
        </div>
        <div v-if="grade.decision === 'accept'" class="field">
          <label>Балл из 10</label>
          <input v-model.number="grade.score" type="number" min="0" max="10" />
        </div>
        <div class="field full">
          <label>Комментарий ученику</label>
          <textarea
            v-model="grade.comment"
            placeholder="Что получилось хорошо и что стоит исправить"
          />
        </div>
      </div>
      <template #footer>
        <BaseButton variant="outline" @click="gradeOpen = false">Отмена</BaseButton>
        <BaseButton @click="gradeWork">
          <CheckCheck :size="16" />
          Сохранить проверку
        </BaseButton>
      </template>
    </BaseModal>

    <BaseModal v-model="detailsOpen" title="Домашнее задание">
      <template v-if="selected">
        <p class="modal-copy">
          <b>{{ selected.title }}</b>
          · {{ selected.subject }}
        </p>
        <dl class="details-list">
          <div>
            <dt>Ученик</dt>
            <dd>{{ selected.student }}</dd>
          </div>
          <div>
            <dt>Срок</dt>
            <dd>{{ selected.deadline }}</dd>
          </div>
          <div>
            <dt>Статус</dt>
            <dd>{{ selected.status }}</dd>
          </div>
          <div v-if="selected.score">
            <dt>Оценка</dt>
            <dd>{{ selected.score }}</dd>
          </div>
        </dl>
        <p v-if="selected.description" class="detail-text">{{ selected.description }}</p>
        <HomeworkFiles :files="selected.submissionFiles || []" />
        <a
          v-if="isHttpLink(selected.attachment)"
          class="submission-link"
          :href="selected.attachment"
          target="_blank"
          rel="noopener"
        >
          <ExternalLink :size="15" />
          Открыть материалы
        </a>
        <p v-if="selected.submissionComment" class="student-note">
          <b>Комментарий ученика:</b>
          {{ selected.submissionComment }}
        </p>
        <a
          v-if="isHttpLink(selected.submissionLink)"
          class="submission-link"
          :href="selected.submissionLink"
          target="_blank"
          rel="noopener"
        >
          <ExternalLink :size="15" />
          Открыть выполненную работу
        </a>
        <p v-if="selected.reviewComment" class="student-note review-note">
          <b>Комментарий репетитора:</b>
          {{ selected.reviewComment }}
        </p>
      </template>
      <template #footer><BaseButton @click="detailsOpen = false">Закрыть</BaseButton></template>
    </BaseModal>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  margin-bottom: 19px;
  padding-bottom: 2px;
}
.tabs button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 35px;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text-secondary);
  background: #fff;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}
.tabs button span {
  display: grid;
  place-items: center;
  min-width: 17px;
  height: 17px;
  padding: 0 3px;
  background: #f2eff5;
  border-radius: 6px;
  font-size: 9px;
}
.tabs button.active {
  color: var(--primary-dark);
  border-color: #cfc1ed;
  background: var(--primary-extra-light);
}
.tabs button.active span {
  color: #fff;
  background: var(--primary);
}
.homework-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 17px;
}
.homework-card {
  display: flex;
  flex-direction: column;
  min-height: 298px;
  padding: 18px;
}
.homework-card header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.score {
  display: flex;
  align-items: center;
  gap: 3px;
  color: #a77a32;
  font-size: 11px;
  font-weight: 800;
}
.subject-icon {
  display: grid;
  place-items: center;
  width: 41px;
  height: 41px;
  margin-top: 18px;
  color: var(--primary-dark);
  background: var(--primary-extra-light);
  border-radius: 13px;
}
.subject {
  margin: 12px 0 4px;
  color: var(--primary-dark);
  font-size: 10px;
  font-weight: 800;
}
.homework-card h2 {
  margin: 0;
  font-size: 14px;
  line-height: 1.35;
}
.description {
  display: -webkit-box;
  min-height: 38px;
  margin: 8px 0;
  color: var(--text-secondary);
  font-size: 10px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}
.task-info {
  display: grid;
  gap: 5px;
  margin-top: auto;
  padding: 10px 0;
  border-top: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 10px;
}
.task-info b {
  color: var(--text-main);
}
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 10px;
}
.attachment {
  display: flex;
  align-items: center;
  max-width: 54%;
  gap: 3px;
  overflow: hidden;
  color: var(--primary-dark);
  font-size: 9px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.view-button {
  border: 0;
  color: var(--primary-dark);
  background: transparent;
  font-size: 10px;
  font-weight: 800;
}
.field-note {
  display: block;
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 9px;
}
.modal-copy {
  margin: 0 0 16px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
}
.student-note,
.detail-text {
  margin: 12px 0;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.55;
}
.review-note {
  padding: 10px;
  border-radius: 10px;
  background: #f6f2fe;
}
.submission-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin: 3px 0 13px;
  color: var(--primary-dark);
  font-size: 11px;
  font-weight: 800;
}
.details-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 0;
}
.details-list div {
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
}
.details-list dt {
  color: var(--text-secondary);
  font-size: 9px;
}
.details-list dd {
  margin: 4px 0 0;
  font-size: 11px;
  font-weight: 800;
}
@media (max-width: 1050px) {
  .homework-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 570px) {
  .homework-grid {
    grid-template-columns: 1fr;
  }
  .homework-card {
    min-height: 270px;
  }
  .details-list {
    grid-template-columns: 1fr;
  }
}
</style>
