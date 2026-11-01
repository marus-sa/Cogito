import { defineStore } from 'pinia'
import { roles } from '../config.js'
import { api, resetAccountRequests } from '../api.js'
import { initialsFromName } from '../helpers.js'
import { useLessonsStore } from './lessons.js'
import { useHomeworkStore } from './homework.js'
import { useMessagesStore } from './messages.js'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    roleKey: 'student',
    isAuthenticated: false,
    profile: null,
  }),
  getters: {
    user(state) {
      const role = roles[state.roleKey]
      if (!state.profile) return role
      return { ...role, ...state.profile, initials: initialsFromName(state.profile.name) }
    },
    roleLabel(state) {
      return roles[state.roleKey]?.label || 'Участник'
    },
  },
  actions: {
    setLogin(user) {
      if (this.profile?.id !== user.id || this.roleKey !== user.role) this.clearAccountData()
      this.roleKey = user.role
      this.profile = user
      this.isAuthenticated = true
    },
    async login(email, password, remember) {
      const data = await api('/auth/login', {
        method: 'POST',
        body: { email, password, remember },
      })
      this.setLogin(data.user)
    },
    async register(form) {
      return api('/auth/register', { method: 'POST', body: form })
    },
    async verifyEmail(token) {
      const data = await api('/auth/verify-email', { method: 'POST', body: { token } })
      if (data.user.accountStatus === 'active') this.setLogin(data.user)
      return data
    },
    async resendEmailVerification(email) {
      return api('/auth/resend-email-verification', { method: 'POST', body: { email } })
    },
    async restore() {
      // Сервер узнаёт пользователя по cookie. Отдельный флаг в браузере не нужен.
      try {
        const data = await api('/auth/me')
        this.setLogin(data.user)
        return true
      } catch (error) {
        if (error.code === 'account_changed') return this.isAuthenticated
        this.clearLogin()
        return false
      }
    },
    clearLogin() {
      this.clearAccountData()
      this.profile = null
      this.isAuthenticated = false
      this.roleKey = 'student'
    },
    clearAccountData() {
      resetAccountRequests()
      useLessonsStore().$reset()
      useHomeworkStore().$reset()
      useMessagesStore().$reset()
    },
    async logout() {
      // При обрыве сети не обещаем выход: серверная сессия ещё может действовать.
      await api('/auth/logout', { method: 'POST' })
      this.clearLogin()
    },
    async updateProfile(form) {
      const data = await api('/profile', { method: 'PUT', body: form })
      this.profile = data.user
    },
  },
})
