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

/**
 * Form Data 字段（以 JSON 数组形式存在 body 中）。
 * type = file 时 value 为本机文件路径，发送时由后端读取文件并以 multipart 上传。
 */
export interface FormDataItem extends KeyValue {
  type: 'text' | 'file'
}

export interface HttpRequestData {
  method: HttpMethod
  url: string
  headers: KeyValue[]
  params: KeyValue[]
  body_type: BodyType
  body: string
  /** 鉴权配置：发送时自动注入对应 header。 */
  auth?: AuthConfig
  /**
   * 请求级占位符（长文本变量，如系统提示词）：在 url / params / headers / body 中用 {{key}} 引用。
   * 仅前端使用，发送前已插值，不会提交给后端。
   */
  placeholders?: KeyValue[]
  /** 接口文档（Markdown），仅前端展示与随集合保存，不会提交给后端。 */
  docs?: string
  /** 超时秒数（默认 30）。 */
  timeout?: number
  /** 跟随重定向（默认 false）。 */
  follow_redirects?: boolean
  /** 校验 SSL 证书（默认 true）。 */
  verify_ssl?: boolean
  /** 批量测试配置：随接口一起保存，切回该接口时自动恢复。 */
  bench?: BenchConfig
}

/** 批量测试（压测）配置。 */
export interface BenchConfig {
  /** 选用的测试集 id */
  dataset_id?: string
  /** 并发数 */
  concurrency?: number
  /** 是否按 SSE 流式统计 */
  streaming?: boolean
  /** 自定义结果列（CSV 追加列） */
  columns?: Array<{ title: string; path: string }>
  /** 要写进结果 CSV 的测试集输入列（原列名，只写勾选的） */
  input_cols?: string[]
  /** 任务名称前缀 */
  name?: string
}

/** 鉴权配置。 */
export interface AuthConfig {
  type: 'none' | 'bearer' | 'basic' | 'apikey'
  /** Bearer Token */
  token?: string
  /** Basic Auth */
  username?: string
  password?: string
  /** API Key：header 名 */
  key?: string
  /** API Key：值 */
  value?: string
  /** API Key 放在 header 还是 query */
  addTo?: 'header' | 'query'
}

/** 接口文档显示模式：edit 仅编辑 / split 左右分屏（实时预览）/ preview 仅预览。 */
export type DocMode = 'edit' | 'split' | 'preview'

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
  /** 仅 collection 节点：集合级占位符，集合内所有请求可用 {{key}} 引用 */
  placeholders?: KeyValue[]
}

/** 工作台中一个打开的标签页。 */
export interface OpenTab {
  id: string
  title: string
  kind: 'http' | 'websocket' | 'mcp'
  nodeId?: string
  /** 是否有未保存的修改（仅 HTTP）。 */
  dirty?: boolean
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
