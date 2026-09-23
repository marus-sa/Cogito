import { defineStore } from 'pinia'
import { api } from '../api'

export const useLessonsStore = defineStore('lessons', {
  state: () => ({ lessons: [], reviewLessons: [] }),
  actions: {
    async loadLessons() {
      const [lessonData, reviewData] = await Promise.all([api('/lessons'), api('/review-lessons')])
      this.lessons = lessonData.items
      this.reviewLessons = reviewData.items
    },
    async addLesson(payload) {
      const data = await api('/lessons', { method: 'POST', body: JSON.stringify(payload) })
      this.lessons.unshift(data.item)
    },
    async updateStatus(id, status) {
      const data = await api(`/lessons/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) })
      const index = this.lessons.findIndex((item) => item.id === id)
      if (index !== -1) this.lessons[index] = data.item
    },
    async verifyLesson(id, status = 'Проверено') {
      const data = await api(`/review-lessons/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) })
      const index = this.reviewLessons.findIndex((item) => item.id === id)
      if (index !== -1) this.reviewLessons[index] = data.item
    },
    async addReview(payload) {
      const data = await api('/review-lessons', { method: 'POST', body: JSON.stringify(payload) })
      this.reviewLessons.unshift(data.item)
    },
  },
})
