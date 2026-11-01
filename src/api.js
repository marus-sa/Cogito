// Здесь собраны все запросы к Flask. Так в компонентах не повторяется fetch.
let accountVersion = 0

export function resetAccountRequests() {
  accountVersion += 1
}

export async function api(url, options = {}) {
  const requestVersion = accountVersion
  const request = {
    ...options,
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...options.headers },
  }
  // Страницы передают обычный объект. В JSON переводим только здесь.
  if (request.body && typeof request.body !== 'string') {
    request.body = JSON.stringify(request.body)
  }
  const response = await fetch(`/api${url}`, request)
  let data = {}

  try {
    data = await response.json()
  } catch {
    data = { error: 'Сервер вернул непонятный ответ' }
  }

  if (requestVersion !== accountVersion) {
    const error = new Error('Аккаунт изменился. Обновите данные страницы.')
    error.code = 'account_changed'
    throw error
  }

  if (!response.ok) {
    if (response.status === 401 && url !== '/auth/me' && url !== '/auth/login') {
      window.dispatchEvent(new Event('cogito:session-expired'))
    }
    const error = new Error(data.error || 'Не получилось выполнить действие')
    error.code = data.code
    error.status = response.status
    throw error
  }

  return data
}
