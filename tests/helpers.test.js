import { test } from 'node:test'
import assert from 'node:assert/strict'
import { durationInMinutes, formatHours, initialsFromName, safeLink, uniqueNames } from '../src/helpers.js'
import { navigation, roles } from '../src/config.js'

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

test('Удалённого раздела целей нет в меню и поиске ни одной роли', () => {
  for (const role of Object.keys(roles)) {
    const pages = navigation.filter((page) => page.roles.includes(role))
    assert.equal(pages.some((page) => page.to === '/goals'), false)
    assert.equal(pages.some((page) => page.label === 'Цели'), false)
  }
})
