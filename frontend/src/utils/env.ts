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

/** 对一整个请求做变量插值：url、header/param 的 value、body。 */
export function resolveRequest(
  req: HttpRequestData,
  vars: Record<string, string>,
): HttpRequestData {
  const resolveKv = (items: KeyValue[]): KeyValue[] =>
    items.map((it) => ({ ...it, value: renderVars(it.value, vars) }))
  return {
    ...req,
    url: renderVars(req.url, vars),
    headers: resolveKv(req.headers || []),
    params: resolveKv(req.params || []),
    body: renderVars(req.body || '', vars),
  }
}
