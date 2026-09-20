/** 共享 HTTP API 客户端：所有请求走 Vite 代理或后端同源。 */

export interface ApiError {
  detail: string
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
  })
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
