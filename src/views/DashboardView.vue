<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRight, BookOpenCheck, CalendarDays, CheckCircle2, CircleAlert, ClipboardCheck, Clock3, FileCheck2, MessageSquareText, Plus, Sparkles, UsersRound } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useHomeworkStore } from '../stores/homework'
import { useLessonsStore } from '../stores/lessons'
import { useMessagesStore } from '../stores/messages'
import { api } from '../api'
import StatCard from '../components/StatCard.vue'
import ProgressBar from '../components/ProgressBar.vue'
import UserAvatar from '../components/UserAvatar.vue'

const auth = useAuthStore()
const homeworkStore = useHomeworkStore()
const lessonsStore = useLessonsStore()
const messageStore = useMessagesStore()
const role = computed(() => auth.roleKey)
const goal = computed(() => homeworkStore.goals[0] || { title: 'Добавьте первую цель', deadline: 'не указан', tasks: [] })
const goalProgress = computed(() => goal.value.tasks.length ? Math.round(goal.value.tasks.filter((item) => item.done).length / goal.value.tasks.length * 100) : 0)
const studentTask = computed(() => homeworkStore.homework.find((item) => item.status !== 'Проверено') || { title: 'Новых заданий пока нет', subject: '—', deadline: '—' })
const upcoming = computed(() => lessonsStore.lessons.find((item) => item.status === 'Запланировано') || null)
const reviewedHomework = computed(() => homeworkStore.homework.filter((item) => item.status === 'Проверено'))
const latestReviewedHomework = computed(() => reviewedHomework.value[0] || null)
const parentHasData = computed(() => homeworkStore.goals.length > 0 || homeworkStore.homework.length > 0 || lessonsStore.lessons.length > 0)
const initialsFromName = (name) => name.split(' ').filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'УЧ'
const durationInMinutes = (duration) => {
  const text = String(duration || '').replace(',', '.').toLowerCase()
  const hours = Number(text.match(/(\d+(?:\.\d+)?)\s*(?:ч|час)/)?.[1] || 0)
  const minutes = Number(text.match(/(\d+(?:\.\d+)?)\s*мин/)?.[1] || 0)
  return Math.round(hours * 60 + minutes)
}
const formatHours = (minutes) => {
  if (!minutes) return '0 ч'
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest ? `${hours} ч ${rest} мин` : `${hours} ч`
}
const students = computed(() => {
  const names = [...new Set([
    ...lessonsStore.lessons.map((lesson) => lesson.student),
    ...homeworkStore.homework.map((item) => item.student),
  ].filter(Boolean))]
  const colors = ['#b39ddb', '#9ebad5', '#a8cdbb', '#e2b9c7']
  return names.map((name, index) => {
    const lesson = lessonsStore.lessons.find((item) => item.student === name)
    const homework = homeworkStore.homework.filter((item) => item.student === name)
    const checked = homework.filter((item) => item.status === 'Проверено').length
    return {
      id: name,
      name,
      initials: initialsFromName(name),
      detail: lesson?.subject || homework[0]?.subject || 'Предмет не указан',
      color: colors[index % colors.length],
      homeworkCount: homework.length,
      checkedHomework: checked,
      homeworkProgress: homework.length ? Math.round(checked / homework.length * 100) : 0,
    }
  })
})
const tutorPlannedLessons = computed(() => lessonsStore.lessons.filter((item) => item.status === 'Запланировано'))
const tutorSubmittedHomework = computed(() => homeworkStore.homework.filter((item) => item.status === 'Сданы'))
const tutorVerifiedReports = computed(() => lessonsStore.reviewLessons.filter((item) => item.status === 'Проверено'))
const tutorVerifiedHours = computed(() => formatHours(tutorVerifiedReports.value.reduce((total, item) => total + durationInMinutes(item.duration), 0)))
const mentorTutors = computed(() => new Set(lessonsStore.reviewLessons.map((item) => item.tutorId || item.tutor).filter(Boolean)))
const mentorAwaitingReviews = computed(() => lessonsStore.reviewLessons.filter((item) => item.status === 'Ожидает проверки'))
const mentorVerifiedHours = computed(() => formatHours(lessonsStore.reviewLessons
  .filter((item) => item.status === 'Проверено')
  .reduce((total, item) => total + durationInMinutes(item.duration), 0)))
const mentorMissingMaterials = computed(() => lessonsStore.reviewLessons.filter((item) => !item.video || !item.shots))
const shortPeople = (items) => {
  const names = items.slice(0, 2).map((item) => `${item.tutor} · ${item.student}`)
  if (items.length > 2) names.push(`и ещё ${items.length - 2}`)
  return names.join('; ')
}
const firstName = computed(() => auth.user?.name?.split(' ')[0] || 'друг')
const roleCopy = computed(() => {
  const text = {
    student: 'Сегодня отличный день, чтобы сделать небольшой шаг к своей цели.',
    tutor: 'Здесь собраны ваши занятия, задания и сообщения учеников.',
    parent: 'Здесь появятся расписание, задания и прогресс ребёнка.',
    mentor: 'Здесь собраны занятия и отчёты вашей команды.',
    admin: 'Управляйте заявками и следите за работой проекта.',
  }
  return [`Здравствуйте, ${firstName.value}!`, text[role.value] || 'Добро пожаловать в Cogito.']
})
const parentChild = computed(() => auth.user?.childName || lessonsStore.lessons[0]?.student || 'Ребёнок')
const parentLesson = computed(() => lessonsStore.lessons.find((item) => item.status === 'Запланировано') || lessonsStore.lessons[0] || null)
const parentTask = computed(() => homeworkStore.homework.find((item) => item.status !== 'Проверено') || homeworkStore.homework[0] || null)
const parentGoal = computed(() => homeworkStore.goals[0] || null)
const adminStats = ref({ students: 0, tutors: 0, lessons: 0, pendingApplications: 0, pendingReviews: 0, subjects: [] })
const subjectTotal = computed(() => adminStats.value.subjects.reduce((total, item) => total + item.count, 0))
const today = new Intl.DateTimeFormat('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())
const todayLabel = `${today[0].toUpperCase()}${today.slice(1)}`
const subjectPercent = (count) => subjectTotal.value ? Math.round(count / subjectTotal.value * 100) : 0

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
    <section class="welcome card"><div><span class="date">{{ todayLabel }}</span><h1>{{ roleCopy[0] }}</h1><p>{{ roleCopy[1] }}</p></div><div class="welcome-orbit"><span><Sparkles :size="24" /></span></div></section>

    <template v-if="role === 'student'">
      <div class="grid two-col main-grid"><section class="stack"><article class="card panel goal-card"><div class="section-title"><div><span class="eyebrow">Моя цель</span><h2>{{ goal.title }}</h2></div><RouterLink to="/goals" class="link">Все цели <ArrowRight :size="14" /></RouterLink></div><ProgressBar :value="goalProgress" /><div class="goal-details"><span>Срок: <b>{{ goal.deadline }}</b></span><span><b>{{ goal.tasks.filter((item) => item.done).length }}</b> из {{ goal.tasks.length }} подзадач</span></div></article>
        <article class="card panel next-lesson"><div class="section-title"><h2>Ближайшее занятие</h2><RouterLink to="/schedule" class="link">Расписание</RouterLink></div><template v-if="upcoming"><div class="lesson-line"><span class="subject-icon"><BookOpenCheck :size="20" /></span><div><b>{{ upcoming.subject }}</b><small>с {{ upcoming.tutor }}</small></div><strong>{{ upcoming.time || '—' }}</strong></div><div class="lesson-meta"><span><CalendarDays :size="14" /> {{ upcoming.date || 'Дата не указана' }}</span><span><Clock3 :size="14" /> {{ upcoming.duration || 'Длительность не указана' }}</span></div><div class="lesson-actions"><RouterLink to="/schedule" class="soft-button">Подробнее</RouterLink><a v-if="upcoming.link" :href="upcoming.link" class="join-button" target="_blank">Подключиться</a><span v-else class="soft-button">Ссылка появится позже</span></div></template><p v-else class="muted tiny empty-copy">Запланированных занятий пока нет.</p></article>
      </section><aside class="card panel notifications"><div class="section-title"><h2>Уведомления</h2><button class="link" @click="messageStore.markAllRead()">Прочитать</button></div><button v-for="note in messageStore.notifications" :key="note.id" class="note" :class="{ unread: !note.read }" @click="note.read = true"><span :class="note.tone"><CheckCircle2 v-if="note.tone === 'success'" :size="16" /><CalendarDays v-else :size="16" /></span><p><b>{{ note.title }}</b><small>{{ note.text }}</small></p></button></aside></div>
      <div class="grid two-col below"><article class="card panel"><div class="section-title"><h2>Домашнее задание</h2><RouterLink to="/homework" class="link">Все задания</RouterLink></div><div class="homework-mini"><span><FileCheck2 :size="19" /></span><div><b>{{ studentTask.title }}</b><small>{{ studentTask.subject }} · До {{ studentTask.deadline }}</small></div><RouterLink to="/homework" class="outline-mini">Открыть</RouterLink></div></article><article class="card panel"><div class="section-title"><h2>Мой прогресс</h2><RouterLink to="/progress" class="link">Подробнее</RouterLink></div><div class="progress-summary"><span><FileCheck2 :size="19" /></span><div><b>{{ reviewedHomework.length ? `Проверено работ: ${reviewedHomework.length}` : 'Проверенных работ пока нет' }}</b><small v-if="latestReviewedHomework">Последняя: {{ latestReviewedHomework.title }} · {{ latestReviewedHomework.score || 'без оценки' }}</small><small v-else>Статистика появится после первой проверки.</small></div></div></article></div>
    </template>

    <template v-else-if="role === 'tutor'">
      <section class="grid four-col"><StatCard label="Моих учеников" :value="students.length" :detail="tutorPlannedLessons.length ? `${tutorPlannedLessons.length} запланировано` : ''" icon="UsersRound" /><StatCard label="Подтверждённых часов" :value="tutorVerifiedHours" :detail="tutorVerifiedReports.length ? `${tutorVerifiedReports.length} отчётов` : ''" icon="Clock3" tone="green" /><StatCard label="Заданий на проверке" :value="tutorSubmittedHomework.length" icon="BookOpenCheck" tone="orange" /><StatCard label="Запланировано занятий" :value="tutorPlannedLessons.length" icon="CalendarDays" tone="rose" /></section>
      <div class="grid two-col below"><section class="card panel"><div class="section-title"><h2>Запланированные занятия</h2><RouterLink to="/schedule" class="link">Все занятия</RouterLink></div><div v-for="item in tutorPlannedLessons.slice(0, 2)" :key="item.id" class="agenda"><span class="agenda-time">{{ item.time ? item.time.slice(0, 5) : '—' }}</span><span class="agenda-line"></span><div><b>{{ item.subject }} · {{ item.student }}</b><small>{{ item.duration }} · {{ item.topic || 'Тема не указана' }}</small></div><RouterLink to="/schedule" class="outline-mini">Открыть</RouterLink></div><p v-if="!tutorPlannedLessons.length" class="muted tiny empty-copy">Запланированных занятий пока нет.</p></section><section class="card panel"><div class="section-title"><h2>Быстрые действия</h2></div><div class="quick-actions"><RouterLink to="/schedule"><Plus :size="17" /> Создать занятие</RouterLink><RouterLink to="/homework"><BookOpenCheck :size="17" /> Задать задание</RouterLink><RouterLink to="/hours"><CheckCircle2 :size="17" /> Отметить занятие</RouterLink><RouterLink to="/chats"><MessageSquareText :size="17" /> Написать ученику</RouterLink></div></section></div>
      <section class="card panel below"><div class="section-title"><h2>Мои ученики</h2><span class="muted tiny">{{ students.length }} в списке</span></div><div v-if="students.length" class="student-list"><article v-for="student in students" :key="student.id"><UserAvatar :initials="student.initials" :color="student.color" :size="42" /><div class="student-main"><b>{{ student.name }}</b><small>{{ student.detail }}</small></div><div class="student-goal"><small>{{ student.homeworkCount ? `Проверено заданий: ${student.checkedHomework} из ${student.homeworkCount}` : 'Заданий пока нет' }}</small><ProgressBar :value="student.homeworkProgress" /></div><RouterLink to="/progress" class="link">Прогресс</RouterLink></article></div><p v-else class="muted tiny empty-copy">Ученики появятся здесь после создания занятия или задания.</p></section>
    </template>

    <template v-else-if="role === 'parent' && parentHasData">
      <section class="child-summary card panel"><div class="child-top"><UserAvatar :initials="initialsFromName(parentChild)" color="#b39ddb" :size="54" /><div><span class="eyebrow">Мой ребёнок</span><h2>{{ parentChild }}</h2><p>{{ parentLesson?.subject || 'Предмет пока не назначен' }}</p></div><RouterLink class="message-button" to="/chats"><MessageSquareText :size="16" /> Написать репетитору</RouterLink></div><div class="grid three-col"><div><small>Текущая цель</small><b>{{ parentGoal?.title || 'Цель пока не добавлена' }}</b><ProgressBar :value="parentGoal ? goalProgress : 0" /></div><div><small>Ближайшее занятие</small><b>{{ parentLesson?.date || 'Пока нет' }} · {{ parentLesson?.time || '—' }}</b><span>{{ parentLesson?.subject || 'Предмет не указан' }} · {{ parentLesson?.tutor || 'Репетитор не назначен' }}</span></div><div><small>Домашние задания</small><b>{{ parentTask ? 'Есть задание в работе' : 'Новых заданий нет' }}</b><span>Срок: {{ parentTask?.deadline || '—' }}</span></div></div></section><div class="grid two-col below"><article class="card panel"><div class="section-title"><h2>Результаты</h2><RouterLink to="/progress" class="link">Подробно</RouterLink></div><div class="progress-summary"><span><FileCheck2 :size="19" /></span><div><b>{{ reviewedHomework.length ? `Проверено работ: ${reviewedHomework.length}` : 'Проверенных работ пока нет' }}</b><small v-if="latestReviewedHomework">Последняя: {{ latestReviewedHomework.title }} · {{ latestReviewedHomework.score || 'без оценки' }}</small><small v-else>Оценки появятся после первой проверки задания.</small></div></div></article><article class="card panel"><div class="section-title"><h2>Комментарий репетитора</h2><span class="tag">Пока нет</span></div><blockquote>«Комментарий репетитора появится здесь после проверки задания или занятия.»</blockquote><div class="comment-author"><UserAvatar initials="РП" color="#9ebad5" :size="29" /><span><b>{{ parentLesson?.tutor || 'Репетитор' }}</b><small>Нет новых комментариев</small></span></div></article></div>
    </template>

    <template v-else-if="role === 'parent'">
      <section class="card panel"><h2>Ребёнок пока не привязан к вашему кабинету</h2><p class="muted">Координатор Light Hearts добавит связь после проверки заявки. Тогда здесь появятся расписание, задания и прогресс.</p></section>
    </template>

    <template v-else-if="role === 'mentor'">
      <section class="grid four-col"><StatCard label="Репетиторов в отчётах" :value="mentorTutors.size" icon="UsersRound" /><StatCard label="Ждут проверки" :value="mentorAwaitingReviews.length" icon="ClipboardCheck" tone="orange" /><StatCard label="Подтверждённых часов" :value="mentorVerifiedHours" icon="Clock3" tone="green" /><StatCard label="Без материалов" :value="mentorMissingMaterials.length" icon="CircleAlert" tone="rose" /></section><div class="grid two-col below"><section class="card panel"><div class="section-title"><h2>Занятия на проверке</h2><RouterLink to="/lessons-control" class="link">Открыть контроль</RouterLink></div><div v-for="item in lessonsStore.reviewLessons.slice(0,3)" :key="item.id" class="review-mini"><UserAvatar :initials="item.tutorInitials || initialsFromName(item.tutor)" :color="'#d9cdf5'" :size="34" /><div><b>{{ item.tutor }} · {{ item.student }}</b><small>{{ item.date }} · {{ item.topic || 'Тема не указана' }}</small></div><span :class="['tag', item.status === 'Проверено' ? 'success' : item.status === 'Нужно исправить' ? 'danger' : 'warning']">{{ item.status }}</span></div><p v-if="!lessonsStore.reviewLessons.length" class="muted tiny empty-copy">Отчётов от закреплённых репетиторов пока нет.</p></section><section class="card panel"><div class="section-title"><h2>Требуют внимания</h2></div><div v-if="mentorMissingMaterials.length" class="issue"><span><FileCheck2 :size="18" /></span><div><b>Не все материалы приложены</b><small>{{ shortPeople(mentorMissingMaterials) }}</small></div><RouterLink class="link" to="/lessons-control">Проверить</RouterLink></div><div v-if="mentorAwaitingReviews.length" class="issue"><span><Clock3 :size="18" /></span><div><b>Отчёты ждут проверки</b><small>{{ shortPeople(mentorAwaitingReviews) }}</small></div><RouterLink class="link" to="/lessons-control">Открыть</RouterLink></div><p v-if="!mentorMissingMaterials.length && !mentorAwaitingReviews.length" class="muted tiny empty-copy">Ничего не требует внимания.</p></section></div>
    </template>

    <template v-else>
      <section class="grid four-col"><StatCard label="Активных учеников" :value="adminStats.students" icon="GraduationCap" /><StatCard label="Активных репетиторов" :value="adminStats.tutors" icon="UsersRound" tone="green" /><StatCard label="Занятий в базе" :value="adminStats.lessons" icon="CalendarDays" tone="orange" /><StatCard label="Заявок ожидают" :value="adminStats.pendingApplications" icon="ClipboardCheck" tone="rose" /></section>
      <div class="grid two-col below"><article class="card panel"><div class="section-title"><h2>Состояние проекта</h2><RouterLink class="link" to="/reports">Заявки</RouterLink></div><div class="activity"><span><ClipboardCheck :size="17" /></span><p><b>{{ adminStats.pendingReviews }}</b> отчётов о занятиях ждут проверки <small>Данные из базы</small></p></div><div class="activity"><span><CalendarDays :size="17" /></span><p><b>{{ adminStats.lessons }}</b> занятий создано в системе <small>Всего за всё время</small></p></div></article><article class="card panel"><div class="section-title"><h2>Распределение по предметам</h2><span class="muted tiny">По созданным занятиям</span></div><div v-if="adminStats.subjects.length" class="subjects"><div v-for="item in adminStats.subjects" :key="item.name"><span>{{ item.name }}</span><ProgressBar :value="subjectPercent(item.count)" /><b>{{ item.count }}</b></div></div><p v-else class="muted tiny empty-copy">Занятий пока нет — статистика появится после их создания.</p></article></div>
      <section class="card panel below"><div class="section-title"><h2>Последние уведомления</h2><button class="link" @click="messageStore.markAllRead()">Прочитать все</button></div><div v-if="messageStore.notifications.length"><div v-for="note in messageStore.notifications.slice(0, 4)" :key="note.id" class="activity"><span><CheckCircle2 :size="17" /></span><p><b>{{ note.title }}</b> <small>{{ note.text }}</small></p></div></div><p v-else class="muted tiny empty-copy">Новых уведомлений пока нет.</p></section>
    </template>
  </div>
</template>

<style scoped>
.dashboard{display:grid;gap:19px}.welcome{position:relative;display:flex;align-items:center;justify-content:space-between;min-height:142px;padding:24px 28px;overflow:hidden;background:linear-gradient(105deg,#fff,#f5f0ff)}.welcome::after{position:absolute;right:57px;bottom:-42px;width:160px;height:160px;content:'';background:#e4d9fb;border-radius:50%}.date{color:var(--primary-dark);font-size:11px;font-weight:800}.welcome h1{margin:5px 0 4px;font-size:27px;letter-spacing:-.8px}.welcome p{margin:0;color:var(--text-secondary);font-size:12px}.welcome-orbit{position:relative;z-index:1;display:grid;place-items:center;width:70px;height:70px;margin-right:30px;border:1px solid #d9cceF;border-radius:50%;background:rgba(255,255,255,.7)}.welcome-orbit::after{position:absolute;inset:10px;border-radius:50%;content:'';background:#e3d8f8}.welcome-orbit span{z-index:1;color:var(--primary-dark)}.main-grid{align-items:stretch}.goal-card .section-title h2{max-width:430px;margin-top:6px;font-size:17px}.eyebrow{display:inline-block;color:var(--primary-dark);font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.06em}.goal-details{display:flex;justify-content:space-between;gap:10px;margin-top:13px;color:var(--text-secondary);font-size:11px}.goal-details b{color:var(--text-main)}.section-title :deep(.link){display:inline-flex;align-items:center;gap:3px}.next-lesson{background:linear-gradient(140deg,#fff,#fbf9ff)}.lesson-line{display:flex;align-items:center;gap:11px;margin:17px 0 13px}.subject-icon{display:grid;place-items:center;width:43px;height:43px;color:var(--primary-dark);background:#ede6fc;border-radius:13px}.lesson-line b,.lesson-line small{display:block}.lesson-line b{font-size:14px}.lesson-line small{margin-top:3px;color:var(--text-secondary);font-size:11px}.lesson-line strong{margin-left:auto;color:var(--primary-dark);font-size:13px}.lesson-meta{display:flex;gap:14px;color:var(--text-secondary);font-size:11px}.lesson-meta span{display:flex;align-items:center;gap:4px}.lesson-actions{display:flex;gap:9px;margin-top:17px}.soft-button,.join-button{display:inline-flex;align-items:center;justify-content:center;min-height:35px;padding:0 12px;border-radius:10px;font-size:11px;font-weight:800}.soft-button{color:var(--primary-dark);background:var(--primary-extra-light)}.join-button{color:#fff;background:var(--primary)}.notifications{padding-bottom:11px}.note{display:flex;gap:9px;width:100%;padding:10px 0;border:0;border-bottom:1px solid #f0edf5;color:var(--text-main);background:transparent;text-align:left}.note:last-child{border-bottom:0}.note>span{display:grid;place-items:center;width:29px;height:29px;border-radius:9px}.note>span.success{color:#4a8965;background:#e8f5ee}.note>span.primary{color:var(--primary-dark);background:var(--primary-extra-light)}.note>span.warning{color:#a77a32;background:#fcf4e5}.note p{margin:0}.note b,.note small{display:block}.note b{font-size:11px}.note small{margin-top:2px;color:var(--text-secondary);font-size:10px;line-height:1.35}.note.unread b::after{display:inline-block;width:5px;height:5px;margin-left:5px;vertical-align:middle;content:'';background:var(--primary);border-radius:50%}.below{margin-top:1px}.homework-mini{display:flex;align-items:center;gap:11px;padding-top:3px}.homework-mini>span{display:grid;place-items:center;width:39px;height:39px;color:#a77a32;background:#fcf4e5;border-radius:12px}.homework-mini div{min-width:0;flex:1}.homework-mini b,.homework-mini small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.homework-mini b{font-size:12px}.homework-mini small{margin-top:3px;color:var(--text-secondary);font-size:10px}.outline-mini{display:inline-flex;align-items:center;justify-content:center;min-height:31px;padding:0 9px;border:1px solid var(--border);border-radius:9px;color:var(--primary-dark);font-size:10px;font-weight:800}.outline-mini:hover{background:var(--primary-extra-light)}.agenda{display:flex;align-items:center;gap:10px;padding:13px 0;border-top:1px solid var(--border)}.agenda-time{color:var(--primary-dark);font-size:11px;font-weight:800}.agenda-line{width:3px;height:35px;background:#d7c9f5;border-radius:3px}.agenda div{min-width:0;flex:1}.agenda b,.agenda small{display:block}.agenda b{font-size:12px}.agenda small{margin-top:3px;color:var(--text-secondary);font-size:10px}.quick-actions{display:grid;grid-template-columns:1fr 1fr;gap:9px}.quick-actions a{display:flex;align-items:center;gap:7px;min-height:48px;padding:0 10px;color:#62586f;background:#faf8fc;border-radius:12px;font-size:11px;font-weight:800}.quick-actions a:hover{color:var(--primary-dark);background:var(--primary-extra-light)}.student-list{display:grid}.student-list article{display:flex;align-items:center;gap:10px;padding:12px 0;border-top:1px solid var(--border)}.student-main{min-width:120px}.student-main b,.student-main small{display:block}.student-main b{font-size:12px}.student-main small{margin-top:2px;color:var(--text-secondary);font-size:10px}.student-goal{width:min(230px,25vw);margin-left:auto}.student-goal small{display:block;margin-bottom:5px;color:var(--text-secondary);font-size:10px}.child-summary{padding:25px}.child-top{display:flex;align-items:center;gap:12px;margin-bottom:26px}.child-top h2{margin:5px 0 2px;font-size:19px}.child-top p{margin:0;color:var(--text-secondary);font-size:11px}.message-button{display:inline-flex;align-items:center;gap:7px;margin-left:auto;min-height:37px;padding:0 11px;border:1px solid var(--border);border-radius:10px;color:var(--primary-dark);background:#fff;font-size:11px;font-weight:800}.message-button:hover{background:var(--primary-extra-light)}.child-summary .three-col>div{display:grid;gap:5px}.child-summary .three-col small{color:var(--text-secondary);font-size:10px}.child-summary .three-col b{font-size:12px}.child-summary .three-col span{color:var(--text-secondary);font-size:10px}.chart-comment{margin:8px 10px 0;color:var(--text-secondary);font-size:10px}blockquote{margin:16px 0 15px;padding:0 0 0 14px;border-left:3px solid #d9cdf5;color:#5d5369;font-size:12px;line-height:1.7}.comment-author{display:flex;align-items:center;gap:7px}.comment-author b,.comment-author small{display:block}.comment-author b{font-size:10px}.comment-author small{margin-top:2px;color:var(--text-secondary);font-size:9px}.review-mini,.issue{display:flex;align-items:center;gap:9px;padding:12px 0;border-top:1px solid var(--border)}.review-mini>div{min-width:0;flex:1}.review-mini b,.review-mini small,.issue b,.issue small{display:block}.review-mini b,.issue b{font-size:11px}.review-mini small,.issue small{margin-top:3px;color:var(--text-secondary);font-size:10px}.issue>span{display:grid;place-items:center;width:34px;height:34px;color:#aa6b6b;background:#faecec;border-radius:10px}.issue>div{min-width:0;flex:1}.bar-legend{display:flex;justify-content:space-between;margin:17px 10px 0;color:var(--text-secondary);font-size:10px}.bar-legend i{display:inline-block;width:8px;height:8px;background:var(--primary);border-radius:50%}.subjects{display:grid;gap:16px;padding:13px 0}.subjects>div{display:grid;grid-template-columns:90px 1fr 28px;align-items:center;gap:8px}.subjects span,.subjects b{font-size:10px}.subjects b{text-align:right;color:var(--text-secondary)}.activity{display:flex;align-items:center;gap:10px;padding:10px 0;border-top:1px solid var(--border)}.activity span{display:grid;place-items:center;width:30px;height:30px;color:#4f896a;background:#e8f5ee;border-radius:9px}.activity:nth-child(3) span{color:var(--primary-dark);background:var(--primary-extra-light)}.activity p{margin:0;font-size:11px}.activity small{display:block;margin-top:3px;color:var(--text-secondary);font-size:10px}
.progress-summary{display:flex;align-items:center;gap:11px;padding:17px 0 5px}.progress-summary>span{display:grid;place-items:center;width:40px;height:40px;color:#4a8965;background:#e8f5ee;border-radius:12px}.progress-summary b,.progress-summary small{display:block}.progress-summary b{font-size:12px}.progress-summary small{margin-top:4px;color:var(--text-secondary);font-size:10px}
@media(max-width:720px){.welcome{min-height:128px;padding:20px}.welcome::after{right:-35px}.welcome-orbit{display:none}.goal-details{display:block;line-height:1.9}.lesson-actions>*{flex:1}.student-list article{flex-wrap:wrap}.student-goal{order:3;width:100%;margin-left:52px}.child-top{align-items:flex-start;flex-wrap:wrap}.message-button{margin:3px 0 0 66px}.child-summary .three-col{gap:18px}.subjects>div{grid-template-columns:82px 1fr 25px}.quick-actions{grid-template-columns:1fr}.bar-legend{display:block;line-height:1.8}}
</style>
