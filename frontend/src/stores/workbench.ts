/** 工作台 Pinia store：管理打开的请求标签页与流式发送。 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { streamPost } from '@/api/client'
import { parseUrlQuery } from '@/utils/parseCurl'
import type { CollectionNode, HttpRequestData, OpenTab } from '@/api/types'

let seq = 0
const uid = () => `t_${Date.now().toString(36)}_${(seq++).toString(36)}`

const blankRequest = (): HttpRequestData => ({
  method: 'GET',
  url: '',
  headers: [{ key: '', value: '', enabled: true }],
  params: [{ key: '', value: '', enabled: true }],
  body_type: 'none',
  body: '',
})

function blankTab(kind: 'http' | 'websocket' | 'mcp' = 'http'): OpenTab {
  return {
    id: uid(),
    title: kind === 'websocket' ? 'WebSocket' : kind === 'mcp' ? 'MCP' : 'New Request',
    kind,
    request: blankRequest(),
    ws_url: 'wss://',
    mcp_url: '',
    mcp_headers: {},
    mcp_tool: '',
    mcp_args: '{}',
    mcp_loading: false,
    mcp_result: '',
    streaming: false,
    error: '',
    status_code: 0,
    status_text: '',
    headers: {},
    body: '',
    elapsed_ms: 0,
    size_bytes: 0,
    stream_events: [],
  }
}

export const useWorkbenchStore = defineStore('workbench', () => {
  const tabs = ref<OpenTab[]>([])
  const activeId = ref<string | null>(null)
  let controller: AbortController | null = null

  const activeTab = ref<OpenTab | null>(null)

  function setActive(id: string) {
    activeId.value = id
    activeTab.value = tabs.value.find((t) => t.id === id) || null
  }

  function openBlank(kind: 'http' | 'websocket' | 'mcp' = 'http') {
    const tab = blankTab(kind)
    tabs.value.push(tab)
    setActive(tab.id)
  }

  function openFromNode(node: CollectionNode) {
    if (node.type !== 'request') return
    const existing = tabs.value.find((t) => t.nodeId === node.id)
    if (existing) {
      setActive(existing.id)
      return
    }
    const kind = node.kind === 'websocket' ? 'websocket' : node.kind === 'mcp' ? 'mcp' : 'http'
    const tab = blankTab(kind)
    tab.nodeId = node.id
    tab.title = node.name
    if (node.kind === 'websocket') {
      tab.ws_url = node.ws_url || 'wss://'
    } else if (node.kind === 'mcp') {
      tab.mcp_url = node.mcp_url || ''
      tab.mcp_headers = node.mcp_headers || {}
      tab.mcp_tool = node.mcp_tool || ''
      tab.mcp_args = node.mcp_args || '{}'
    } else if (node.request) {
      tab.request = JSON.parse(JSON.stringify(node.request))
    }
    tabs.value.push(tab)
    setActive(tab.id)
  }

  function closeTab(id: string) {
    const idx = tabs.value.findIndex((t) => t.id === id)
    if (idx < 0) return
    tabs.value.splice(idx, 1)
    if (activeId.value === id) {
      const next = tabs.value[idx] || tabs.value[idx - 1] || null
      activeId.value = next?.id || null
      activeTab.value = next
    }
  }

  function resetResponse(tab: OpenTab) {
    tab.streaming = false
    tab.error = ''
    tab.status_code = 0
    tab.status_text = ''
    tab.headers = {}
    tab.body = ''
    tab.elapsed_ms = 0
    tab.size_bytes = 0
    tab.stream_events = []
  }

  function pushEvent(tab: OpenTab, type: string, data: string) {
    const time = new Date().toLocaleTimeString('zh-CN', { hour12: false }) +
      '.' + String(Date.now() % 1000).padStart(3, '0')
    tab.stream_events.push({ time, type, data })
  }

  async function send(tab: OpenTab, persist?: (req: HttpRequestData) => void) {
    resetResponse(tab)
    tab.streaming = true
    controller = new AbortController()
    try {
      // URL 输入框保留完整 URL（含 query），发送时剥离 query，由后端用 params 重新拼接，避免重复参数
      const { baseUrl } = parseUrlQuery(tab.request.url)
      const payload: HttpRequestData = { ...tab.request, url: baseUrl }
      await streamPost('/api/http/stream', payload, (ev) => {
        const type = ev.type
        if (type === 'meta') {
          tab.status_code = ev.status_code as number
          tab.status_text = (ev.status_text as string) || ''
          tab.headers = (ev.headers as Record<string, string>) || {}
          pushEvent(tab, 'meta', `${tab.status_code} ${tab.status_text}`)
        } else if (type === 'chunk') {
          const data = (ev.data as string) || ''
          tab.body += data
          pushEvent(tab, 'chunk', data)
        } else if (type === 'done') {
          tab.elapsed_ms = ev.elapsed_ms as number
          tab.size_bytes = ev.size_bytes as number
          pushEvent(tab, 'done', `${tab.elapsed_ms} ms, ${tab.size_bytes} B`)
        } else if (type === 'error') {
          tab.error = (ev.message as string) || '请求出错'
          pushEvent(tab, 'error', tab.error)
        }
      }, controller.signal)
      persist?.(tab.request)
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        tab.error = (e as Error).message
      }
    } finally {
      tab.streaming = false
      controller = null
    }
  }

  function cancel() {
    controller?.abort()
  }

  function renameTab(id: string, title: string) {
    const t = tabs.value.find((x) => x.id === id)
    if (t) t.title = title
  }

  return {
    tabs,
    activeId,
    activeTab,
    setActive,
    openBlank,
    openFromNode,
    closeTab,
    send,
    cancel,
    renameTab,
  }
})
