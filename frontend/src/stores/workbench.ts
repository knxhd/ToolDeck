/** 工作台 Pinia store：管理打开的请求标签页与流式发送。 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import { streamPost } from '@/api/client'
import { useCollectionsStore } from './collections'
import { useEnvironmentsStore } from './environments'
import { missingVars, resolveRequest } from '@/utils/env'
import { parseUrlQuery } from '@/utils/parseCurl'
import { toast } from '@/utils/feedback'
import type { CollectionNode, HttpRequestData, OpenTab } from '@/api/types'

let seq = 0
const uid = () => `t_${Date.now().toString(36)}_${(seq++).toString(36)}`

const STORAGE_KEY = 'api-tool.tabs.v1'

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
    dirty: false,
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

/** 持久化到 localStorage 的精简结构。 */
interface PersistedTab {
  id: string
  title: string
  kind: 'http' | 'websocket' | 'mcp'
  nodeId?: string
  dirty?: boolean
  /** 临时 tab（无 nodeId）才存完整请求数据 */
  request?: HttpRequestData
  ws_url?: string
  mcp_url?: string
  mcp_headers?: Record<string, string>
  mcp_tool?: string
  mcp_args?: string
}

function serializeTabs(tabs: OpenTab[], activeId: string | null): { activeId: string | null; tabs: PersistedTab[] } {
  return {
    activeId,
    tabs: tabs.map((t) => {
      const out: PersistedTab = { id: t.id, title: t.title, kind: t.kind, dirty: t.dirty }
      if (t.nodeId) {
        out.nodeId = t.nodeId
      } else {
        // 临时 tab：完整保存
        out.request = JSON.parse(JSON.stringify(t.request))
        if (t.kind === 'websocket') out.ws_url = t.ws_url
        if (t.kind === 'mcp') {
          out.mcp_url = t.mcp_url
          out.mcp_headers = { ...t.mcp_headers }
          out.mcp_tool = t.mcp_tool
          out.mcp_args = t.mcp_args
        }
      }
      return out
    }),
  }
}

function saveToStorage(tabs: OpenTab[], activeId: string | null) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(serializeTabs(tabs, activeId)))
  } catch {
    /* 配额满等情况忽略 */
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
      // 变量插值（优先级：请求占位符 > 集合占位符 > 环境变量），替换 url/headers/params/body 中的 {{var}}
      const env = useEnvironmentsStore()
      const resolved = resolveRequest(tab.request, env.scopeVars)

      // 发送前提醒未定义的占位符（不阻断请求）：插值后仍残留的 {{var}} 即为未定义
      const resolvedText = [
        resolved.url,
        resolved.body || '',
        ...(resolved.headers || []).filter((h) => h.enabled).map((h) => h.value),
        ...(resolved.params || []).filter((p) => p.enabled).map((p) => p.value),
      ].join('\n')
      const missing = [...new Set(missingVars(resolvedText, {}))]
      if (missing.length) toast.warning(`未定义的变量：${missing.join(', ')}`)

      // URL 输入框保留完整 URL（含 query），发送时剥离 query，由后端用 params 重新拼接，避免重复参数
      const { baseUrl } = parseUrlQuery(resolved.url)
      const payload: HttpRequestData = { ...resolved, url: baseUrl }
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

  /** 集合树里节点被重命名后，同步更新已打开该节点的 tab 标题。 */
  function syncTitleByNodeId(nodeId: string, title: string) {
    const t = tabs.value.find((x) => x.nodeId === nodeId)
    if (t) t.title = title
  }

  /**
   * 从 localStorage 恢复上次打开的 tabs。需在 collections.load() 之后调用，
   * 因为 nodeId 类型的 tab 要从集合树重新加载节点数据；节点不存在则丢弃。
   */
  function restore() {
    let saved: { activeId: string | null; tabs: PersistedTab[] } | null = null
    try {
      saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    } catch {
      saved = null
    }
    if (!saved || !Array.isArray(saved.tabs) || saved.tabs.length === 0) return

    const collections = useCollectionsStore()
    const restored: OpenTab[] = []
    for (const p of saved.tabs) {
      const tab = blankTab(p.kind || 'http')
      tab.id = p.id
      tab.title = p.title
      tab.dirty = p.dirty
      if (p.nodeId) {
        // 节点类型：从集合树重新加载
        const node = collections.findNode(p.nodeId)
        if (!node || node.type !== 'request') continue // 节点已删，丢弃
        tab.nodeId = node.id
        tab.title = node.name
        if (node.kind === 'websocket') tab.ws_url = node.ws_url || 'wss://'
        else if (node.kind === 'mcp') {
          tab.mcp_url = node.mcp_url || ''
          tab.mcp_headers = node.mcp_headers || {}
          tab.mcp_tool = node.mcp_tool || ''
          tab.mcp_args = node.mcp_args || '{}'
        } else if (node.request) tab.request = JSON.parse(JSON.stringify(node.request))
      } else {
        // 临时 tab：用保存的请求数据
        if (p.request) tab.request = JSON.parse(JSON.stringify(p.request))
        if (p.ws_url) tab.ws_url = p.ws_url
        if (p.mcp_url) tab.mcp_url = p.mcp_url
        if (p.mcp_headers) tab.mcp_headers = { ...p.mcp_headers }
        if (p.mcp_tool) tab.mcp_tool = p.mcp_tool
        if (p.mcp_args) tab.mcp_args = p.mcp_args
      }
      restored.push(tab)
    }
    tabs.value = restored
    // 恢复 activeId（如果存在）
    const active = saved.activeId && restored.find((t) => t.id === saved.activeId)
    if (active) {
      activeId.value = active.id
      activeTab.value = active
    } else if (restored.length) {
      activeId.value = restored[restored.length - 1].id
      activeTab.value = restored[restored.length - 1]
    }
  }

  // 自动持久化：tabs 结构变化（增删/重命名/切 active）和临时 tab 的 request 变化都触发
  // 用 computed 投影避免 deep watch stream_events 这种高频大数组
  const persistKey = computed(() => JSON.stringify(serializeTabs(tabs.value, activeId.value)))
  watch(persistKey, () => saveToStorage(tabs.value, activeId.value))

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
    syncTitleByNodeId,
    restore,
  }
})

// 开发态热更新：替换已创建的 store 实例，否则修改 store 后页面仍使用旧逻辑
if (import.meta.hot) import.meta.hot.accept(acceptHMRUpdate(useWorkbenchStore, import.meta.hot))
