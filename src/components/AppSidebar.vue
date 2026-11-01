<script setup>
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { CircleHelp, LogOut, UserRound, X } from 'lucide-vue-next'
import { useAuthStore } from '../stores/auth'
import { navigation } from '../config'
import AppIcon from './AppIcon.vue'
import { useMessagesStore } from '../stores/messages'

const props = defineProps({ mobileOpen: Boolean })
const emit = defineEmits(['close'])
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const navItems = computed(() =>
  navigation.filter((item) => item.sidebar !== false && item.roles.includes(auth.roleKey)),
)

function close() {
  emit('close')
}
async function logout() {
  try {
    await auth.logout()
    router.push('/login')
    close()
  } catch (error) {
    useMessagesStore().showToast(
      'Не удалось выйти. Проверьте подключение и попробуйте снова.',
      'error',
    )
  }
}
</script>

<template>
  <div v-if="mobileOpen" class="mobile-dim" @click="close" />
  <aside class="sidebar" :class="{ 'is-open': mobileOpen }">
    <div class="brand-row">
      <RouterLink class="brand" to="/dashboard" @click="close">
        <span class="brand-mark">
          <span></span>
          <span></span>
        </span>
        <span>
          <b>Cogito</b>
          <small>Платформа Light Hearts</small>
        </span>
      </RouterLink>
      <button class="mobile-close" aria-label="Закрыть меню" @click="close">
        <X :size="20" />
      </button>
    </div>

    <nav aria-label="Основная навигация">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-link"
        :class="{ active: route.path === item.to }"
        @click="close"
      >
        <AppIcon :name="item.icon" />
        <span>{{ item.label }}</span>
      </RouterLink>
      <RouterLink
        to="/profile"
        class="nav-link"
        :class="{ active: route.path === '/profile' }"
        @click="close"
      >
        <UserRound :size="19" />
        <span>Профиль</span>
      </RouterLink>
    </nav>

    <div class="sidebar-bottom">
      <RouterLink to="/help" class="help-card" @click="close">
        <span class="help-icon"><CircleHelp :size="17" /></span>
        <div>
          <b>Нужна помощь?</b>
          <small>Инструкция и поддержка</small>
        </div>
      </RouterLink>
      <button class="nav-link logout" @click="logout">
        <LogOut :size="19" />
        <span>Выйти</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  z-index: 30;
  inset: 0 auto 0 0;
  display: flex;
  flex-direction: column;
  width: 264px;
  padding: 25px 14px 16px;
  background: #fff;
  border-right: 1px solid var(--border);
}
.brand-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px 27px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 11px;
}
.brand b {
  display: block;
  color: var(--text-main);
  font-size: 22px;
  letter-spacing: -0.9px;
}
.brand small {
  display: block;
  margin-top: -1px;
  color: var(--text-secondary);
  font-size: 9px;
  font-weight: 700;
}
.brand-mark {
  position: relative;
  display: inline-block;
  width: 33px;
  height: 28px;
}
.brand-mark span {
  position: absolute;
  top: 5px;
  width: 18px;
  height: 18px;
  background: var(--primary);
  border-radius: 7px 9px 7px 2px;
  transform: rotate(45deg);
}
.brand-mark span:first-child {
  left: 3px;
  background: #9a83d1;
}
.brand-mark span:last-child {
  right: 2px;
  background: #e8c2ce;
  transform: rotate(45deg) scale(0.76);
}
nav {
  display: grid;
  gap: 4px;
}
.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 44px;
  padding: 0 12px;
  border: 0;
  border-radius: 12px;
  color: #72697f;
  background: transparent;
  text-align: left;
  font-size: 13px;
  font-weight: 700;
  transition: 0.18s;
}
.nav-link:hover {
  color: var(--primary-dark);
  background: #faf8fd;
}
.nav-link.active {
  color: var(--primary-dark);
  background: var(--primary-extra-light);
}
.nav-link.active :deep(svg) {
  stroke-width: 2.6px;
}
.sidebar-bottom {
  margin-top: auto;
}
.help-card {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 12px 5px 14px;
  padding: 12px;
  background: #f7f3ff;
  border-radius: 15px;
  transition:
    background 0.18s,
    transform 0.18s;
}
.help-card:hover {
  background: #eee6fc;
  transform: translateY(-1px);
}
.help-card:focus-visible {
  outline: 3px solid rgba(130, 103, 199, 0.28);
  outline-offset: 2px;
}
.help-icon {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  color: var(--primary-dark);
  background: #e6dcfa;
  border-radius: 9px;
}
.help-card b {
  display: block;
  font-size: 11px;
}
.help-card small {
  display: block;
  margin-top: 2px;
  color: var(--text-secondary);
  font-size: 9px;
}
.logout {
  color: #9a6670;
}
.logout:hover {
  color: #a2515d;
  background: #fff6f7;
}
.mobile-close {
  display: none;
  border: 0;
  background: transparent;
  color: var(--text-secondary);
}
.mobile-dim {
  display: none;
}
@media (max-width: 850px) {
  .sidebar {
    transform: translateX(-105%);
    box-shadow: 0 15px 35px rgba(34, 19, 58, 0.16);
    transition: transform 0.25s ease;
  }
  .sidebar.is-open {
    transform: translateX(0);
  }
  .mobile-dim {
    position: fixed;
    z-index: 29;
    inset: 0;
    display: block;
    background: rgba(40, 30, 55, 0.34);
  }
  .mobile-close {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: 9px;
  }
  .mobile-close:hover {
    background: var(--primary-extra-light);
  }
}
</style>
