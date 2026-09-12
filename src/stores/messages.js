import { defineStore } from 'pinia'
import { initialMessages, notifications } from '../data/mockData'
import { api } from '../api'

export const useMessagesStore = defineStore('messages', {
  state: () => ({ messages: [...initialMessages], notifications: [...notifications], toast: null }),
  actions: {
    async loadMessages(dialogId = 1) {
      const data = await api(`/messages?dialog_id=${dialogId}`)
      this.messages = data.items
    },
    async loadNotifications() {
      const data = await api('/notifications')
      this.notifications = data.items
    },
    async send(dialogId, text) {
      const data = await api('/messages', { method: 'POST', body: JSON.stringify({ dialogId, text }) })
      this.messages.push(data.item)
    },
    async markAllRead() {
      await api('/notifications', { method: 'PATCH', body: JSON.stringify({ all: true }) })
      this.notifications.forEach((item) => { item.read = true })
    },
    async markRead(id) {
      await api('/notifications', { method: 'PATCH', body: JSON.stringify({ id }) })
      const item = this.notifications.find((note) => note.id === id)
      if (item) item.read = true
    },
    showToast(text, type = 'success') {
      this.toast = { text, type, id: Date.now() }
      setTimeout(() => { this.toast = null }, 3200)
    },
  },
})
