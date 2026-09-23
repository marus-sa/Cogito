// Здесь остаются только подписи ролей и пункты меню.
// Учебные данные, чаты и уведомления загружаются с сервера.
export const roles = {
  student: { label: 'Ученик', name: 'Участник', initials: 'УЧ', color: '#b39ddb', description: 'Учусь и двигаюсь к своей цели' },
  tutor: { label: 'Репетитор', name: 'Участник', initials: 'УЧ', color: '#9ebad5', description: 'Помогаю ученикам расти' },
  parent: { label: 'Родитель', name: 'Участник', initials: 'УЧ', color: '#e2b9c7', description: 'Поддерживаю ребёнка на пути к цели' },
  mentor: { label: 'Наставник', name: 'Участник', initials: 'УЧ', color: '#a8cdbb', description: 'Сопровождаю команду репетиторов' },
  admin: { label: 'Администратор', name: 'Администратор', initials: 'АД', color: '#e6c48e', description: 'Развиваю проект Light Hearts' },
}

export const navigation = [
  { label: 'Главная', to: '/dashboard', icon: 'LayoutDashboard', roles: ['student', 'tutor', 'parent', 'mentor', 'admin'] },
  { label: 'Расписание', to: '/schedule', icon: 'CalendarDays', roles: ['student', 'tutor', 'parent', 'mentor', 'admin'] },
  { label: 'Домашние задания', to: '/homework', icon: 'BookOpenCheck', roles: ['student', 'tutor', 'parent', 'mentor', 'admin'] },
  { label: 'Цели', to: '/goals', icon: 'Target', roles: ['student', 'tutor', 'parent', 'mentor', 'admin'] },
  { label: 'Прогресс', to: '/progress', icon: 'ChartNoAxesCombined', roles: ['student', 'tutor', 'parent', 'mentor', 'admin'] },
  { label: 'Чаты', to: '/chats', icon: 'MessagesSquare', roles: ['student', 'tutor', 'parent', 'mentor', 'admin'] },
  { label: 'Мои часы', to: '/hours', icon: 'Clock3', roles: ['tutor', 'mentor', 'admin'] },
  { label: 'Контроль занятий', to: '/lessons-control', icon: 'ClipboardCheck', roles: ['mentor', 'admin'] },
  { label: 'Заявки', to: '/reports', icon: 'FileBarChart', roles: ['admin'] },
]
