<script setup>
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
</script>
<template>
  <div class="page help-page">
    <div class="page-heading">
      <div>
        <h1>Помощь</h1>
        <p>Как пользоваться Cogito.</p>
      </div>
    </div>
    <section class="card panel">
      <h2>Основные разделы</h2>
      <ul>
        <li>
          <RouterLink to="/schedule">Расписание</RouterLink>
          : откройте ссылку занятия; репетитор может создать, перенести или отменить встречу.
        </li>
        <li>
          <RouterLink to="/homework">Домашние задания</RouterLink>
          : ученик отправляет ответ, файлы или ссылку на работу, репетитор назначает и проверяет задания.
        </li>
        <li>
          <RouterLink to="/goals">Цели</RouterLink>
          : ученик создаёт цель и отмечает подзадачи. Прогресс рассчитывается по сохранённым данным.
        </li>
        <li>
          <RouterLink to="/chats">Чаты</RouterLink>
          : начните диалог с доступным участником. Получателей определяют ваши связи и роль. Чужие
          переписки недоступны.
        </li>
        <li>
          <RouterLink to="/notifications">Уведомления</RouterLink>
          : откройте событие или отметьте его прочитанным.
        </li>
        <li>
          <RouterLink to="/profile">Профиль</RouterLink>
          : измените личные данные, цвет аватара и настройки уведомлений. Смена почты самостоятельно
          недоступна.
        </li>
      </ul>
    </section>
    <section v-if="['tutor', 'mentor', 'admin'].includes(auth.roleKey)" class="card panel">
      <h2>Отчёты о занятиях</h2>
      <p v-if="auth.roleKey === 'tutor'">
        В
        <RouterLink to="/hours">«Моих часах»</RouterLink>
        добавьте отчёт: ученика, дату, длительность, тему и ссылку на запись на облачном диске.
        Проверьте, что наставнику разрешён просмотр записи. После проверки часы попадут в
        подтверждённые.
      </p>
      <p v-if="auth.roleKey !== 'tutor'">
        В
        <RouterLink to="/lessons-control">«Контроле занятий»</RouterLink>
        проверьте запись и измените статус отчёта.
      </p>
    </section>
    <section v-if="auth.roleKey === 'parent'" class="card panel">
      <h2>Если не видно данных ребёнка</h2>
      <p>
        Попросите координатора связать ваш аккаунт с аккаунтом ученика. Указание имени ребёнка в
        профиле не открывает доступ автоматически — это защищает данные детей.
      </p>
    </section>
    <section v-if="auth.roleKey === 'admin'" class="card panel">
      <h2>Администрирование</h2>
      <p>
        В
        <RouterLink to="/reports">«Заявках»</RouterLink>
        одобрите или отклоните репетитора после подтверждения почты. В
        <RouterLink to="/users">«Участниках»</RouterLink>
        назначьте роли и связи. Собственную роль изменить и свой аккаунт заблокировать нельзя.
      </p>
    </section>
    <section class="card panel">
      <h2>Остался вопрос?</h2>
      <p>
        <RouterLink to="/chats">Напишите координатору в чате.</RouterLink>
        Опишите раздел, действие и текст ошибки. Никому не отправляйте пароль или ссылку
        подтверждения почты.
      </p>
    </section>
  </div>
</template>
<style scoped>
.help-page {
  max-width: 1000px;
}
.panel {
  margin-top: 20px;
}
p,
li {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
}
ul {
  display: grid;
  gap: 12px;
  padding-left: 20px;
}
a {
  color: var(--primary-dark);
}
</style>
