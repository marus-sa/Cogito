import { beforeEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../src/stores/auth.js'
import { useLessonsStore } from '../src/stores/lessons.js'
import { useHomeworkStore } from '../src/stores/homework.js'
import { useMessagesStore } from '../src/stores/messages.js'
import { api } from '../src/api.js'

const firstUser = { id: 1, name: 'Первый Участник', role: 'student', accountStatus: 'active' }
const secondUser = { id: 2, name: 'Второй Участник', role: 'parent', accountStatus: 'active' }
const response = (body, status = 200) => ({ ok: status < 400, status, json: async () => body })

beforeEach(() => {
  setActivePinia(createPinia())
  globalThis.window = new EventTarget()
})

test('Файл отправляется как FormData без подмены на JSON', async () => {
  const body = new FormData()
  body.append('comment', 'Моя работа')
  body.append('files', new Blob(['answer']), 'answer.txt')
  globalThis.fetch = async (url, request) => {
    assert.equal(url, '/api/homework/1/submit')
    assert.equal(request.body, body)
    assert.equal(request.headers['Content-Type'], undefined)
    assert.equal(request.credentials, 'same-origin')
    return response({ item: { id: 1, submissionFiles: [] } })
  }
  await api('/homework/1/submit', { method: 'PATCH', body })
})

test('Загрузка домашних заданий не обращается к удалённым целям', async () => {
  const requests = []
  globalThis.fetch = async (url) => {
    requests.push(url)
    return response({ items: [{ id: 42, title: 'Задание' }] })
  }
  const homework = useHomeworkStore()
  await homework.loadHomework()
  assert.deepEqual(requests, ['/api/homework'])
  assert.equal(homework.homework[0].id, 42)
  assert.equal('goals' in homework.$state, false)
})

test('Вход использует роль сервера и обычный объект запроса', async () => {
  globalThis.fetch = async (url, request) => {
    assert.equal(url, '/api/auth/login')
    assert.deepEqual(JSON.parse(request.body), {
      email: 'user@example.test',
      password: 'test-password',
      remember: true,
    })
    assert.equal(request.credentials, 'same-origin')
    assert.equal(request.cache, 'no-store')
    return response({ user: secondUser })
  }
  const auth = useAuthStore()
  await auth.login('user@example.test', 'test-password', true)
  assert.equal(auth.roleKey, 'parent')
  assert.equal(auth.isAuthenticated, true)
})

test('Смена аккаунта и выход очищают учебные данные и переписку', () => {
  const auth = useAuthStore()
  auth.setLogin(firstUser)
  useLessonsStore().lessons = [{ id: 1 }]
  useHomeworkStore().homework = [{ id: 1 }]
  useMessagesStore().messages = [{ text: 'Личное сообщение' }]
  auth.setLogin(secondUser)
  assert.deepEqual(useLessonsStore().lessons, [])
  assert.deepEqual(useHomeworkStore().homework, [])
  assert.deepEqual(useMessagesStore().messages, [])
  auth.clearLogin()
  assert.equal(auth.profile, null)
  assert.equal(auth.isAuthenticated, false)
})

test('Поздний ответ старого аккаунта не возвращается в новый кабинет', async () => {
  const auth = useAuthStore()
  auth.setLogin(firstUser)
  let finishRequest
  globalThis.fetch = () =>
    new Promise((resolve) => {
      finishRequest = resolve
    })
  const pending = api('/lessons')
  auth.setLogin(secondUser)
  finishRequest(response({ items: [{ student: 'Первый Участник' }] }))
  await assert.rejects(pending, /Аккаунт изменился/)
})

test('При недоступном сервере выход не выдаёт ложное сообщение об успехе', async () => {
  const auth = useAuthStore()
  auth.setLogin(firstUser)
  globalThis.fetch = async () => {
    throw new Error('Нет сети')
  }
  await assert.rejects(auth.logout(), /Нет сети/)
  assert.equal(auth.isAuthenticated, true)
  globalThis.fetch = async () => response({ ok: true })
  await auth.logout()
  assert.equal(auth.isAuthenticated, false)
})

test('Сессия восстанавливается с сервера, а просроченная закрывается', async () => {
  const auth = useAuthStore()
  globalThis.fetch = async () => response({ user: firstUser })
  assert.equal(await auth.restore(), true)
  globalThis.fetch = async () => response({ error: 'Сначала войдите' }, 401)
  assert.equal(await auth.restore(), false)
  assert.equal(auth.profile, null)
})

test('Ошибка 401 у защищённого действия сообщает о завершении сессии', async () => {
  let events = 0
  window.addEventListener('cogito:session-expired', () => {
    events += 1
  })
  globalThis.fetch = async () => response({ error: 'Сначала войдите' }, 401)
  await assert.rejects(api('/lessons'))
  assert.equal(events, 1)
})

test('Запоздалое восстановление сессии не подменяет новый аккаунт', async () => {
  const auth = useAuthStore()
  auth.setLogin(firstUser)
  let finishRequest
  globalThis.fetch = () =>
    new Promise((resolve) => {
      finishRequest = resolve
    })
  const pending = auth.restore()
  auth.setLogin(secondUser)
  finishRequest(response({ user: firstUser }))
  assert.equal(await pending, true)
  assert.equal(auth.profile.id, secondUser.id)
})
