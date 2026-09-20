/** LLM 调用 Pinia store。 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/api/client'

export interface LlmProvider {
  name: string
  base_url: string
  api_key: string
  model: string
  provider_type: 'openai' | 'anthropic' | 'custom'
  options: Record<string, unknown>
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatResponse {
  content: string
  finish_reason: string
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number }
  model: string
}

export interface LlmCallRecord {
  provider: string
  model: string
  messages: ChatMessage[]
  content: string
  finish_reason: string
  usage: Record<string, number>
  stream?: boolean
  timestamp: string
}

/** 掩码 api_key，仅显示前后各 4 字符。 */
export function maskApiKey(key: string): string {
  if (!key) return ''
  if (key.length <= 8) return '***'
  return `${key.slice(0, 4)}***${key.slice(-4)}`
}

export const useLlmStore = defineStore('llm', () => {
  const providers = ref<LlmProvider[]>([])
  const selectedProvider = ref<string>('')
  const messages = ref<ChatMessage[]>([{ role: 'user', content: '' }])
  const streamingText = ref('')
  const streaming = ref(false)
  const streamInterrupted = ref(false)
  const lastUsage = ref('')
  const history = ref<LlmCallRecord[]>([])
  const error = ref('')

  async function loadProviders() {
    providers.value = await api.get<LlmProvider[]>('/api/llm/providers')
  }

  async function addProvider(p: LlmProvider) {
    await api.post('/api/llm/providers', p)
    await loadProviders()
  }

  async function updateProvider(name: string, p: LlmProvider) {
    await api.put(`/api/llm/providers/${name}`, p)
    await loadProviders()
  }

  async function deleteProvider(name: string) {
    await api.del(`/api/llm/providers/${name}`)
    if (selectedProvider.value === name) selectedProvider.value = ''
    await loadProviders()
  }

  /** 同步调用 */
  async function chatSync(temperature: number) {
    if (!selectedProvider.value) return
    error.value = ''
    const res = await api.post<ChatResponse>('/api/llm/chat', {
      provider_name: selectedProvider.value,
      messages: messages.value,
      stream: false,
      temperature,
    })
    // 追加 assistant 消息
    messages.value.push({ role: 'assistant', content: res.content })
    lastUsage.value = `tokens: ${res.usage?.total_tokens ?? 0}`
  }

  /** 流式调用：fetch + ReadableStream 解析 SSE */
  async function chatStream(temperature: number) {
    if (!selectedProvider.value) return
    streaming.value = true
    streamInterrupted.value = false
    streamingText.value = ''
    error.value = ''
    try {
      const res = await fetch('/api/llm/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_name: selectedProvider.value,
          messages: messages.value,
          stream: true,
          temperature,
        }),
      })
      if (!res.ok || !res.body) {
        const txt = await res.text()
        throw new Error(txt || `${res.status}`)
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let finishReason = ''
      // 预先放入一条空 assistant 消息用于增量追加
      messages.value.push({ role: 'assistant', content: '' })
      const assistantIdx = messages.value.length - 1
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const data = line.slice(5).trim()
          if (!data) continue
          try {
            const evt = JSON.parse(data)
            if (evt.error) {
              streamInterrupted.value = true
              error.value = evt.error
            }
            if (evt.delta) {
              streamingText.value += evt.delta
              messages.value[assistantIdx].content += evt.delta
            }
            if (evt.finish_reason) finishReason = evt.finish_reason
          } catch {
            // 忽略解析错误
          }
        }
      }
      if (finishReason) lastUsage.value = `finish: ${finishReason}`
    } catch (e) {
      streamInterrupted.value = true
      error.value = (e as Error).message
    } finally {
      streaming.value = false
    }
  }

  function addMessage(role: ChatMessage['role']) {
    messages.value.push({ role, content: '' })
  }

  function removeMessage(index: number) {
    messages.value.splice(index, 1)
  }

  function clearMessages() {
    messages.value = [{ role: 'user', content: '' }]
    streamingText.value = ''
    lastUsage.value = ''
    error.value = ''
  }

  async function loadHistory() {
    history.value = await api.get<LlmCallRecord[]>('/api/llm/history')
  }

  return {
    providers,
    selectedProvider,
    messages,
    streamingText,
    streaming,
    streamInterrupted,
    lastUsage,
    history,
    error,
    loadProviders,
    addProvider,
    updateProvider,
    deleteProvider,
    chatSync,
    chatStream,
    addMessage,
    removeMessage,
    clearMessages,
    loadHistory,
  }
})
