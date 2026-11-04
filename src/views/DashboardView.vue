<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  ArrowRight,
  BookOpenCheck,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  ClipboardCheck,
  Clock3,
  FileCheck2,
  MessageSquareText,
  Plus,
  Sparkles,
  UsersRound,
} from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useHomeworkStore } from '../stores/homework'
import { useLessonsStore } from '../stores/lessons'
import { useMessagesStore } from '../stores/messages'
import { api } from '../api'
import StatCard from '../components/StatCard.vue'
import ProgressBar from '../components/ProgressBar.vue'
import UserAvatar from '../components/UserAvatar.vue'
import { countText, formatHours, initialsFromName, notificationPath, sumReportMinutes, uniqueNames } from '../helpers'

const auth = useAuthStore()
const router = useRouter()
const homeworkStore = useHomeworkStore()
const lessonsStore = useLessonsStore()
const messageStore = useMessagesStore()
const role = computed(() => auth.roleKey)
const studentTask = computed(
  () =>
    homeworkStore.homework.find((item) => item.status !== 'Проверено') || {
      title: 'Новых заданий пока нет',
      subject: '—',
      deadline: '—',
    },
)
const upcoming = computed(
  () => lessonsStore.lessons.find((item) => item.status === 'Запланировано') || null,
)
const reviewedHomework = computed(() =>
  homeworkStore.homework.filter((item) => item.status === 'Проверено'),
)
const latestReviewedHomework = computed(() => reviewedHomework.value[0] || null)
const parentHasData = computed(
  () =>
    homeworkStore.homework.length > 0 ||
    lessonsStore.lessons.length > 0,
)
const students = computed(() => {
  const records = [...lessonsStore.lessons, ...homeworkStore.homework]
  const names = uniqueNames(records, 'student')
  const colors = ['#b39ddb', '#9ebad5', '#a8cdbb', '#e2b9c7']
  const result = []
  for (const [index, name] of names.entries()) {
    const lesson = lessonsStore.lessons.find((item) => item.student === name)
    const homework = homeworkStore.homework.filter((item) => item.student === name)
    const checked = homework.filter((item) => item.status === 'Проверено').length
    result.push({
      id: name,
      name,
      initials: initialsFromName(name),
      detail: lesson?.subject || homework[0]?.subject || 'Предмет не указан',
      color: colors[index % colors.length],
      homeworkCount: homework.length,
      checkedHomework: checked,
      homeworkProgress: homework.length ? Math.round((checked / homework.length) * 100) : 0,
    })
  }
  return result
})
const tutorPlannedLessons = computed(() =>
  lessonsStore.lessons.filter((item) => item.status === 'Запланировано'),
)
const tutorSubmittedHomework = computed(() =>
  homeworkStore.homework.filter((item) => item.status === 'Сданы'),
)
const tutorVerifiedReports = computed(() =>
  lessonsStore.reviewLessons.filter((item) => item.status === 'Проверено'),
)
const tutorVerifiedHours = computed(() => formatHours(sumReportMinutes(tutorVerifiedReports.value)))
const mentorTutors = computed(
  () =>
    new Set(lessonsStore.reviewLessons.map((item) => item.tutorId || item.tutor).filter(Boolean)),
)
const mentorAwaitingReviews = computed(() =>
  lessonsStore.reviewLessons.filter((item) => item.status === 'Ожидает проверки'),
)
const mentorVerifiedHours = computed(() =>
  formatHours(
    sumReportMinutes(lessonsStore.reviewLessons.filter((item) => item.status === 'Проверено')),
  ),
)
const mentorMissingMaterials = computed(() =>
  lessonsStore.reviewLessons.filter((item) => !item.video || !item.shots),
)
const shortPeople = (items) => {
  const names = items.slice(0, 2).map((item) => `${item.tutor} · ${item.student}`)
  if (items.length > 2) names.push(`и ещё ${items.length - 2}`)
  return names.join('; ')
}
const firstName = computed(() => auth.user?.name?.split(' ')[0] || 'друг')
const roleCopy = computed(() => {
  const text = {
    student: 'Сегодня отличный день, чтобы узнать что-то новое.',
    tutor: 'Здесь собраны ваши занятия, задания и сообщения учеников.',
    parent: 'Здесь появятся расписание, задания и прогресс ребёнка.',
    mentor: 'Здесь собраны занятия и отчёты вашей команды.',
    admin: 'Управляйте заявками и следите за работой проекта.',
  }
  return [`Здравствуйте, ${firstName.value}!`, text[role.value] || 'Добро пожаловать в Cogito.']
})
const parentChild = computed(
  () => auth.user?.childName || lessonsStore.lessons[0]?.student || 'Ребёнок',
)
const parentLesson = computed(
  () =>
    lessonsStore.lessons.find((item) => item.status === 'Запланировано') ||
    lessonsStore.lessons[0] ||
    null,
)
const parentTask = computed(
  () =>
    homeworkStore.homework.find((item) => item.status !== 'Проверено') ||
    homeworkStore.homework[0] ||
    null,
)
const adminStats = ref({
  students: 0,
  tutors: 0,
  lessons: 0,
  pendingApplications: 0,
  pendingReviews: 0,
  subjects: [],
})
const subjectTotal = computed(() => {
  let total = 0
  for (const subject of adminStats.value.subjects) total += subject.count
  return total
})
const today = new Intl.DateTimeFormat('ru-RU', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
}).format(new Date())
const todayLabel = `${today[0].toUpperCase()}${today.slice(1)}`
const subjectPercent = (count) =>
  subjectTotal.value ? Math.round((count / subjectTotal.value) * 100) : 0

async function openNotification(note) {
  try {
    if (!note.read) await messageStore.markRead(note.id)
    router.push(notificationPath(note, auth.roleKey))
  } catch (error) {
    messageStore.showToast(error.message, 'error')
  }
}

async function markAllNotificationsRead() {
  try {
    await messageStore.markAllRead()
  } catch (error) {
    messageStore.showToast(error.message, 'error')
  }
}

onMounted(async () => {
  if (auth.roleKey !== 'admin') return
  try {
    adminStats.value = await api('/admin/dashboard')
  } catch (error) {
    messageStore.showToast(error.message, 'error')
  }
})
</script>

<template>
  <div class="page dashboard">
    <section class="welcome card">
      <div>
        <span class="date">{{ todayLabel }}</span>
        <h1>{{ roleCopy[0] }}</h1>
        <p>{{ roleCopy[1] }}</p>
      </div>
      <div class="welcome-orbit">
        <span><Sparkles :size="24" /></span>
      </div>
    </section>

    <template v-if="role === 'student'">
      <div class="grid two-col main-grid">
        <section class="stack">
          <article class="card panel next-lesson">
            <div class="section-title">
              <h2>Ближайшее занятие</h2>
              <RouterLink to="/schedule" class="link">Расписание</RouterLink>
            </div>
            <template v-if="upcoming">
              <div class="lesson-line">
                <span class="subject-icon"><BookOpenCheck :size="20" /></span>
                <div>
                  <b>{{ upcoming.subject }}</b>
                  <small>Репетитор: {{ upcoming.tutor }}</small>
                </div>
                <strong>{{ upcoming.time || '—' }}</strong>
              </div>
              <div class="lesson-meta">
                <span>
                  <CalendarDays :size="14" />
                  {{ upcoming.date || 'Дата не указана' }}
                </span>
                <span>
                  <Clock3 :size="14" />
                  {{ upcoming.duration || 'Длительность не указана' }}
                </span>
              </div>
              <div class="lesson-actions">
                <RouterLink to="/schedule" class="soft-button">Подробнее</RouterLink>
                <a
                  v-if="upcoming.link"
                  :href="upcoming.link"
                  class="join-button"
                  target="_blank"
                  rel="noopener"
                >
                  Подключиться
                </a>
                <RouterLink v-else to="/schedule" class="soft-button">
                  Посмотреть занятие
                </RouterLink>
              </div>
            </template>
            <p v-else class="muted tiny empty-copy">Запланированных занятий пока нет.</p>
          </article>
        </section>
        <aside class="card panel notifications">
          <div class="section-title">
            <h2>Уведомления</h2>
            <button class="link" @click="markAllNotificationsRead">Прочитать</button>
          </div>
          <button
            v-for="note in messageStore.notifications.slice(0, 4)"
            :key="note.id"
            class="note"
            :class="{ unread: !note.read }"
            @click="openNotification(note)"
          >
            <span :class="note.tone">
              <CheckCircle2 v-if="note.tone === 'success'" :size="16" />
              <CalendarDays v-else :size="16" />
            </span>
            <p>
              <b>{{ note.title }}</b>
              <small>{{ note.text }}</small>
            </p>
          </button>
          <p v-if="!messageStore.notifications.length" class="muted tiny empty-copy">
            Новых уведомлений пока нет.
          </p>
          <RouterLink to="/notifications" class="link notification-link">
            Все уведомления
            <ArrowRight :size="14" />
          </RouterLink>
        </aside>
      </div>
      <div class="grid two-col below">
        <article class="card panel">
          <div class="section-title">
            <h2>Домашнее задание</h2>
            <RouterLink to="/homework" class="link">Все задания</RouterLink>
          </div>
          <div class="homework-mini">
            <span><FileCheck2 :size="19" /></span>
            <div>
              <b>{{ studentTask.title }}</b>
              <small>{{ studentTask.subject }} · До {{ studentTask.deadline }}</small>
            </div>
            <RouterLink to="/homework" class="outline-mini">Открыть</RouterLink>
          </div>
        </article>
        <article class="card panel">
          <div class="section-title">
            <h2>Мой прогресс</h2>
            <RouterLink to="/progress" class="link">Подробнее</RouterLink>
          </div>
          <div class="progress-summary">
            <span><FileCheck2 :size="19" /></span>
            <div>
              <b>
                {{
                  reviewedHomework.length
                    ? `Проверено работ: ${reviewedHomework.length}`
                    : 'Проверенных работ пока нет'
                }}
              </b>
              <small v-if="latestReviewedHomework">
                Последняя: {{ latestReviewedHomework.title }} ·
                {{ latestReviewedHomework.score || 'без оценки' }}
              </small>
              <small v-else>Статистика появится после первой проверки.</small>
            </div>
          </div>
        </article>
      </div>
    </template>

    <template v-else-if="role === 'tutor'">
      <section class="grid four-col">
        <StatCard
          label="Моих учеников"
          :value="students.length"
          :detail="tutorPlannedLessons.length ? `${tutorPlannedLessons.length} запланировано` : ''"
          icon="UsersRound"
        />
        <StatCard
          label="Подтверждённых часов"
          :value="tutorVerifiedHours"
          :detail="tutorVerifiedReports.length ? countText(tutorVerifiedReports.length, 'отчёт', 'отчёта', 'отчётов') : ''"
          icon="Clock3"
          tone="green"
        />
        <StatCard
          label="Заданий на проверке"
          :value="tutorSubmittedHomework.length"
          icon="BookOpenCheck"
          tone="orange"
        />
        <StatCard
          label="Запланировано занятий"
          :value="tutorPlannedLessons.length"
          icon="CalendarDays"
          tone="rose"
        />
      </section>
      <div class="grid two-col below">
        <section class="card panel">
          <div class="section-title">
            <h2>Запланированные занятия</h2>
            <RouterLink to="/schedule" class="link">Все занятия</RouterLink>
          </div>
          <div v-for="item in tutorPlannedLessons.slice(0, 2)" :key="item.id" class="agenda">
            <span class="agenda-time">{{ item.time ? item.time.slice(0, 5) : '—' }}</span>
            <span class="agenda-line"></span>
            <div>
              <b>{{ item.subject }} · {{ item.student }}</b>
              <small>{{ item.duration }} · {{ item.topic || 'Тема не указана' }}</small>
            </div>
            <RouterLink to="/schedule" class="outline-mini">Открыть</RouterLink>
          </div>
          <p v-if="!tutorPlannedLessons.length" class="muted tiny empty-copy">
            Запланированных занятий пока нет.
          </p>
        </section>
        <section class="card panel">
          <div class="section-title"><h2>Быстрые действия</h2></div>
          <div class="quick-actions">
            <RouterLink to="/schedule">
              <Plus :size="17" />
              Создать занятие
            </RouterLink>
            <RouterLink to="/homework">
              <BookOpenCheck :size="17" />
              Задать задание
            </RouterLink>
            <RouterLink to="/hours">
              <CheckCircle2 :size="17" />
              Отметить занятие
            </RouterLink>
            <RouterLink to="/chats">
              <MessageSquareText :size="17" />
              Написать ученику
            </RouterLink>
          </div>
        </section>
      </div>
      <section class="card panel below">
        <div class="section-title">
          <h2>Мои ученики</h2>
          <span class="muted tiny">{{ students.length }} в списке</span>
        </div>
        <div v-if="students.length" class="student-list">
          <article v-for="student in students" :key="student.id">
            <UserAvatar :initials="student.initials" :color="student.color" :size="42" />
            <div class="student-main">
              <b>{{ student.name }}</b>
              <small>{{ student.detail }}</small>
            </div>
            <div class="student-homework-progress">
              <small>
                {{
                  student.homeworkCount
                    ? `Проверено заданий: ${student.checkedHomework} из ${student.homeworkCount}`
                    : 'Заданий пока нет'
                }}
              </small>
              <ProgressBar :value="student.homeworkProgress" />
            </div>
            <RouterLink to="/progress" class="link">Прогресс</RouterLink>
          </article>
        </div>
        <p v-else class="muted tiny empty-copy">
          Ученики появятся здесь после создания занятия или задания.
        </p>
      </section>
    </template>

    <template v-else-if="role === 'parent' && parentHasData">
      <section class="child-summary card panel">
        <div class="child-top">
          <UserAvatar :initials="initialsFromName(parentChild)" color="#b39ddb" :size="54" />
          <div>
            <span class="eyebrow">Мой ребёнок</span>
            <h2>{{ parentChild }}</h2>
            <p>{{ parentLesson?.subject || 'Предмет пока не назначен' }}</p>
          </div>
          <RouterLink class="message-button" to="/chats">
            <MessageSquareText :size="16" />
            Написать репетитору
          </RouterLink>
        </div>
        <div class="grid two-col">
          <div>
            <small>Ближайшее занятие</small>
            <b>{{ parentLesson?.date || 'Пока нет' }} · {{ parentLesson?.time || '—' }}</b>
            <span>
              {{ parentLesson?.subject || 'Предмет не указан' }} ·
              {{ parentLesson?.tutor || 'Репетитор не назначен' }}
            </span>
          </div>
          <div>
            <small>Домашние задания</small>
            <b>{{ parentTask ? 'Есть задание в работе' : 'Новых заданий нет' }}</b>
            <span>Срок: {{ parentTask?.deadline || '—' }}</span>
          </div>
        </div>
      </section>
      <div class="grid two-col below">
        <article class="card panel">
          <div class="section-title">
            <h2>Результаты</h2>
            <RouterLink to="/progress" class="link">Подробно</RouterLink>
          </div>
          <div class="progress-summary">
            <span><FileCheck2 :size="19" /></span>
            <div>
              <b>
                {{
                  reviewedHomework.length
                    ? `Проверено работ: ${reviewedHomework.length}`
                    : 'Проверенных работ пока нет'
                }}
              </b>
              <small v-if="latestReviewedHomework">
                Последняя: {{ latestReviewedHomework.title }} ·
                {{ latestReviewedHomework.score || 'без оценки' }}
              </small>
              <small v-else>Оценки появятся после первой проверки задания.</small>
            </div>
          </div>
        </article>
        <article class="card panel">
          <div class="section-title">
            <h2>Комментарий репетитора</h2>
            <span class="tag">Пока нет</span>
          </div>
          <blockquote>
            «Комментарий репетитора появится здесь после проверки задания или занятия.»
          </blockquote>
          <div class="comment-author">
            <UserAvatar initials="РП" color="#9ebad5" :size="29" />
            <span>
              <b>{{ parentLesson?.tutor || 'Репетитор' }}</b>
              <small>Нет новых комментариев</small>
            </span>
          </div>
        </article>
      </div>
    </template>

    <template v-else-if="role === 'parent'">
      <section class="card panel">
        <h2>Ребёнок пока не привязан к вашему кабинету</h2>
        <p class="muted">
          Координатор Light Hearts добавит связь после проверки заявки. Тогда здесь появятся
          расписание, задания и прогресс.
        </p>
      </section>
    </template>

    <template v-else-if="role === 'mentor'">
      <section class="grid four-col">
        <StatCard label="Репетиторов в отчётах" :value="mentorTutors.size" icon="UsersRound" />
        <StatCard
          label="Ждут проверки"
          :value="mentorAwaitingReviews.length"
          icon="ClipboardCheck"
          tone="orange"
        />
        <StatCard
          label="Подтверждённых часов"
          :value="mentorVerifiedHours"
          icon="Clock3"
          tone="green"
        />
        <StatCard
          label="Без материалов"
          :value="mentorMissingMaterials.length"
          icon="CircleAlert"
          tone="rose"
        />
      </section>
      <div class="grid two-col below">
        <section class="card panel">
          <div class="section-title">
            <h2>Занятия на проверке</h2>
            <RouterLink to="/lessons-control" class="link">Открыть контроль</RouterLink>
          </div>
          <div
            v-for="item in lessonsStore.reviewLessons.slice(0, 3)"
            :key="item.id"
            class="review-mini"
          >
            <UserAvatar
              :initials="item.tutorInitials || initialsFromName(item.tutor)"
              :color="'#d9cdf5'"
              :size="34"
            />
            <div>
              <b>{{ item.tutor }} · {{ item.student }}</b>
              <small>{{ item.date }} · {{ item.topic || 'Тема не указана' }}</small>
            </div>
            <span
              :class="[
                'tag',
                item.status === 'Проверено'
                  ? 'success'
                  : item.status === 'Нужно исправить'
                    ? 'danger'
                    : 'warning',
              ]"
            >
              {{ item.status }}
            </span>
          </div>
          <p v-if="!lessonsStore.reviewLessons.length" class="muted tiny empty-copy">
            Отчётов от закреплённых репетиторов пока нет.
          </p>
        </section>
        <section class="card panel">
          <div class="section-title"><h2>Требуют внимания</h2></div>
          <div v-if="mentorMissingMaterials.length" class="issue">
            <span><FileCheck2 :size="18" /></span>
            <div>
              <b>Не все материалы приложены</b>
              <small>{{ shortPeople(mentorMissingMaterials) }}</small>
            </div>
            <RouterLink class="link" to="/lessons-control">Проверить</RouterLink>
          </div>
          <div v-if="mentorAwaitingReviews.length" class="issue">
            <span><Clock3 :size="18" /></span>
            <div>
              <b>Отчёты ждут проверки</b>
              <small>{{ shortPeople(mentorAwaitingReviews) }}</small>
            </div>
            <RouterLink class="link" to="/lessons-control">Открыть</RouterLink>
          </div>
          <p
            v-if="!mentorMissingMaterials.length && !mentorAwaitingReviews.length"
            class="muted tiny empty-copy"
          >
            Ничего не требует внимания.
          </p>
        </section>
      </div>
    </template>

    <template v-else>
      <section class="grid four-col">
        <StatCard label="Активных учеников" :value="adminStats.students" icon="GraduationCap" />
        <StatCard
          label="Активных репетиторов"
          :value="adminStats.tutors"
          icon="UsersRound"
          tone="green"
        />
        <StatCard
          label="Занятий в базе"
          :value="adminStats.lessons"
          icon="CalendarDays"
          tone="orange"
        />
        <StatCard
          label="Заявок на проверке"
          :value="adminStats.pendingApplications"
          icon="ClipboardCheck"
          tone="rose"
        />
      </section>
      <div class="grid two-col below">
        <article class="card panel">
          <div class="section-title">
            <h2>Состояние проекта</h2>
            <RouterLink class="link" to="/reports">Заявки</RouterLink>
          </div>
          <div class="activity">
            <span><ClipboardCheck :size="17" /></span>
            <p>
              Отчётов на проверке: <b>{{ adminStats.pendingReviews }}</b>
              <small>Данные из базы</small>
            </p>
          </div>
          <div class="activity">
            <span><CalendarDays :size="17" /></span>
            <p>
              Создано занятий: <b>{{ adminStats.lessons }}</b>
              <small>Всего за всё время</small>
            </p>
          </div>
        </article>
        <article class="card panel">
          <div class="section-title">
            <h2>Распределение по предметам</h2>
            <span class="muted tiny">По созданным занятиям</span>
          </div>
          <div v-if="adminStats.subjects.length" class="subjects">
            <div v-for="item in adminStats.subjects" :key="item.name">
              <span>{{ item.name }}</span>
              <ProgressBar :value="subjectPercent(item.count)" />
              <b>{{ item.count }}</b>
            </div>
          </div>
          <p v-else class="muted tiny empty-copy">
            Занятий пока нет — статистика появится после их создания.
          </p>
        </article>
      </div>
      <section class="card panel below">
        <div class="section-title">
          <h2>Последние уведомления</h2>
          <button class="link" @click="markAllNotificationsRead">Прочитать все</button>
        </div>
        <div v-if="messageStore.notifications.length">
          <button
            v-for="note in messageStore.notifications.slice(0, 4)"
            :key="note.id"
            class="activity notification-activity"
            :class="{ unread: !note.read }"
            @click="openNotification(note)"
          >
            <span><CheckCircle2 :size="17" /></span>
            <p>
              <b>{{ note.title }}</b>
              <small>{{ note.text }}</small>
            </p>
          </button>
        </div>
        <p v-else class="muted tiny empty-copy">Новых уведомлений пока нет.</p>
        <RouterLink to="/notifications" class="link notification-link">
          Все уведомления
          <ArrowRight :size="14" />
        </RouterLink>
      </section>
    </template>
  </div>
</template>

<style scoped src="../styles/dashboard.css"></style>
