// Здесь собраны все запросы к Flask. Так в компонентах не повторяется fetch.
export async function api(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }

  const response = await fetch(`/api${url}`, { ...options, headers })
  let data = {}

  try {
    data = await response.json()
  } catch {
    data = { error: 'Сервер вернул непонятный ответ' }
  }

  if (!response.ok) throw new Error(data.error || 'Не получилось выполнить действие')

  return data
}
