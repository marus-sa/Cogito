import { defineStore } from 'pinia'
import { api } from '../api'

export const useHomeworkStore = defineStore('homework', {
  state: () => ({ homework: [], goals: [] }),
  actions: {
    async loadHomework() {
      const [homeworkData, goalsData] = await Promise.all([api('/homework'), api('/goals')])
      this.homework = homeworkData.items
      this.goals = goalsData.items
    },
    async addHomework(payload) {
      const data = await api('/homework', { method: 'POST', body: JSON.stringify(payload) })
      this.homework.unshift(data.item)
    },
    async submitHomework(id) {
      const data = await api(`/homework/${id}/submit`, { method: 'PATCH' })
      const index = this.homework.findIndex((item) => item.id === id)
      if (index !== -1) this.homework[index] = data.item
    },
    async gradeHomework(id, score) {
      const data = await api(`/homework/${id}/grade`, { method: 'PATCH', body: JSON.stringify({ score }) })
      const index = this.homework.findIndex((item) => item.id === id)
      if (index !== -1) this.homework[index] = data.item
    },
    async toggleGoalTask(goalId, taskId) {
      const data = await api(`/goals/${goalId}/tasks/${taskId}`, { method: 'PATCH' })
      const index = this.goals.findIndex((item) => item.id === goalId)
      if (index !== -1) this.goals[index] = data.item
    },
    async addGoal(payload) {
      const data = await api('/goals', { method: 'POST', body: JSON.stringify(payload) })
      this.goals.unshift(data.item)
    },
  },
})
