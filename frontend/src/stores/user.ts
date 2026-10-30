/** 用户身份：本地存用户名，所有 API 请求带 X-User 头。 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/api/client'

const STORAGE_KEY = 'api-tool.username'

export const useUserStore = defineStore('user', () => {
  const name = ref<string>(localStorage.getItem(STORAGE_KEY) || '')
  /** 是否需要先选名字（首次打开 / 名字被清空）。 */
  const needsName = computed(() => !name.value)

  function setName(n: string) {
    name.value = n
    localStorage.setItem(STORAGE_KEY, n)
  }

  function logout() {
    name.value = ''
    localStorage.removeItem(STORAGE_KEY)
  }

  /** 检查用户名是否已有数据；已存在则返回 true。 */
  async function checkExists(n: string): Promise<boolean> {
    const res = await api.post<{ exists: boolean }>('/api/user/check', { username: n })
    return !!res.exists
  }

  return { name, needsName, setName, logout, checkExists }
})
