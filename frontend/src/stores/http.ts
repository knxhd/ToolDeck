/** HTTP 工作台 Pinia store。 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/api/client'
import type {
  HttpCallRecord,
  HttpRequestData,
  HttpResponseData,
} from '@/api/types'

const emptyRequest = (): HttpRequestData => ({
  method: 'GET',
  url: '',
  headers: [{ key: '', value: '', enabled: true }],
  params: [{ key: '', value: '', enabled: true }],
  body_type: 'none',
  body: '',
})

export const useHttpStore = defineStore('http', () => {
  const request = ref<HttpRequestData>(emptyRequest())
  const response = ref<HttpResponseData | null>(null)
  const history = ref<HttpCallRecord[]>([])
  const loading = ref(false)
  const error = ref('')

  async function send() {
    loading.value = true
    error.value = ''
    response.value = null
    try {
      response.value = await api.post<HttpResponseData>('/api/http/send', request.value)
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function loadHistory() {
    history.value = await api.get<HttpCallRecord[]>('/api/http/history')
  }

  async function clearHistory() {
    await api.del('/api/http/history')
    await loadHistory()
  }

  function loadFromHistory(record: HttpCallRecord) {
    request.value = {
      method: record.method as HttpRequestData['method'],
      url: record.url,
      headers: record.headers?.length ? record.headers : [{ key: '', value: '', enabled: true }],
      params: [{ key: '', value: '', enabled: true }],
      body_type: (record.body_type as HttpRequestData['body_type']) || 'none',
      body: record.body || '',
    }
  }

  function reset() {
    request.value = emptyRequest()
    response.value = null
    error.value = ''
  }

  return { request, response, history, loading, error, send, loadHistory, clearHistory, loadFromHistory, reset }
})

if (import.meta.hot) import.meta.hot.accept(acceptHMRUpdate(useHttpStore, import.meta.hot))
