<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Menu, Search, ArrowRight, X } from 'lucide-vue-next'
import { navigation } from '../config'
import AppIcon from './AppIcon.vue'
import { useAuthStore } from '../stores/auth'
import UserAvatar from './UserAvatar.vue'
import { countText } from '../helpers'

defineEmits(['menu'])

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const searchOpen = ref(false)
const search = ref('')

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
  searchOpen.value = true
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
}
</style>
