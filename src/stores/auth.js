import { defineStore } from 'pinia'
import { roles } from '../data/mockData'
import { api } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    roleKey: localStorage.getItem('cogito-role') || 'student',
    isAuthenticated: Boolean(localStorage.getItem('cogito-auth')),
    profile: null,
  }),
  getters: {
    user(state) {
      const role = roles[state.roleKey]
      if (!state.profile) return role
      const words = state.profile.name.split(' ')
      return { ...role, ...state.profile, initials: words.map((word) => word[0]).join('').slice(0, 2) }
    },
    roleLabel(state) { return roles[state.roleKey]?.label || 'Участник' },
  },
  actions: {
    setLogin(user) {
      this.roleKey = user.role
      this.profile = user
      this.isAuthenticated = true
      localStorage.setItem('cogito-role', user.role)
      localStorage.setItem('cogito-auth', 'true')
    },
    async login(email, password, role, remember) {
      const data = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password, role, remember }) })
      this.setLogin(data.user)
    },
    async register(form) {
      const data = await api('/auth/register', { method: 'POST', body: JSON.stringify(form) })
      if (!data.needsApproval) this.setLogin(data.user)
      return data
    },
    async restore() {
      if (!localStorage.getItem('cogito-auth')) return false
      try {
        const data = await api('/auth/me')
        this.setLogin(data.user)
        return true
      } catch {
        this.clearLogin()
        return false
      }
    },
    clearLogin() {
      this.profile = null
      this.isAuthenticated = false
      localStorage.removeItem('cogito-auth')
      localStorage.removeItem('cogito-role')
    },
    async logout() {
      try { await api('/auth/logout', { method: 'POST' }) } catch { /* Сервер может быть уже выключен. */ }
      this.clearLogin()
    },
    async updateProfile(form) {
      const data = await api('/profile', { method: 'PUT', body: JSON.stringify({ ...this.profile, ...form }) })
      this.profile = data.user
    },
  },
})
