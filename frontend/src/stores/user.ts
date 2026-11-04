/** 用户身份：登录态存 localStorage。 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api, clearSession, getStoredUser, setSession, updateStoredUser } from '@/api/client'
import type { SessionUser } from '@/api/client'

export interface LoggedInUser extends SessionUser {
  avatar?: string
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

  /** 同步服务端返回的用户信息到内存与 localStorage。 */
  function applyUser(next: LoggedInUser) {
    user.value = next
    updateStoredUser(next)
  }

  /** 修改个人信息：昵称 + 头像（base64 data URL，空串表示清除）。 */
  async function updateProfile(payload: { display_name: string; avatar: string }) {
    const res = await api.put<{ user: LoggedInUser }>('/api/auth/profile', payload)
    applyUser(res.user)
    return res.user
  }

  /** 修改密码（需提供当前密码，后端会做强度校验）。 */
  async function changePassword(oldPassword: string, newPassword: string) {
    await api.put('/api/auth/password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
  }

  /**
   * 从服务端拉取最新用户信息（含头像），失败时忽略。
   * 用于登录后同步其它设备上修改过的昵称 / 头像。
   */
  async function refresh() {
    if (!user.value) return
    try {
      const res = await api.get<{ user: LoggedInUser }>('/api/auth/me')
      if (res?.user) applyUser(res.user)
    } catch {
      // 网络异常时保留本地缓存
    }
  }

  return { user, needsLogin, login, register, logout, updateProfile, changePassword, refresh }
})
