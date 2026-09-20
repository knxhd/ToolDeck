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
