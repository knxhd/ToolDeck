/** 用户身份：登录态存 localStorage。 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api, clearSession, getStoredUser, setSession } from '@/api/client'

export interface LoggedInUser {
  id: number
  username: string
  display_name: string
}

export const useUserStore = defineStore('user', () => {
  const user = ref<LoggedInUser | null>(getStoredUser())
  const needsLogin = computed(() => !user.value)

  async function login(username: string, password: string) {
    const res = await api.post<{ token: string; user: LoggedInUser }>('/api/auth/login', {
      username,
      password,
    })
    setSession(res.token, res.user)
    user.value = res.user
  }

  async function register(username: string, password: string, displayName: string) {
    const res = await api.post<{ token: string; user: LoggedInUser }>('/api/auth/register', {
      username,
      password,
      display_name: displayName,
    })
    setSession(res.token, res.user)
    user.value = res.user
  }

  async function logout() {
    try {
      await api.post('/api/auth/logout')
    } catch {
      // ignore
    }
    clearSession()
    user.value = null
  }

  return { user, needsLogin, login, register, logout }
})
