<script setup>
import { computed } from 'vue'
import { BookOpen, CalendarDays, CheckCircle2, Target, TrendingUp } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useHomeworkStore } from '../stores/homework'
import { useLessonsStore } from '../stores/lessons'
import EmptyState from '../components/EmptyState.vue'
import ProgressBar from '../components/ProgressBar.vue'
import StatCard from '../components/StatCard.vue'

const auth = useAuthStore()
const homework = useHomeworkStore()
const lessons = useLessonsStore()

function goalTasks(goal) {
  return Array.isArray(goal.tasks) ? goal.tasks : []
}

function scorePercent(score) {
  const match = String(score || '').match(/^\s*(\d+(?:[.,]\d+)?)\s*\/\s*(\d+(?:[.,]\d+)?)\s*$/)
  if (!match) return null

  const earned = Number(match[1].replace(',', '.'))
  const total = Number(match[2].replace(',', '.'))
  if (!Number.isFinite(earned) || !Number.isFinite(total) || total <= 0) return null

  return Math.round((earned / total) * 100)
}

const scopeText = computed(() => {
  const texts = {
    student: 'Здесь собраны данные по вашим заданиям, занятиям и учебным целям.',
    parent: 'Здесь собраны доступные данные по заданиям, занятиям и учебным целям ребёнка.',
    tutor: 'Здесь собраны данные по доступным заданиям, занятиям и учебным целям учеников.',
    mentor: 'Здесь собраны данные по доступным занятиям и учебным целям команды.',
    admin: 'Здесь собраны данные по занятиям, заданиям и учебным целям проекта.',
  }
  return texts[auth.roleKey] || 'Здесь собраны доступные данные об учебном прогрессе.'
})

const gradedHomework = computed(() => homework.homework.filter((item) => item.score))
const scoredHomework = computed(() => gradedHomework.value
  .map((item) => ({ ...item, percent: scorePercent(item.score) }))
  .filter((item) => item.percent !== null))
const averageScore = computed(() => {
  if (!scoredHomework.value.length) return null
  return Math.round(scoredHomework.value.reduce((sum, item) => sum + item.percent, 0) / scoredHomework.value.length)
})
const completedHomework = computed(() => homework.homework.filter((item) => ['Сданы', 'Проверено'].includes(item.status)).length)
const heldLessons = computed(() => lessons.lessons.filter((item) => item.status === 'Проведено').length)
const totalGoalTasks = computed(() => homework.goals.reduce((sum, goal) => sum + goalTasks(goal).length, 0))
const completedGoalTasks = computed(() => homework.goals.reduce(
  (sum, goal) => sum + goalTasks(goal).filter((task) => task.done).length,
  0,
))
const goalProgress = computed(() => totalGoalTasks.value
  ? Math.round((completedGoalTasks.value / totalGoalTasks.value) * 100)
  : 0)
const hasData = computed(() => homework.homework.length || lessons.lessons.length || homework.goals.length)

const subjects = computed(() => {
  const result = new Map()
  const add = (subject, type) => {
    const name = String(subject || '').trim()
    if (!name) return
    if (!result.has(name)) result.set(name, { name, homework: 0, lessons: 0, goals: 0 })
    result.get(name)[type] += 1
  }

  homework.homework.forEach((item) => add(item.subject, 'homework'))
  lessons.lessons.forEach((item) => add(item.subject, 'lessons'))
  homework.goals.forEach((item) => add(item.subject, 'goals'))

  return [...result.values()].sort((first, second) => {
    const firstCount = first.homework + first.lessons + first.goals
    const secondCount = second.homework + second.lessons + second.goals
    return secondCount - firstCount || first.name.localeCompare(second.name, 'ru')
  })
})

function progress(goal) {
  const tasks = goalTasks(goal)
  return tasks.length ? Math.round((tasks.filter((task) => task.done).length / tasks.length) * 100) : 0
}
</script>

<template>
  <div class="page">
    <div class="page-heading">
      <div>
        <h1>Прогресс и успеваемость</h1>
        <p>{{ scopeText }}</p>
      </div>
    </div>

    <section class="grid four-col">
      <StatCard
        label="Средний результат"
        :value="averageScore === null ? '—' : `${averageScore}%`"
        icon="TrendingUp"
        tone="green"
      />
      <StatCard label="Сдано или проверено" :value="completedHomework" icon="CheckCircle2" />
      <StatCard label="Проведено занятий" :value="heldLessons" icon="CalendarDays" tone="orange" />
      <StatCard label="Прогресс по целям" :value="`${goalProgress}%`" icon="Target" tone="rose" />
    </section>

    <section v-if="hasData" class="grid two-col below">
      <section class="card panel">
        <div class="section-title">
          <div>
            <h2>Результаты проверок</h2>
            <p class="muted tiny">Показываются только сохранённые оценки.</p>
          </div>
          <span class="tag">{{ gradedHomework.length }}</span>
        </div>

        <div v-if="gradedHomework.length" class="table-wrap">
          <table>
            <thead>
              <tr><th>Задание</th><th>Предмет</th><th>Оценка</th><th>Статус</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in gradedHomework" :key="item.id">
                <td><b>{{ item.title }}</b></td>
                <td>{{ item.subject || 'Не указан' }}</td>
                <td>{{ item.score }}</td>
                <td><span class="tag success">{{ item.status }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-compact">Проверенных заданий с оценкой пока нет.</div>
      </section>

      <section class="card panel">
        <div class="section-title">
          <h2>Учебные цели</h2>
          <span class="tag">{{ homework.goals.length }}</span>
        </div>

        <div v-if="homework.goals.length" class="goal-list">
          <article v-for="goal in homework.goals" :key="goal.id" class="goal-item">
            <div class="goal-head">
              <div>
                <b>{{ goal.title }}</b>
                <span>{{ goal.subject || 'Предмет не указан' }} · {{ goalTasks(goal).filter((task) => task.done).length }} из {{ goalTasks(goal).length }} шагов</span>
              </div>
              <strong>{{ progress(goal) }}%</strong>
            </div>
            <ProgressBar :value="progress(goal)" :show-label="false" />
          </article>
        </div>
        <div v-else class="empty-compact">Учебные цели пока не добавлены.</div>
      </section>
    </section>

    <section v-if="hasData" class="card panel below">
      <div class="section-title">
        <h2>Данные по предметам</h2>
        <BookOpen :size="18" class="light-icon" />
      </div>

      <div v-if="subjects.length" class="subjects">
        <article v-for="item in subjects" :key="item.name" class="subject-item">
          <b>{{ item.name }}</b>
          <span>Занятий: {{ item.lessons }} · заданий: {{ item.homework }} · целей: {{ item.goals }}</span>
        </article>
      </div>
      <div v-else class="empty-compact">В занятиях, заданиях и целях пока не указан предмет.</div>
    </section>

    <section v-else class="card">
      <EmptyState
        title="Данных о прогрессе пока нет"
        text="Они появятся после создания занятий, заданий или учебных целей."
      />
    </section>
  </div>
</template>

<style scoped>
.below{margin-top:19px}.section-title p{margin:3px 0 0}.goal-list{display:grid;gap:14px}.goal-item{padding:13px;border:1px solid var(--border);border-radius:13px;background:#fcfbfe}.goal-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px}.goal-head b,.goal-head span{display:block}.goal-head b{font-size:12px}.goal-head span{margin-top:4px;color:var(--text-secondary);font-size:10px}.goal-head strong{font-size:13px}.subjects{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.subject-item{padding:14px;border:1px solid var(--border);border-radius:13px;background:#fcfbfe}.subject-item b,.subject-item span{display:block}.subject-item b{font-size:12px}.subject-item span{margin-top:4px;color:var(--text-secondary);font-size:10px;line-height:1.5}.light-icon{color:var(--primary)}@media(max-width:850px){.subjects{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:560px){.subjects{grid-template-columns:1fr}}
</style>
