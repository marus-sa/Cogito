// Короткие общие функции. Они ничего не сохраняют и не обращаются к серверу.

export function initialsFromName(name) {
  const words = String(name || '')
    .trim()
    .split(/\s+/)
  let initials = ''
  for (const word of words.slice(0, 2)) {
    initials += word[0] || ''
  }
  return initials.toUpperCase() || 'УЧ'
}

export function countText(count, one, few, many) {
  const lastTwo = Math.abs(count) % 100
  const last = lastTwo % 10
  let word = many
  if (lastTwo < 11 || lastTwo > 14) {
    if (last === 1) word = one
    else if (last >= 2 && last <= 4) word = few
  }
  return `${count} ${word}`
}

export function scorePercent(score) {
  // Оценка приходит строкой, например «8 / 10» или «1,5 / 2».
  const parts = String(score || '').split('/')
  if (parts.length !== 2) return null

  const earnedText = parts[0].trim()
  const totalText = parts[1].trim()
  const numberPattern = /^\d+([.,]\d+)?$/
  if (!numberPattern.test(earnedText) || !numberPattern.test(totalText)) return null

  const earned = Number(earnedText.replace(',', '.'))
  const total = Number(totalText.replace(',', '.'))
  if (!Number.isFinite(earned) || !Number.isFinite(total) || total <= 0) return null
  return Math.round((earned / total) * 100)
}

export function durationInMinutes(value) {
  // В базе встречаются «60 мин», «1 ч» и «1 ч 30 мин».
  const text = String(value || '')
    .toLowerCase()
    .replace(',', '.')
  const hours = text.match(/(\d+(?:\.\d+)?)\s*ч/)
  const minutes = text.match(/(\d+(?:\.\d+)?)\s*мин/)
  if (hours || minutes) {
    return Math.round(Number(hours?.[1] || 0) * 60 + Number(minutes?.[1] || 0))
  }
  // Старые отчёты могли хранить просто число минут.
  return Math.round(parseFloat(text) || 0)
}

export function formatHours(minutes) {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (!hours && !rest) return '0 ч'
  if (!hours) return `${rest} мин`
  if (!rest) return `${hours} ч`
  return `${hours} ч ${rest} мин`
}

export function sumReportMinutes(reports) {
  let total = 0
  for (const report of reports) {
    total += durationInMinutes(report.duration)
  }
  return total
}

export function uniqueNames(items, field) {
  const names = []
  for (const item of items) {
    const name = item[field]
    if (name && !names.includes(name)) names.push(name)
  }
  return names
}

export function safeLink(value) {
  try {
    const url = new URL(String(value || '').trim())
    if (url.protocol === 'http:' || url.protocol === 'https:') return url.href
  } catch {
    // Пустая или неправильная ссылка не должна открываться.
  }
  return ''
}

// Новый объект при каждом вызове: поля разных форм не будут связаны между собой.
export function emptyHomework() {
  return {
    assignment: '',
    title: '',
    subject: '',
    deadline: '',
    description: '',
    attachment: '',
    maxScore: 10,
  }
}

export function emptyLesson() {
  return {
    student: '',
    tutor: '',
    subject: '',
    date: '',
    time: '',
    duration: '60 мин',
    link: '',
    topic: '',
  }
}

export function emptyReport() {
  return { student: '', date: '', duration: '', topic: '', videoLink: '' }
}

