import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  countText,
  durationInMinutes,
  formatHours,
  initialsFromName,
  safeLink,
  scorePercent,
  uniqueNames,
} from '../src/helpers.js'
import { navigation, roles } from '../src/config.js'

test('Инициалы берутся из первых двух слов', () => {
  assert.equal(initialsFromName(' Мария Сагалаева '), 'МС')
  assert.equal(initialsFromName(''), 'УЧ')
})

test('Окончания подписей верны для одного, нескольких и многих элементов', () => {
  const cases = [
    [0, 'отчётов'], [1, 'отчёт'], [2, 'отчёта'], [4, 'отчёта'],
    [5, 'отчётов'], [11, 'отчётов'], [12, 'отчётов'], [14, 'отчётов'],
    [21, 'отчёт'], [22, 'отчёта'], [25, 'отчётов'], [101, 'отчёт'],
    [111, 'отчётов'], [112, 'отчётов'],
  ]
  for (const [count, word] of cases) {
    assert.equal(countText(count, 'отчёт', 'отчёта', 'отчётов'), `${count} ${word}`)
  }
  assert.equal(countText(5, 'раздел', 'раздела', 'разделов'), '5 разделов')
})

test('Списки имён сохраняют порядок без повторов и пустых значений', () => {
  const rows = [{ name: 'Антон' }, { name: '' }, { name: 'Антон' }, { name: 'Мария' }]
  assert.deepEqual(uniqueNames(rows, 'name'), ['Антон', 'Мария'])
})

test('Открываются только обычные ссылки на сайты', () => {
  assert.equal(safeLink(' https://example.com/video '), 'https://example.com/video')
  for (const value of ['', null, 'не ссылка', 'javascript:alert(1)', 'file:///etc/passwd']) {
    assert.equal(safeLink(value), '')
  }
})

test('Длительность и часы считаются в минутах', () => {
  assert.equal(durationInMinutes('1 ч 30 мин'), 90)
  assert.equal(durationInMinutes('1,5 ч'), 90)
  assert.equal(durationInMinutes('45'), 45)
  assert.equal(formatHours(0), '0 ч')
  assert.equal(formatHours(45), '45 мин')
  assert.equal(formatHours(60), '1 ч')
  assert.equal(formatHours(105), '1 ч 45 мин')
})

test('Баллы переводятся в проценты без изменения сохранённых оценок', () => {
  const cases = [
    ['8 / 10', 80], ['1,5 / 2', 75], ['0 / 10', 0],
    ['12 / 10', 120], [' 3 / 4 ', 75], ['1 / 2.5', 40],
  ]
  for (const [score, percent] of cases) {
    assert.equal(scorePercent(score), percent)
  }
})

test('Пустые и неправильные оценки не участвуют в среднем результате', () => {
  const scores = [
    null, '', '8', 'хорошо', '8 / 0', '/ 10', '8 /', '8 / 10 / 2',
    '-1 / 10', '+1 / 10', '1e2 / 10', '.5 / 10', '5. / 10',
    `${'9'.repeat(400)} / 10`,
  ]
  for (const score of scores) assert.equal(scorePercent(score), null)
})

test('Меню и поиск содержат только доступные разделы', () => {
  const routes = new Set([
    '/dashboard', '/users', '/schedule', '/homework', '/progress', '/chats',
    '/hours', '/lessons-control', '/reports', '/profile', '/notifications', '/help',
  ])
  for (const role of Object.keys(roles)) {
    const pages = navigation.filter((page) => page.roles.includes(role))
    assert.equal(pages.every((page) => routes.has(page.to)), true)
    assert.equal(new Set(pages.map((page) => page.to)).size, pages.length)
  }
})
