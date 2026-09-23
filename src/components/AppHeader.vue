<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bell, Menu, Search, CheckCheck, X } from 'lucide-vue-next'
import * as Icons from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { useMessagesStore } from '../stores/messages'
import UserAvatar from './UserAvatar.vue'

defineEmits(['menu'])
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const messages = useMessagesStore()
const notificationsOpen = ref(false)
const search = ref('')
const unread = computed(() => messages.notifications.filter((item) => !item.read).length)
const title = computed(() => route.meta.title || 'Главная')
function handleSearch() {
  if (search.value.trim()) { messages.showToast(`Поиск: «${search.value.trim()}» — результаты появятся в этом разделе.`, 'success'); search.value = '' }
}
async function openNotification(notification) {
  try {
    await messages.markRead(notification.id)
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
  notificationsOpen.value = false
  router.push(notification.title === 'Новая заявка репетитора' ? '/reports' : '/dashboard')
}

async function readAll() {
  try {
    await messages.markAllRead()
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
</script>

<template>
  <header class="header">
    <div class="page-name"><button class="menu-button" aria-label="Открыть меню" @click="$emit('menu')"><Menu :size="22" /></button><h1>{{ title }}</h1></div>
    <div class="header-actions">
      <form class="search-field" @submit.prevent="handleSearch"><Search :size="17" /><input v-model="search" aria-label="Поиск" placeholder="Поиск" /></form>
      <div class="notification-wrap">
        <button class="bell" aria-label="Уведомления" @click="notificationsOpen = !notificationsOpen"><Bell :size="20" /><span v-if="unread">{{ unread }}</span></button>
        <Transition name="drop"><div v-if="notificationsOpen" class="notification-panel">
          <div class="notify-head"><b>Уведомления</b><button @click="readAll"><CheckCheck :size="15" /> Прочитать все</button></div>
          <button v-for="item in messages.notifications" :key="item.id" class="notification-item" :class="{ unread: !item.read }" @click="openNotification(item)">
            <span :class="['notify-icon', item.tone]"><component :is="Icons[item.icon]" :size="16" /></span><span><b>{{ item.title }}</b><small>{{ item.text }}</small><em>{{ item.time }}</em></span>
          </button>
          <button class="all-notifications" @click="notificationsOpen = false; router.push('/dashboard')">Все уведомления</button>
        </div></Transition>
      </div>
      <RouterLink to="/profile" class="user-menu"><UserAvatar :initials="auth.user.initials" :color="auth.user.color" :size="38" /><span><b>{{ auth.user.name }}</b><small>{{ auth.roleLabel }}</small></span></RouterLink>
    </div>
  </header>
</template>

<style scoped>
.header { position: sticky; z-index: 20; top: 0; display: flex; align-items: center; justify-content: space-between; min-height: 79px; padding: 0 32px; background: rgba(248,246,252,.91); border-bottom: 1px solid rgba(231,224,241,.73); backdrop-filter: blur(12px); }.page-name { display: flex; align-items: center; gap: 12px; }.page-name h1 { margin: 0; font-size: 18px; letter-spacing: -.3px; }.menu-button { display: none; width: 36px; height: 36px; border: 0; border-radius: 10px; color: var(--primary-dark); background: var(--primary-extra-light); }.header-actions { display: flex; align-items: center; gap: 15px; }.search-field { position: relative; display: flex; align-items: center; width: 220px; color: var(--text-secondary); }.search-field :deep(input) { min-height: 38px; padding-left: 36px; border-radius: 11px; background: rgba(255,255,255,.74); font-size: 12px; }.search-field svg { position: absolute; z-index: 1; left: 12px; }.bell { position: relative; display: grid; place-items: center; width: 38px; height: 38px; border: 0; border-radius: 11px; color: #6d647a; background: #fff; }.bell:hover { color: var(--primary-dark); background: var(--primary-extra-light); }.bell span { position: absolute; top: -3px; right: -3px; display: grid; place-items: center; min-width: 17px; height: 17px; padding: 0 4px; color: #fff; background: #c97880; border: 2px solid var(--background); border-radius: 9px; font-size: 9px; font-weight: 800; }.user-menu { display: flex; align-items: center; gap: 9px; padding-left: 3px; }.user-menu b { display: block; max-width: 135px; overflow: hidden; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }.user-menu small { display: block; margin-top: 1px; color: var(--text-secondary); font-size: 10px; }.notification-wrap { position: relative; }.notification-panel { position: absolute; top: 48px; right: -6px; width: 355px; overflow: hidden; background: #fff; border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow); }.notify-head { display: flex; align-items: center; justify-content: space-between; padding: 15px 16px 11px; }.notify-head b { font-size: 14px; }.notify-head button, .all-notifications { display: inline-flex; align-items: center; gap: 5px; border: 0; color: var(--primary-dark); background: transparent; font-size: 11px; font-weight: 800; }.notification-item { display: flex; gap: 9px; width: 100%; padding: 11px 16px; border: 0; color: var(--text-main); background: #fff; text-align: left; }.notification-item:hover { background: #fbf9fe; }.notification-item.unread { background: #faf8ff; }.notify-icon { display: grid; place-items: center; width: 31px; height: 31px; border-radius: 9px; }.notify-icon.primary { background: var(--primary-extra-light); color: var(--primary-dark); }.notify-icon.success { background: #e8f5ee; color: #4d8967; }.notify-icon.warning { background: #fcf3e5; color: #a87d37; }.notification-item b,.notification-item small,.notification-item em { display: block; }.notification-item b { font-size: 11px; }.notification-item small { margin-top: 2px; color: var(--text-secondary); font-size: 10px; line-height: 1.35; }.notification-item em { margin-top: 4px; color: #9d94a8; font-size: 9px; font-style: normal; }.all-notifications { justify-content: center; width: 100%; padding: 12px; border-top: 1px solid var(--border); }.drop-enter-active,.drop-leave-active{transition:.17s ease}.drop-enter-from,.drop-leave-to{opacity:0;transform:translateY(-5px)}
@media(max-width:850px){.header{min-height:68px;padding:0 18px}.menu-button{display:grid;place-items:center}.search-field{display:none}.user-menu span{display:none}.header-actions{gap:10px}.notification-panel{right:-50px;width:min(355px,calc(100vw - 30px))}}@media(max-width:430px){.header{padding:0 13px}.page-name h1{font-size:16px}.header-actions{gap:5px}.bell{background:transparent}.notification-panel{right:-46px}}
</style>
