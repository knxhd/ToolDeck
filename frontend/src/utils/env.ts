/** 环境变量插值：把文本中的 {{key}} 占位符替换为当前环境里的值。 */
import type { HttpRequestData, KeyValue } from '@/api/types'

/**
 * 占位符名称：普通变量允许字母数字、下划线、点、短横线；
 * 内置占位符以 $ 开头，可带括号参数，如 {{$randomString(32)}}。
 */
export const VAR_TOKEN = String.raw`\$?[A-Za-z0-9_.-]+(?:\([^(){}]*\))?`

/** 匹配 {{ key }} / {{key}} / {{$builtin(args)}}。 */
export const PLACEHOLDER_SOURCE = String.raw`\{\{\s*(${VAR_TOKEN})\s*\}\}`
const PLACEHOLDER_RE = new RegExp(PLACEHOLDER_SOURCE, 'g')

/** 最多递归替换轮数，避免变量值里又引用其它变量时死循环。 */
const MAX_ROUNDS = 5

const hasOwn = (obj: object, key: string) => Object.prototype.hasOwnProperty.call(obj, key)

// ---------------------------------------------------------------------------
// 内置占位符（动态值，每次发送、每处引用都会重新生成）
// ---------------------------------------------------------------------------

export interface BuiltinVar {
  /** 名称（含 $ 前缀） */
  name: string
  /** 说明 */
  desc: string
  /** 参数用法说明（可选） */
  usage?: string
  /** 根据括号内的原始参数生成值 */
  gen: (arg?: string) => string
}

const pad = (n: number, len = 2) => String(n).padStart(len, '0')

/** 日期格式化：支持 yyyy MM dd HH mm ss SSS。 */
export function formatDate(d: Date, fmt = 'yyyy-MM-dd HH:mm:ss'): string {
  const map: Record<string, string> = {
    yyyy: String(d.getFullYear()),
    MM: pad(d.getMonth() + 1),
    dd: pad(d.getDate()),
    HH: pad(d.getHours()),
    mm: pad(d.getMinutes()),
    ss: pad(d.getSeconds()),
    SSS: pad(d.getMilliseconds(), 3),
  }
  return fmt.replace(/yyyy|SSS|MM|dd|HH|mm|ss/g, (t) => map[t])
}

function randomBytes(n: number): Uint8Array {
  const buf = new Uint8Array(n)
  crypto.getRandomValues(buf)
  return buf
}

const ALNUM = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

function randomString(len: number): string {
  let out = ''
  // 拒绝采样，保证字符分布均匀
  const limit = 256 - (256 % ALNUM.length)
  while (out.length < len) {
    for (const b of randomBytes(len * 2)) {
      if (b < limit) out += ALNUM[b % ALNUM.length]
      if (out.length >= len) break
    }
  }
  return out
}

/** UUID v4；非安全上下文（http + IP 访问）没有 crypto.randomUUID，用 getRandomValues 兜底。 */
function uuid(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const b = randomBytes(16)
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const h = [...b].map((x) => x.toString(16).padStart(2, '0')).join('')
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`
}

const toInt = (s: string | undefined, def: number) => {
  const n = parseInt((s ?? '').trim(), 10)
  return Number.isFinite(n) ? n : def
}

export const BUILTIN_VARS: BuiltinVar[] = [
  {
    name: '$datetime',
    desc: '当前时间，格式 yyyy-MM-dd HH:mm:ss',
    usage: '可自定义格式：{{$datetime(yyyy/MM/dd HH:mm)}}，支持 yyyy MM dd HH mm ss SSS',
    gen: (arg) => formatDate(new Date(), arg?.trim() || 'yyyy-MM-dd HH:mm:ss'),
  },
  { name: '$date', desc: '当前日期，格式 yyyy-MM-dd', gen: () => formatDate(new Date(), 'yyyy-MM-dd') },
  { name: '$time', desc: '当前时间，格式 HH:mm:ss', gen: () => formatDate(new Date(), 'HH:mm:ss') },
  { name: '$timestamp', desc: '当前 Unix 时间戳（秒）', gen: () => String(Math.floor(Date.now() / 1000)) },
  { name: '$timestampMs', desc: '当前 Unix 时间戳（毫秒）', gen: () => String(Date.now()) },
  {
    name: '$randomString',
    desc: '随机字符串（大小写字母 + 数字），默认 16 位',
    usage: '可指定长度：{{$randomString(32)}}',
    gen: (arg) => randomString(Math.min(Math.max(toInt(arg, 16), 1), 4096)),
  },
  {
    name: '$randomInt',
    desc: '随机整数，默认 0 ~ 1000',
    usage: '可指定范围：{{$randomInt(1, 100)}}（含两端）；只给一个参数时为上限，如 {{$randomInt(10)}}',
    gen: (arg) => {
      const parts = (arg ?? '').split(',').map((s) => s.trim()).filter(Boolean)
      let min = 0
      let max = 1000
      if (parts.length === 1) {
        max = toInt(parts[0], 1000)
      } else if (parts.length >= 2) {
        min = toInt(parts[0], 0)
        max = toInt(parts[1], 1000)
      }
      if (min > max) [min, max] = [max, min]
      return String(min + Math.floor(Math.random() * (max - min + 1)))
    },
  },
  { name: '$uuid', desc: '随机 UUID（v4）', gen: () => uuid() },
]

const BUILTIN_MAP: Record<string, BuiltinVar> = Object.fromEntries(BUILTIN_VARS.map((b) => [b.name, b]))

/** 解析内置占位符 token（如 `$randomString(8)`）；不是合法内置占位符时返回 null。 */
export function parseBuiltin(token: string): { def: BuiltinVar; arg?: string } | null {
  const m = /^(\$[A-Za-z0-9_]+)(?:\(([^(){}]*)\))?$/.exec(token)
  if (!m) return null
  const def = BUILTIN_MAP[m[1]]
  return def ? { def, arg: m[2] } : null
}

/** 变量是否可解析（用户变量或合法内置占位符）。 */
export function isKnownVar(token: string, vars: Record<string, string>): boolean {
  return hasOwn(vars, token) || !!parseBuiltin(token)
}

/** 取变量原始值：用户变量优先，其次内置占位符（每次调用重新生成）；未定义返回 undefined。 */
export function lookupVar(token: string, vars: Record<string, string>): string | undefined {
  if (hasOwn(vars, token)) return vars[token]
  const b = parseBuiltin(token)
  return b ? b.def.gen(b.arg) : undefined
}

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
      const value = lookupVar(name, vars)
      if (value !== undefined) {
        changed = true
        return value
      }
      return raw
    })
    out = next
    if (!changed) break
  }
  return out
}

/** 收集 text 中出现的、但 vars 里缺失的变量名（内置占位符视为已定义），用于发送前提醒。 */
export function missingVars(text: string, vars: Record<string, string>): string[] {
  const missing = new Set<string>()
  for (const m of text.matchAll(new RegExp(PLACEHOLDER_SOURCE, 'g'))) {
    const name = m[1]
    if (!isKnownVar(name, vars)) missing.add(name)
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

/** 取变量的最终值：用户变量递归展开其中引用的其它变量；内置占位符直接生成。 */
function finalValue(name: string, vars: Record<string, string>): string {
  if (hasOwn(vars, name)) return renderVars(vars[name], vars)
  return lookupVar(name, vars) ?? ''
}

/**
 * JSON 感知的插值：占位符位于 JSON 字符串字面量内时，对变量值做 JSON 转义
 * （换行、制表符、引号、反斜杠等），保证替换后仍是合法 JSON；位于字符串外时原样插入。
 * 未定义的占位符原样保留。
 */
export function renderVarsJson(text: string, vars: Record<string, string>): string {
  if (!text) return text
  const re = new RegExp(PLACEHOLDER_SOURCE, 'y')
  let out = ''
  let inString = false
  let i = 0
  while (i < text.length) {
    const ch = text[i]
    if (ch === '{' && text[i + 1] === '{') {
      re.lastIndex = i
      const m = re.exec(text)
      if (m && isKnownVar(m[1], vars)) {
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
