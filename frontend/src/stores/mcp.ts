/** MCP 客户端 Pinia store。 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/api/client'

export interface McpServer {
  name: string
  url: string
  headers: Record<string, string>
}

export interface McpTool {
  name: string
  description: string
  input_schema: Record<string, unknown>
}

export interface McpCallResult {
  server: string
  tool: string
  is_error: boolean
  content: Array<Record<string, unknown>>
  error: string | null
}

export interface McpTestResult {
  ok: boolean
  message: string
  server_info: { name: string; version: string; protocol_version: string } | null
}

export interface McpCallRecord {
  server: string
  tool: string
  args: Record<string, unknown>
  is_error: boolean
  content: Array<Record<string, unknown>>
  error: string | null
  timestamp: string
}

export const useMcpStore = defineStore('mcp', () => {
  const servers = ref<McpServer[]>([])
  const selectedServer = ref<string>('')
  const tools = ref<McpTool[]>([])
  const lastResult = ref<McpCallResult | null>(null)
  const history = ref<McpCallRecord[]>([])
  const loading = ref(false)
  const error = ref('')

  async function loadServers() {
    servers.value = await api.get<McpServer[]>('/api/mcp/servers')
  }

  async function addServer(server: McpServer) {
    await api.post('/api/mcp/servers', server)
    await loadServers()
  }

  async function updateServer(name: string, server: McpServer) {
    await api.put(`/api/mcp/servers/${name}`, server)
    await loadServers()
  }

  async function deleteServer(name: string) {
    await api.del(`/api/mcp/servers/${name}`)
    if (selectedServer.value === name) selectedServer.value = ''
    tools.value = []
    await loadServers()
  }

  async function testServer(name: string): Promise<McpTestResult> {
    return api.post<McpTestResult>(`/api/mcp/servers/${name}/test`, {})
  }

  async function loadTools(name: string) {
    selectedServer.value = name
    tools.value = []
    error.value = ''
    try {
      tools.value = await api.get<McpTool[]>(`/api/mcp/servers/${name}/tools`)
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function callTool(name: string, tool: string, args: Record<string, unknown>) {
    loading.value = true
    error.value = ''
    lastResult.value = null
    try {
      lastResult.value = await api.post<McpCallResult>(
        `/api/mcp/servers/${name}/tools/${tool}/call`,
        args,
      )
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function loadHistory() {
    history.value = await api.get<McpCallRecord[]>('/api/mcp/history')
  }

  async function adHocTools(url: string, headers: Record<string, string>): Promise<McpTool[]> {
    return api.post<McpTool[]>('/api/mcp/ad-hoc/tools', { url, headers })
  }

  async function adHocCall(
    url: string,
    headers: Record<string, string>,
    tool: string,
    args: Record<string, unknown>,
  ): Promise<McpCallResult> {
    return api.post<McpCallResult>('/api/mcp/ad-hoc/call', { url, headers, tool, args })
  }

  return {
    servers,
    selectedServer,
    tools,
    lastResult,
    history,
    loading,
    error,
    loadServers,
    addServer,
    updateServer,
    deleteServer,
    testServer,
    loadTools,
    callTool,
    loadHistory,
    adHocTools,
    adHocCall,
  }
})

if (import.meta.hot) import.meta.hot.accept(acceptHMRUpdate(useMcpStore, import.meta.hot))
