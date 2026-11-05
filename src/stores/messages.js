import { defineStore } from 'pinia'
import { api } from '../api.js'

export const useMessagesStore = defineStore('messages', {
  state: () => ({ messages: [], dialogs: [], contacts: [], toast: null }),
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
      const data = await api('/conversations', { method: 'POST', body: { recipientId } })
      await this.loadDialogs()
      return data.item
    },
    async send(dialogId, text) {
      const data = await api('/messages', { method: 'POST', body: { dialogId, text } })
      this.messages.push(data.item)
      const dialog = this.dialogs.find((item) => item.id === dialogId)
      if (dialog) {
        dialog.last = data.item.text
        dialog.time = data.item.time
        dialog.unread = 0
      }
    },
    showToast(text, type = 'success') {
      this.toast = { text, type, id: Date.now() }
      setTimeout(() => {
        this.toast = null
      }, 3200)
    },
  },
})
