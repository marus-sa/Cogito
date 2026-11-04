import { defineStore } from 'pinia'
import { api } from '../api.js'

export const useHomeworkStore = defineStore('homework', {
  state: () => ({ homework: [] }),
  actions: {
    async loadHomework() {
      const homeworkData = await api('/homework')
      this.homework = homeworkData.items
    },
    async addHomework(payload) {
      const data = await api('/homework', { method: 'POST', body: payload })
      this.homework.unshift(data.item)
    },
    async submitHomework(id, payload = {}) {
      const data = await api(`/homework/${id}/submit`, { method: 'PATCH', body: payload })
      const index = this.homework.findIndex((item) => item.id === id)
      if (index !== -1) this.homework[index] = data.item
    },
    async gradeHomework(id, payload) {
      const data = await api(`/homework/${id}/grade`, { method: 'PATCH', body: payload })
      const index = this.homework.findIndex((item) => item.id === id)
      if (index !== -1) this.homework[index] = data.item
    },
    async removeFile(homeworkId, fileId) {
      const data = await api(`/homework/${homeworkId}/files/${fileId}`, { method: 'DELETE' })
      const index = this.homework.findIndex((item) => item.id === homeworkId)
      if (index !== -1) this.homework[index] = data.item
      return data.item
    },
  },
})
