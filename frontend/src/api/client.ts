/** 共享 HTTP API 客户端：所有请求走 Vite 代理或后端同源。 */

export interface ApiError {
  detail: string
}

const TOKEN_KEY = 'api-tool.token'
const USER_KEY = 'api-tool.user'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setSession(token: string, user: { id: number; username: string; display_name: string }) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getStoredUser(): { id: number; username: string; display_name: string } | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function authHeaders(): Record<string, string> {
  const t = getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(options?.headers || {}),
    },
    ...options,
  })
  if (res.status === 401) {
    clearSession()
    // 让页面刷新回到登录页
    location.reload()
    throw new Error('登录已过期')
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const err = (await res.json()) as ApiError
      detail = err.detail || detail
    } catch {
      // 非 JSON 错误
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  get: <T>(url: string) => request<T>(url, { method: 'GET' }),
  post: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  del: <T>(url: string) => request<T>(url, { method: 'DELETE' }),
}

/**
 * 流式 POST：按 NDJSON 逐行解析，每行回调一个事件。
 */
export async function streamPost(
  url: string,
  body: unknown,
  onEvent: (event: Record<string, unknown>) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    location.reload()
    throw new Error('登录已过期')
  }
  if (!res.ok || !res.body) {
    let detail = `${res.status} ${res.statusText}`
    try {
      detail = ((await res.json()) as ApiError).detail || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx: number
    while ((idx = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, idx).trim()
      buffer = buffer.slice(idx + 1)
      if (line) {
        try {
          onEvent(JSON.parse(line) as Record<string, unknown>)
        } catch {
          // 忽略半行/坏行
        }
      }
    }
  }
}
