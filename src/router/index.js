import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import LocalAdminSetupView from '../views/LocalAdminSetupView.vue'
import DashboardView from '../views/DashboardView.vue'
import ScheduleView from '../views/ScheduleView.vue'
import HomeworkView from '../views/HomeworkView.vue'
import GoalsView from '../views/GoalsView.vue'
import ProgressView from '../views/ProgressView.vue'
import ChatsView from '../views/ChatsView.vue'
import HoursView from '../views/HoursView.vue'
import LessonsControlView from '../views/LessonsControlView.vue'
import ReportsView from '../views/ReportsView.vue'
import ProfileView from '../views/ProfileView.vue'
import MainLayout from '../layouts/MainLayout.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/register', component: RegisterView, meta: { public: true } },
  { path: '/setup-admin', component: LocalAdminSetupView, meta: { public: true } },
  {
    path: '/', component: MainLayout,
    children: [
      { path: 'dashboard', component: DashboardView, meta: { title: 'Главная' } },
      { path: 'schedule', component: ScheduleView, meta: { title: 'Расписание' } },
      { path: 'homework', component: HomeworkView, meta: { title: 'Домашние задания' } },
      { path: 'goals', component: GoalsView, meta: { title: 'Цели' } },
      { path: 'progress', component: ProgressView, meta: { title: 'Прогресс' } },
      { path: 'chats', component: ChatsView, meta: { title: 'Чаты' } },
      { path: 'hours', component: HoursView, meta: { title: 'Мои часы', roles: ['tutor', 'mentor', 'admin'] } },
      { path: 'lessons-control', component: LessonsControlView, meta: { title: 'Контроль занятий', roles: ['mentor', 'admin'] } },
      { path: 'reports', component: ReportsView, meta: { title: 'Отчёты', roles: ['admin'] } },
      { path: 'profile', component: ProfileView, meta: { title: 'Профиль' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({ history: createWebHistory(), routes, scrollBehavior: () => ({ top: 0 }) })

router.beforeEach((to) => {
  const role = localStorage.getItem('cogito-role') || 'student'
  const authenticated = Boolean(localStorage.getItem('cogito-auth'))
  if (!to.meta.public && !authenticated) return '/login'
  if (to.meta.roles && !to.meta.roles.includes(role)) return '/dashboard'
  if (to.meta.public && authenticated && to.path === '/login') return '/dashboard'
})

export default router
