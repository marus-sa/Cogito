<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bell, Menu, Search, CheckCheck, ArrowRight, X } from 'lucide-vue-next'
import { navigation } from '../config'
import AppIcon from './AppIcon.vue'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import UserAvatar from './UserAvatar.vue'
import { countText, notificationPath } from '../helpers'

defineEmits(['menu'])

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const messages = useMessagesStore()
const notificationsOpen = ref(false)
const searchOpen = ref(false)
const search = ref('')

const unread = computed(() => messages.notifications.filter((item) => !item.read).length)
const title = computed(() => route.meta.title || 'Главная')
const searchText = computed(() => search.value.trim().toLowerCase().replace(/ё/g, 'е'))
const pages = computed(() => navigation.filter((item) => item.roles.includes(auth.roleKey)))
const searchResults = computed(() => {
  if (!searchText.value) return pages.value.slice(0, 5)
  return pages.value.filter((item) =>
    `${item.label} ${item.description} ${item.keywords}`
      .toLowerCase()
      .replace(/ё/g, 'е')
      .includes(searchText.value),
  )
})

function handleSearch() {
  searchOpen.value = true
  if (searchText.value && searchResults.value.length === 1) openSearchResult(searchResults.value[0])
}

function openSearchResult(result) {
  router.push(result.to)
  search.value = ''
  searchOpen.value = false
}

function closeSearch() {
  searchOpen.value = false
}

function clearSearch() {
  search.value = ''
  searchOpen.value = true
}

function startSearch() {
  notificationsOpen.value = false
  searchOpen.value = true
}

function toggleNotifications() {
  searchOpen.value = false
  notificationsOpen.value = !notificationsOpen.value
}

async function openNotification(notification) {
  try {
    if (!notification.read) await messages.markRead(notification.id)
    notificationsOpen.value = false
    router.push(notificationPath(notification, auth.roleKey))
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}

async function readAll() {
  try {
    await messages.markAllRead()
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}

function openAllNotifications() {
  notificationsOpen.value = false
  router.push('/notifications')
}
</script>

<template>
  <header class="header">
    <div class="page-name">
      <button class="menu-button" aria-label="Открыть меню" @click="$emit('menu')">
        <Menu :size="22" />
      </button>
      <h1>{{ title }}</h1>
    </div>
    <div class="header-actions">
      <div class="search-wrap">
        <form class="search-field" @submit.prevent="handleSearch" @focusin="startSearch">
          <Search :size="17" />
          <input
            v-model="search"
            aria-label="Поиск по разделам"
            placeholder="Поиск"
            @keydown.esc="closeSearch"
          />
          <button
            v-if="search"
            class="clear-search"
            type="button"
            aria-label="Очистить поиск"
            @click="clearSearch"
          >
            <X :size="14" />
          </button>
        </form>
        <Transition name="drop">
          <div v-if="searchOpen" class="search-results">
            <div class="search-results-head">
              <b>{{ searchText ? 'Результаты поиска' : 'Быстрый переход' }}</b>
              <small v-if="searchText">
                {{ countText(searchResults.length, 'раздел', 'раздела', 'разделов') }}
              </small>
            </div>
            <button
              v-for="item in searchResults"
              :key="item.to"
              class="search-result"
              @click="openSearchResult(item)"
            >
              <span class="search-result-icon"><AppIcon :name="item.icon" :size="16" /></span>
              <span>
                <b>{{ item.label }}</b>
                <small>{{ item.description }}</small>
              </span>
              <ArrowRight :size="15" />
            </button>
            <p v-if="!searchResults.length" class="search-empty">
              Ничего не найдено. Попробуйте другое слово.
            </p>
          </div>
        </Transition>
      </div>
      <div class="notification-wrap">
        <button class="bell" aria-label="Уведомления" @click="toggleNotifications">
          <Bell :size="20" />
          <span v-if="unread">{{ unread }}</span>
        </button>
        <Transition name="drop">
          <div v-if="notificationsOpen" class="notification-panel">
            <div class="notify-head">
              <b>Уведомления</b>
              <button @click="readAll">
                <CheckCheck :size="15" />
                Прочитать все
              </button>
            </div>
            <button
              v-for="item in messages.notifications.slice(0, 5)"
              :key="item.id"
              class="notification-item"
              :class="{ unread: !item.read }"
              @click="openNotification(item)"
            >
              <span :class="['notify-icon', item.tone]">
                <AppIcon :name="item.icon" :size="16" />
              </span>
              <span>
                <b>{{ item.title }}</b>
                <small>{{ item.text }}</small>
                <em>{{ item.time }}</em>
              </span>
            </button>
            <p v-if="!messages.notifications.length" class="notification-empty">
              Новых уведомлений пока нет.
            </p>
            <button class="all-notifications" @click="openAllNotifications">
              Все уведомления
              <ArrowRight :size="14" />
            </button>
          </div>
        </Transition>
      </div>
      <RouterLink to="/profile" class="user-menu">
        <UserAvatar
          :initials="auth.user.initials"
          :color="auth.user.avatarColor || auth.user.color"
          :size="38"
        />
        <span>
          <b>{{ auth.user.name }}</b>
          <small>{{ auth.roleLabel }}</small>
        </span>
      </RouterLink>
    </div>
  </header>
</template>

<style scoped>
.header {
  position: sticky;
  z-index: 20;
  top: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 79px;
  padding: 0 32px;
  background: rgba(248, 246, 252, 0.91);
  border-bottom: 1px solid rgba(231, 224, 241, 0.73);
  backdrop-filter: blur(12px);
}
.page-name {
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-name h1 {
  margin: 0;
  font-size: 18px;
  letter-spacing: -0.3px;
}
.menu-button {
  display: none;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 10px;
  color: var(--primary-dark);
  background: var(--primary-extra-light);
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}
.search-wrap {
  position: relative;
}
.search-field {
  position: relative;
  display: flex;
  align-items: center;
  width: 220px;
  color: var(--text-secondary);
}
.search-field :deep(input) {
  min-height: 38px;
  padding-left: 36px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.74);
  font-size: 12px;
}
.search-field > svg {
  position: absolute;
  z-index: 1;
  left: 12px;
  pointer-events: none;
}
.clear-search {
  position: absolute;
  z-index: 1;
  top: 7px;
  right: 7px;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 7px;
  color: var(--text-secondary);
  background: transparent;
}
.clear-search:hover {
  color: var(--primary-dark);
  background: var(--primary-extra-light);
}
.search-results {
  position: absolute;
  top: 46px;
  right: 0;
  z-index: 4;
  width: 350px;
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow);
}
.search-results-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding: 14px 15px 8px;
}
.search-results-head b {
  font-size: 12px;
}
.search-results-head small {
  color: var(--text-secondary);
  font-size: 10px;
}
.search-result {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 9px 14px;
  border: 0;
  color: var(--text-main);
  background: #fff;
  text-align: left;
}
.search-result:hover {
  background: #fbf9fe;
}
.search-result > span:nth-child(2) {
  min-width: 0;
  flex: 1;
}
.search-result b,
.search-result small {
  display: block;
}
.search-result b {
  font-size: 11px;
}
.search-result small {
  margin-top: 2px;
  color: var(--text-secondary);
  font-size: 9px;
}
.search-result > svg {
  color: var(--primary);
}
.search-result-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  color: var(--primary-dark);
  background: var(--primary-extra-light);
  border-radius: 9px;
}
.search-empty {
  margin: 0;
  padding: 18px 15px;
  color: var(--text-secondary);
  font-size: 11px;
  text-align: center;
}
.bell {
  position: relative;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 11px;
  color: #6d647a;
  background: #fff;
}
.bell:hover {
  color: var(--primary-dark);
  background: var(--primary-extra-light);
}
.bell span {
  position: absolute;
  top: -3px;
  right: -3px;
  display: grid;
  place-items: center;
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  color: #fff;
  background: #c97880;
  border: 2px solid var(--background);
  border-radius: 9px;
  font-size: 9px;
  font-weight: 800;
}
.user-menu {
  display: flex;
  align-items: center;
  gap: 9px;
  padding-left: 3px;
}
.user-menu b {
  display: block;
  max-width: 135px;
  overflow: hidden;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-menu small {
  display: block;
  margin-top: 1px;
  color: var(--text-secondary);
  font-size: 10px;
}
.notification-wrap {
  position: relative;
}
.notification-panel {
  position: absolute;
  top: 48px;
  right: -6px;
  width: 355px;
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: var(--shadow);
}
.notify-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 16px 11px;
}
.notify-head b {
  font-size: 14px;
}
.notify-head button,
.all-notifications {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 0;
  color: var(--primary-dark);
  background: transparent;
  font-size: 11px;
  font-weight: 800;
}
.notification-item {
  display: flex;
  gap: 9px;
  width: 100%;
  padding: 11px 16px;
  border: 0;
  color: var(--text-main);
  background: #fff;
  text-align: left;
}
.notification-item:hover {
  background: #fbf9fe;
}
.notification-item.unread {
  background: #faf8ff;
}
.notify-icon {
  display: grid;
  place-items: center;
  width: 31px;
  height: 31px;
  border-radius: 9px;
}
.notify-icon.primary {
  background: var(--primary-extra-light);
  color: var(--primary-dark);
}
.notify-icon.success {
  background: #e8f5ee;
  color: #4d8967;
}
.notify-icon.warning {
  background: #fcf3e5;
  color: #a87d37;
}
.notification-item b,
.notification-item small,
.notification-item em {
  display: block;
}
.notification-item b {
  font-size: 11px;
}
.notification-item small {
  margin-top: 2px;
  color: var(--text-secondary);
  font-size: 10px;
  line-height: 1.35;
}
.notification-item em {
  margin-top: 4px;
  color: #9d94a8;
  font-size: 9px;
  font-style: normal;
}
.notification-empty {
  margin: 0;
  padding: 13px 16px;
  color: var(--text-secondary);
  font-size: 11px;
  text-align: center;
}
.all-notifications {
  justify-content: center;
  width: 100%;
  padding: 12px;
  border-top: 1px solid var(--border);
}
.drop-enter-active,
.drop-leave-active {
  transition: 0.17s ease;
}
.drop-enter-from,
.drop-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}
@media (max-width: 850px) {
  .header {
    min-height: 68px;
    padding: 0 18px;
  }
  .menu-button {
    display: grid;
    place-items: center;
  }
  .search-wrap {
    display: none;
  }
  .user-menu span {
    display: none;
  }
  .header-actions {
    gap: 10px;
  }
  .notification-panel {
    right: -50px;
    width: min(355px, calc(100vw - 30px));
  }
}
@media (max-width: 430px) {
  .header {
    padding: 0 13px;
  }
  .page-name h1 {
    font-size: 16px;
  }
  .header-actions {
    gap: 5px;
  }
  .bell {
    background: transparent;
  }
  .notification-panel {
    right: -46px;
  }
}
</style>
