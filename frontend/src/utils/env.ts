/** 环境变量插值：把文本中的 {{key}} 占位符替换为当前环境里的值。 */
import type { HttpRequestData, KeyValue } from '@/api/types'

/** 匹配 {{ key }} / {{key}}，变量名允许字母数字、下划线、点、短横线。 */
const PLACEHOLDER_RE = /\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}/g

/** 最多递归替换轮数，避免变量值里又引用其它变量时死循环。 */
const MAX_ROUNDS = 5

/**
 * 用 vars 渲染 text 中的占位符。未匹配到的占位符原样保留（Postman 行为）。
 * 变量值若再次包含 {{other}}，会继续迭代替换，最多 MAX_ROUNDS 轮。
 */
export function renderVars(text: string, vars: Record<string, string>): string {
  if (!text) return text
  let out = text
  for (let i = 0; i < MAX_ROUNDS; i++) {
    let changed = false
    const next = out.replace(PLACEHOLDER_RE, (raw, name: string) => {
      if (Object.prototype.hasOwnProperty.call(vars, name)) {
        changed = true
        return vars[name]
      }
      return raw
    })
    out = next
    if (!changed) break
  }
  return out
}

/** 收集 text 中出现的、但 vars 里缺失的变量名，用于发送前提醒。 */
export function missingVars(text: string, vars: Record<string, string>): string[] {
  const missing = new Set<string>()
  for (const m of text.matchAll(new RegExp(PLACEHOLDER_RE.source, 'g'))) {
    const name = m[1]
    if (!Object.prototype.hasOwnProperty.call(vars, name)) missing.add(name)
  }
  return [...missing]
}

/** 合法的变量 / 占位符名称（与 PLACEHOLDER_RE 保持一致）。 */
export const VAR_NAME_RE = /^[A-Za-z0-9_.-]+$/

/**
 * 合并变量表：环境变量 + 请求级占位符（同名时占位符优先）。
 * 占位符文本内可再引用环境变量或其它占位符，引用在插值时递归展开。
 */
export function requestVars(
  req: Pick<HttpRequestData, 'placeholders'>,
  envVars: Record<string, string>,
): Record<string, string> {
  const out: Record<string, string> = { ...envVars }
  for (const p of req.placeholders || []) {
    const key = (p.key || '').trim()
    if (p.enabled && key) out[key] = p.value ?? ''
  }
  return out
}

/** 取变量的最终值（递归展开其中引用的其它变量）。 */
function finalValue(name: string, vars: Record<string, string>): string {
  return renderVars(vars[name], vars)
}

/**
 * JSON 感知的插值：占位符位于 JSON 字符串字面量内时，对变量值做 JSON 转义
 * （换行、制表符、引号、反斜杠等），保证替换后仍是合法 JSON；位于字符串外时原样插入。
 * 未定义的占位符原样保留。
 */
export function renderVarsJson(text: string, vars: Record<string, string>): string {
  if (!text) return text
  const re = /\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}/y
  let out = ''
  let inString = false
  let i = 0
  while (i < text.length) {
    const ch = text[i]
    if (ch === '{' && text[i + 1] === '{') {
      re.lastIndex = i
      const m = re.exec(text)
      if (m && Object.prototype.hasOwnProperty.call(vars, m[1])) {
        const value = finalValue(m[1], vars)
        out += inString ? JSON.stringify(value).slice(1, -1) : value
        i += m[0].length
        continue
      }
    }
    if (inString) {
      if (ch === '\\') {
        // 转义序列整体拷贝，避免 \" 被误判为字符串结束
        out += text.slice(i, i + 2)
        i += 2
        continue
      }
      if (ch === '"') inString = false
    } else if (ch === '"') {
      inString = true
    }
    out += ch
    i += 1
  }
  return out
}

/**
 * 对一整个请求做变量插值：url、header/param 的 value、body。
 * vars 为环境变量；请求自身的占位符会自动并入（同名时优先）。
 * JSON / Form Data body 使用 JSON 感知插值，长文本中的换行、引号会自动转义。
 * 返回结果不含 placeholders 字段。
 */
export function resolveRequest(
  req: HttpRequestData,
  vars: Record<string, string>,
): HttpRequestData {
  const all = requestVars(req, vars)
  const resolveKv = (items: KeyValue[]): KeyValue[] =>
    items.map((it) => ({ ...it, value: renderVars(it.value, all) }))
  const jsonLike = req.body_type === 'json' || req.body_type === 'form-data'
  return {
    method: req.method,
    url: renderVars(req.url, all),
    headers: resolveKv(req.headers || []),
    params: resolveKv(req.params || []),
    body_type: req.body_type,
    body: jsonLike ? renderVarsJson(req.body || '', all) : renderVars(req.body || '', all),
  }
}
