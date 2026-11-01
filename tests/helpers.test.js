import { test } from 'node:test'
import assert from 'node:assert/strict'
import { durationInMinutes, formatHours, goalPercent, initialsFromName, safeLink, uniqueNames } from '../src/helpers.js'

test('Инициалы берутся из первых двух слов', () => {
  assert.equal(initialsFromName(' Мария Сагалаева '), 'МС')
  assert.equal(initialsFromName(''), 'УЧ')
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

test('Процент цели зависит от выполненных шагов', () => {
  assert.equal(goalPercent({}), 0)
  assert.equal(goalPercent({ tasks: [] }), 0)
  assert.equal(goalPercent({ tasks: [{ done: true }, { done: false }, { done: false }] }), 33)
  assert.equal(goalPercent({ tasks: [{ done: true }] }), 100)
})
