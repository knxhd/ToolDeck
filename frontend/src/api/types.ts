/** HTTP 工作台类型定义。 */
export interface KeyValue {
  key: string
  value: string
  enabled: boolean
}

export type HttpMethod =
  | 'GET'
  | 'POST'
  | 'PUT'
  | 'DELETE'
  | 'PATCH'
  | 'HEAD'
  | 'OPTIONS'

export type BodyType = 'none' | 'json' | 'raw' | 'form-data'

export interface HttpRequestData {
  method: HttpMethod
  url: string
  headers: KeyValue[]
  params: KeyValue[]
  body_type: BodyType
  body: string
}

export interface HttpResponseData {
  status_code: number
  status_text: string
  headers: Record<string, string>
  body: string
  elapsed_ms: number
  size_bytes: number
  error: string | null
}

export interface HttpCallRecord {
  method: string
  url: string
  headers: KeyValue[]
  body_type: string
  body: string
  status_code: number
  elapsed_ms: number
  timestamp: string
}

/** 环境变量条目。 */
export interface EnvVariable {
  key: string
  value: string
  enabled: boolean
  description?: string
}

/** 一套环境（local / test / prod …），挂在 collection 根节点上。 */
export interface Environment {
  id: string
  name: string
  variables: EnvVariable[]
}

/** Collections 树节点：collection / folder / request。 */
export interface CollectionNode {
  id: string
  type: 'collection' | 'folder' | 'request'
  name: string
  children?: CollectionNode[]
  /** 仅 request 节点：http | websocket | mcp */
  kind?: 'http' | 'websocket' | 'mcp'
  /** 仅 http 请求节点 */
  request?: HttpRequestData
  /** 仅 websocket 请求节点 */
  ws_url?: string
  /** 仅 mcp 请求节点 */
  mcp_url?: string
  mcp_headers?: Record<string, string>
  mcp_tool?: string
  mcp_args?: string
  /** 仅 collection 节点：该集合下的多套环境 */
  environments?: Environment[]
  /** 仅 collection 节点：当前激活环境 id，null 表示不启用环境变量 */
  activeEnvId?: string | null
}

/** 工作台中一个打开的标签页。 */
export interface OpenTab {
  id: string
  title: string
  kind: 'http' | 'websocket' | 'mcp'
  nodeId?: string
  request: HttpRequestData
  ws_url: string
  // MCP 请求态
  mcp_url: string
  mcp_headers: Record<string, string>
  mcp_tool: string
  mcp_args: string
  mcp_loading: boolean
  mcp_result: string
  // HTTP 响应态
  streaming: boolean
  error: string
  status_code: number
  status_text: string
  headers: Record<string, string>
  body: string
  elapsed_ms: number
  size_bytes: number
  stream_events: Array<{ time: string; type: string; data: string }>
}
