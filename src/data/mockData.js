export const roles = {
  student: { label: 'Ученик', name: 'Анна Смирнова', initials: 'АС', color: '#b39ddb', description: 'Учусь и двигаюсь к своей цели' },
  tutor: { label: 'Репетитор', name: 'Мария Иванова', initials: 'МИ', color: '#9ebad5', description: 'Помогаю ученикам расти' },
  parent: { label: 'Родитель', name: 'Елена Смирнова', initials: 'ЕС', color: '#e2b9c7', description: 'Поддерживаю Анну на пути к цели' },
  mentor: { label: 'Наставник', name: 'Алексей Петров', initials: 'АП', color: '#a8cdbb', description: 'Сопровождаю команду репетиторов' },
  admin: { label: 'Администратор', name: 'Софья Орлова', initials: 'СО', color: '#e6c48e', description: 'Развиваю проект Light Hearts' },
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
  { label: 'Отчёты', to: '/reports', icon: 'FileBarChart', roles: ['admin'] },
]

export const users = [
  { id: 1, name: 'Анна Смирнова', initials: 'АС', role: 'Ученик', detail: '7 класс · математика', color: '#b39ddb' },
  { id: 2, name: 'Мария Иванова', initials: 'МИ', role: 'Репетитор', detail: '11 класс · математика', color: '#9ebad5' },
  { id: 3, name: 'Елена Смирнова', initials: 'ЕС', role: 'Родитель', detail: 'Мама Анны', color: '#e2b9c7' },
  { id: 4, name: 'Алексей Петров', initials: 'АП', role: 'Наставник', detail: 'Координатор', color: '#a8cdbb' },
  { id: 5, name: 'Софья Орлова', initials: 'СО', role: 'Администратор', detail: 'Light Hearts', color: '#e6c48e' },
  { id: 6, name: 'Данил Мельников', initials: 'ДМ', role: 'Ученик', detail: '8 класс · информатика', color: '#b6d4cc' },
  { id: 7, name: 'Полина Кравцова', initials: 'ПК', role: 'Ученик', detail: '7 класс · математика', color: '#e2b9c7' },
]

export const initialLessons = [
  { id: 1, subject: 'Математика', student: 'Анна Смирнова', tutor: 'Мария Иванова', date: 'Сегодня, 18:00', time: '18:00–19:00', duration: '60 мин', status: 'Запланировано', link: 'https://telemost.yandex.ru', topic: 'Линейные уравнения', materials: true },
  { id: 2, subject: 'Информатика', student: 'Данил Мельников', tutor: 'Мария Иванова', date: 'Завтра, 16:30', time: '16:30–17:30', duration: '60 мин', status: 'Запланировано', link: 'https://telemost.yandex.ru', topic: 'Алгоритмы', materials: false },
  { id: 3, subject: 'Математика', student: 'Полина Кравцова', tutor: 'Мария Иванова', date: '30 июля', time: '17:00–18:00', duration: '60 мин', status: 'Проведено', link: '', topic: 'Дроби', materials: true },
  { id: 4, subject: 'Математика', student: 'Анна Смирнова', tutor: 'Мария Иванова', date: '28 июля', time: '18:00–19:00', duration: '60 мин', status: 'Проведено', link: '', topic: 'Диагностическая работа', materials: true },
]

export const initialHomework = [
  { id: 1, title: 'Линейные уравнения: тренировка', subject: 'Математика', student: 'Анна Смирнова', tutor: 'Мария Иванова', issued: '29 июля', deadline: '3 августа', status: 'В работе', attachment: 'Карточка с заданиями.pdf', score: null, description: 'Решите задания 1–12. Покажите ход решения в тетради.' },
  { id: 2, title: 'Диагностическая работа', subject: 'Математика', student: 'Анна Смирнова', tutor: 'Мария Иванова', issued: '22 июля', deadline: '28 июля', status: 'Проверено', attachment: 'Диагностика.pdf', score: '8 / 10', description: 'Повторить действия с дробями перед следующим занятием.' },
  { id: 3, title: 'Основы алгоритмов', subject: 'Информатика', student: 'Данил Мельников', tutor: 'Мария Иванова', issued: '28 июля', deadline: '2 августа', status: 'Сданы', attachment: 'Практика.docx', score: null, description: 'Составить два алгоритма в виде блок-схемы.' },
  { id: 4, title: 'Задачи на проценты', subject: 'Математика', student: 'Полина Кравцова', tutor: 'Мария Иванова', issued: '15 июля', deadline: '23 июля', status: 'Просрочено', attachment: '', score: null, description: 'Решить шесть задач из рабочей тетради.' },
]

export const initialGoals = [
  {
    id: 1,
    title: 'Повысить оценку по математике с 3 до 4',
    subject: 'Математика',
    deadline: '25 августа',
    tutor: 'Мария Иванова',
    description: 'Уверенно решать базовые задания и выйти на твёрдую четвёрку к концу четверти.',
    tasks: [
      { id: 1, label: 'Повторить дроби', done: true },
      { id: 2, label: 'Решить диагностическую работу', done: true },
      { id: 3, label: 'Изучить линейные уравнения', done: false },
      { id: 4, label: 'Выполнить итоговый тест', done: false },
    ],
  },
]

export const dialogs = [
  { id: 1, name: 'Мария Иванова', initials: 'МИ', role: 'Репетитор', color: '#9ebad5', last: 'Отлично, разберём на занятии!', time: '12:40', unread: 2, online: true },
  { id: 2, name: 'Елена Смирнова', initials: 'ЕС', role: 'Родитель', color: '#e2b9c7', last: 'Спасибо за обратную связь', time: 'Вчера', unread: 0, online: false },
  { id: 3, name: 'Алексей Петров', initials: 'АП', role: 'Наставник', color: '#a8cdbb', last: 'Не забудьте приложить запись', time: 'Пн', unread: 0, online: true },
]

export const initialMessages = [
  { id: 1, dialogId: 1, sender: 'them', text: 'Анна, добрый день! Посмотрела твою работу — есть несколько мест, которые разберём на занятии.', time: '12:34', read: true },
  { id: 2, dialogId: 1, sender: 'me', text: 'Спасибо! Я попробую ещё раз решить задачи 7 и 8.', time: '12:37', read: true },
  { id: 3, dialogId: 1, sender: 'them', text: 'Отлично, разберём на занятии! Можешь прислать фото, если что-то не получается.', time: '12:40', read: true },
]

export const notifications = [
  { id: 1, icon: 'CheckCircle2', tone: 'success', title: 'Работа проверена', text: 'Мария Иванова проверила «Диагностическую работу».', time: '20 минут назад', read: false },
  { id: 2, icon: 'CalendarClock', tone: 'primary', title: 'Занятие завтра', text: 'Математика начнётся завтра в 18:00.', time: '2 часа назад', read: false },
  { id: 3, icon: 'MessageCircle', tone: 'warning', title: 'Новое сообщение', text: 'Мария Иванова написала вам в чате.', time: 'Сегодня, 12:40', read: true },
]

export const lessonsForReview = [
  { id: 14, tutor: 'Мария Иванова', tutorInitials: 'МИ', student: 'Анна Смирнова', date: '30 июля, 18:00', duration: '60 мин', video: true, shots: true, status: 'Ожидает проверки', topic: 'Дроби и проценты' },
  { id: 15, tutor: 'Иван Соколов', tutorInitials: 'ИС', student: 'Кирилл Власов', date: '30 июля, 16:30', duration: '45 мин', video: false, shots: true, status: 'Нужно исправить', topic: 'Чтение и понимание текста' },
  { id: 16, tutor: 'Ольга Лебедева', tutorInitials: 'ОЛ', student: 'Вера Михайлова', date: '29 июля, 17:00', duration: '60 мин', video: true, shots: true, status: 'Проверено', topic: 'Вводный урок по английскому' },
]
