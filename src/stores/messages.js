import { defineStore } from 'pinia'
import { api } from '../api'

export const useMessagesStore = defineStore('messages', {
  state: () => ({ messages: [], dialogs: [], contacts: [], notifications: [], toast: null }),
  actions: {
    async loadMessages(dialogId) {
      const data = await api(`/messages?dialog_id=${dialogId}`)
      this.messages = data.items
    },
    async loadDialogs() {
      const data = await api('/conversations')
      this.dialogs = data.items
    },
    async loadContacts() {
      const data = await api('/chat/contacts')
      this.contacts = data.items
    },
    async startConversation(recipientId) {
      const data = await api('/conversations', { method: 'POST', body: JSON.stringify({ recipientId }) })
      await this.loadDialogs()
      return data.item
    },
    async loadNotifications() {
      const data = await api('/notifications')
      this.notifications = data.items
    },
    async send(dialogId, text) {
      const data = await api('/messages', { method: 'POST', body: JSON.stringify({ dialogId, text }) })
      this.messages.push(data.item)
      const dialog = this.dialogs.find((item) => item.id === dialogId)
      if (dialog) {
        dialog.last = data.item.text
        dialog.time = data.item.time
        dialog.unread = 0
      }
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
