import { createRouter, createWebHistory } from 'vue-router'
import LoginView from './views/LoginView.vue'
import RegisterView from './views/RegisterView.vue'
import VerifyEmailView from './views/VerifyEmailView.vue'
import CheckEmailView from './views/CheckEmailView.vue'
import LocalAdminSetupView from './views/LocalAdminSetupView.vue'
import AdminResetView from './views/AdminResetView.vue'
import DashboardView from './views/DashboardView.vue'
import ScheduleView from './views/ScheduleView.vue'
import HomeworkView from './views/HomeworkView.vue'
import ProgressView from './views/ProgressView.vue'
import ChatsView from './views/ChatsView.vue'
import HoursView from './views/HoursView.vue'
import LessonsControlView from './views/LessonsControlView.vue'
import ReportsView from './views/ReportsView.vue'
import ProfileView from './views/ProfileView.vue'
import NotificationsView from './views/NotificationsView.vue'
import UsersView from './views/UsersView.vue'
import HelpView from './views/HelpView.vue'
import MainLayout from './Layout.vue'
import { useAuthStore } from './stores/auth'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/register', component: RegisterView, meta: { public: true } },
  { path: '/verify-email', component: VerifyEmailView, meta: { public: true } },
  { path: '/check-email', component: CheckEmailView, meta: { public: true } },
  { path: '/setup-admin', component: LocalAdminSetupView, meta: { public: true } },
  { path: '/admin-reset', component: AdminResetView, meta: { public: true } },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: 'dashboard', component: DashboardView, meta: { title: 'Главная' } },
      { path: 'schedule', component: ScheduleView, meta: { title: 'Расписание' } },
      { path: 'homework', component: HomeworkView, meta: { title: 'Домашние задания' } },
      { path: 'progress', component: ProgressView, meta: { title: 'Прогресс' } },
      { path: 'chats', component: ChatsView, meta: { title: 'Чаты' } },
      {
        path: 'hours',
        component: HoursView,
        meta: { title: 'Мои часы', roles: ['tutor', 'mentor', 'admin'] },
      },
      {
        path: 'lessons-control',
        component: LessonsControlView,
        meta: { title: 'Контроль занятий', roles: ['mentor', 'admin'] },
      },
      { path: 'reports', component: ReportsView, meta: { title: 'Отчёты', roles: ['admin'] } },
      { path: 'notifications', component: NotificationsView, meta: { title: 'Уведомления' } },
      { path: 'profile', component: ProfileView, meta: { title: 'Профиль' } },
      { path: 'users', component: UsersView, meta: { title: 'Участники', roles: ['admin'] } },
      { path: 'help', component: HelpView, meta: { title: 'Помощь' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !(await auth.restore())) return '/login'
  if (to.meta.roles && !to.meta.roles.includes(auth.roleKey)) return '/dashboard'
  if (to.path === '/login' && auth.isAuthenticated) return '/dashboard'
})

export default router
