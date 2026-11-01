<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CheckCheck, ChevronRight } from 'lucide-vue-next'
import AppIcon from '../components/AppIcon.vue'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import EmptyState from '../components/EmptyState.vue'
import { notificationPath } from '../helpers'

const router = useRouter()
const auth = useAuthStore()
const messages = useMessagesStore()
const isLoading = ref(false)
const isMarkingAll = ref(false)
const notifications = computed(() => messages.notifications)
const unread = computed(() => notifications.value.filter((item) => !item.read).length)

async function loadNotifications() {
  isLoading.value = true
  try {
    await messages.loadNotifications()
  } catch (error) {
    messages.showToast(error.message, 'error')
  } finally {
    isLoading.value = false
  }
}

async function openNotification(notification) {
  try {
    if (!notification.read) await messages.markRead(notification.id)
    const destination = notificationPath(notification, auth.roleKey)
    if (destination !== '/notifications') router.push(destination)
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}

async function markAllRead() {
  if (!unread.value) return
  isMarkingAll.value = true
  try {
    await messages.markAllRead()
  } catch (error) {
    messages.showToast(error.message, 'error')
  } finally {
    isMarkingAll.value = false
  }
}

onMounted(loadNotifications)
</script>

<template>
  <div class="page notifications-page">
    <div class="page-heading">
      <div>
        <h1>Уведомления</h1>
        <p>Все события, связанные с вашим кабинетом и обучением.</p>
      </div>
      <button class="read-all" :disabled="!unread || isMarkingAll" @click="markAllRead">
        <CheckCheck :size="17" />
        {{ isMarkingAll ? 'Отмечаем…' : unread ? `Прочитать все (${unread})` : 'Всё прочитано' }}
      </button>
    </div>

    <section class="card notification-list">
      <div v-if="isLoading" class="loading-copy">Обновляем уведомления…</div>
      <template v-else>
        <button
          v-for="notification in notifications"
          :key="notification.id"
          class="notification-row"
          :class="{ unread: !notification.read }"
          @click="openNotification(notification)"
        >
          <span :class="['notification-icon', notification.tone]">
            <AppIcon :name="notification.icon" />
          </span>
          <span class="notification-copy">
            <b>{{ notification.title }}</b>
            <small>{{ notification.text }}</small>
            <em>{{ notification.time }}</em>
          </span>
          <span class="row-action">
            <span
              v-if="notification.title === 'Новая заявка репетитора' && auth.roleKey === 'admin'"
            >
              Открыть заявку
            </span>
            <ChevronRight :size="18" />
          </span>
        </button>
        <EmptyState
          v-if="!notifications.length"
          title="Уведомлений пока нет"
          text="Когда в кабинете появится новое событие, оно будет показано здесь."
        />
      </template>
    </section>
  </div>
</template>

<style scoped>
.notifications-page {
  max-width: 920px;
}
.page-heading {
  align-items: center;
}
.read-all {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 40px;
  padding: 0 13px;
  border: 1px solid var(--border);
  border-radius: 11px;
  color: var(--primary-dark);
  background: #fff;
  font-size: 12px;
  font-weight: 800;
}
.read-all:hover:not(:disabled) {
  background: var(--primary-extra-light);
}
.read-all:disabled {
  cursor: default;
  opacity: 0.65;
}
.notification-list {
  overflow: hidden;
}
.notification-row {
  display: flex;
  align-items: center;
  gap: 13px;
  width: 100%;
  padding: 16px 19px;
  border: 0;
  border-bottom: 1px solid var(--border);
  color: var(--text-main);
  background: #fff;
  text-align: left;
  transition: background 0.18s;
}
.notification-row:last-child {
  border-bottom: 0;
}
.notification-row:hover {
  background: #fbf9fe;
}
.notification-row.unread {
  background: #faf8ff;
}
.notification-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 42px;
  height: 42px;
  border-radius: 13px;
}
.notification-icon.primary {
  color: var(--primary-dark);
  background: var(--primary-extra-light);
}
.notification-icon.success {
  color: #4d8967;
  background: #e8f5ee;
}
.notification-icon.warning {
  color: #a87d37;
  background: #fcf3e5;
}
.notification-copy {
  min-width: 0;
  flex: 1;
}
.notification-copy b,
.notification-copy small,
.notification-copy em {
  display: block;
}
.notification-copy b {
  font-size: 13px;
}
.notification-copy small {
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.45;
}
.notification-copy em {
  margin-top: 5px;
  color: #9d94a8;
  font-size: 10px;
  font-style: normal;
}
.notification-row.unread .notification-copy b::after {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-left: 6px;
  vertical-align: middle;
  content: '';
  background: var(--primary);
  border-radius: 50%;
}
.row-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex: 0 0 auto;
  color: var(--primary-dark);
  font-size: 10px;
  font-weight: 800;
}
.loading-copy {
  padding: 38px 20px;
  color: var(--text-secondary);
  font-size: 12px;
  text-align: center;
}
@media (max-width: 720px) {
  .page-heading {
    display: flex;
  }
  .page-heading p {
    font-size: 12px;
  }
  .read-all {
    padding: 0 10px;
    font-size: 10px;
  }
  .notification-row {
    align-items: flex-start;
    padding: 14px;
  }
  .row-action span {
    display: none;
  }
  .row-action {
    margin-top: 12px;
  }
  .notification-copy b {
    font-size: 12px;
  }
  .notification-copy small {
    font-size: 10px;
  }
}
</style>
