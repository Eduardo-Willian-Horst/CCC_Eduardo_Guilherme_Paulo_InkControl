import { TOKEN_STORAGE_KEY } from '../lib/constants'
import { formatApiError } from '../lib/apiError'

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setStoredToken(token) {
  if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token)
  else localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export async function apiFetch(path, { token, skipAuth, headers, ...init } = {}) {
  const authToken = token ?? getStoredToken()
  const h = new Headers(headers)
  const isFormData =
    typeof FormData !== 'undefined' && init.body != null && init.body instanceof FormData
  if (init.body && !isFormData && !h.has('Content-Type')) {
    h.set('Content-Type', 'application/json')
  }
  if (!skipAuth && authToken) {
    h.set('Authorization', `Token ${authToken}`)
  }

  const res = await fetch(path, { ...init, headers: h })
  const text = await res.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { detail: text }
    }
  }

  if (!res.ok) {
    const err = new Error(formatApiError(data))
    err.status = res.status
    err.code = data?.code
    err.body = data
    throw err
  }

  return data
}
