/** curl 命令解析：从 curl 指令文本中提取 method / url / headers / params / body。 */

export interface ParsedCurl {
  method: string
  url: string
  headers: Array<{ key: string; value: string; enabled: boolean }>
  params: Array<{ key: string; value: string; enabled: boolean }>
  body: string
  bodyType: 'none' | 'json' | 'raw' | 'form-data'
}

/** 按 shell 风格切分 token：支持单/双引号、反斜杠转义、行尾 \ 续行。 */
function tokenize(text: string): string[] {
  const tokens: string[] = []
  let i = 0
  let cur = ''
  let quote: '"' | "'" | null = null
  let esc = false
  while (i < text.length) {
    const ch = text[i]
    if (esc) {
      // 反斜杠 + 换行 = 续行，直接丢弃
      if (ch === '\n' || ch === '\r') {
        // skip
      } else {
        cur += ch
      }
      esc = false
      i++
      continue
    }
    if (ch === '\\') {
      esc = true
      i++
      continue
    }
    if (quote) {
      if (ch === quote) quote = null
      else cur += ch
      i++
      continue
    }
    if (ch === '"' || ch === "'") {
      quote = ch
      i++
      continue
    }
    if (ch === ' ' || ch === '\t' || ch === '\n' || ch === '\r') {
      if (cur) {
        tokens.push(cur)
        cur = ''
      }
      i++
      continue
    }
    cur += ch
    i++
  }
  if (cur) tokens.push(cur)
  return tokens
}

/** 把 "name=value" 拆成 query 参数；无 = 时 value 为空。 */
function kvFromPair(pair: string): { key: string; value: string; enabled: boolean } {
  const eq = pair.indexOf('=')
  if (eq < 0) return { key: safeDecode(pair), value: '', enabled: true }
  return { key: safeDecode(pair.slice(0, eq)), value: safeDecode(pair.slice(eq + 1)), enabled: true }
}

function safeDecode(s: string): string {
  try {
    return decodeURIComponent(s)
  } catch {
    return s
  }
}

/** 从 URL 拆出 query string 到 params，返回去掉 query 的 URL。 */
function splitQuery(url: string): { url: string; params: Array<{ key: string; value: string; enabled: boolean }> } {
  const qi = url.indexOf('?')
  if (qi < 0) return { url, params: [] }
  const query = url.slice(qi + 1)
  const base = url.slice(0, qi)
  const params: Array<{ key: string; value: string; enabled: boolean }> = []
  if (query) {
    for (const pair of query.split('&')) {
      if (!pair) continue
      params.push(kvFromPair(pair))
    }
  }
  return { url: base, params }
}

/**
 * URL → Params 自动解析：把 URL 中的 query string 拆成参数表。
 * 返回 { baseUrl: 去掉 query 的 URL, params: 解析出的参数列表 }。
 */
export function parseUrlQuery(
  url: string,
): { baseUrl: string; params: Array<{ key: string; value: string; enabled: boolean }> } {
  const { url: baseUrl, params } = splitQuery(url)
  return { baseUrl, params: params.filter((p) => p.key || p.value) }
}

/** 把 Params 表拼成 query string（仅 enabled 且有 key 的行；key/value 做 URL 编码）。 */
export function buildQueryString(params: Array<{ key: string; value: string; enabled: boolean }>): string {
  return (params || [])
    .filter((p) => p.enabled && p.key)
    .map((p) => `${encodeURIComponent(p.key)}=${encodeURIComponent(p.value ?? '')}`)
    .join('&')
}

export function parseCurl(text: string): ParsedCurl {
  const tokens = tokenize(text)

  let explicitMethod = ''
  let url = ''
  const headers: Array<{ key: string; value: string; enabled: boolean }> = []
  const dataParts: string[] = []
  const formParts: string[] = []
  let getMode = false
  let cookie = ''
  const bareTokens: string[] = []

  const nextValue = (i: number) => tokens[i + 1] || ''

  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i]

    if (t === '-X' || t === '--request') {
      explicitMethod = nextValue(i).toUpperCase()
      i++
      continue
    }
    if (t === '-H' || t === '--header') {
      const h = nextValue(i)
      i++
      const idx = h.indexOf(':')
      if (idx > 0) {
        headers.push({ key: h.slice(0, idx).trim(), value: h.slice(idx + 1).trim(), enabled: true })
      }
      continue
    }
    if (t === '-d' || t === '--data' || t === '--data-raw' || t === '--data-ascii' || t === '--data-binary') {
      dataParts.push(nextValue(i))
      i++
      continue
    }
    if (t === '--data-urlencode') {
      dataParts.push(nextValue(i))
      i++
      continue
    }
    if (t === '-F' || t === '--form') {
      formParts.push(nextValue(i))
      i++
      continue
    }
    if (t === '-G' || t === '--get') {
      getMode = true
      continue
    }
    if (t === '-b' || t === '--cookie') {
      cookie = nextValue(i)
      i++
      continue
    }
    if (t === '--compressed' || t === '--location' || t === '-L' || t === '--include' ||
      t === '--silent' || t === '-s' || t === '--insecure' || t === '-k' || t === '--verbose' || t === '-v') {
      continue
    }
    // 堆叠短 flag（-sS / -ik 等）
    if (/^-[a-zA-Z]{2,}$/.test(t)) {
      continue
    }
    // 带值但未显式处理的选项：跳过自身（值可能误判为 URL，但概率低，保守忽略）
    if (t.startsWith('-') && t !== '-') {
      continue
    }
    // 裸 token：第一个作为 URL
    bareTokens.push(t)
  }

  url = bareTokens.find((t) => /^https?:\/\//i.test(t)) || bareTokens[0] || ''

  // ---- 请求方式 ----
  let method = explicitMethod
  if (!method) {
    if (formParts.length || dataParts.length) method = 'POST'
    else method = 'GET'
  }

  // ---- query 参数（-G 时 data 作为 query；否则 URL 自带 query 拆出）----
  let params: Array<{ key: string; value: string; enabled: boolean }> = []
  let finalUrl = url
  if (getMode && dataParts.length) {
    for (const part of dataParts) {
      for (const pair of part.split('&')) {
        if (pair) params.push(kvFromPair(pair))
      }
    }
    dataParts.length = 0
  }
  const split = splitQuery(finalUrl)
  finalUrl = split.url
  params = params.concat(split.params)

  // ---- body ----
  let body = ''
  let bodyType: ParsedCurl['bodyType'] = 'none'
  if (formParts.length) {
    body = JSON.stringify(formParts.map((p) => kvFromPair(p)))
    bodyType = 'form-data'
  } else if (dataParts.length) {
    body = dataParts.join('&')
    const trimmed = body.trim()
    if (trimmed && (trimmed.startsWith('{') || trimmed.startsWith('['))) {
      try {
        JSON.parse(trimmed)
        bodyType = 'json'
      } catch {
        bodyType = 'raw'
      }
    } else {
      bodyType = 'raw'
    }
  }

  // ---- Cookie 并入请求头 ----
  if (cookie && !headers.some((h) => h.key.toLowerCase() === 'cookie')) {
    headers.push({ key: 'Cookie', value: cookie, enabled: true })
  }

  return {
    method,
    url: finalUrl,
    headers: headers.filter((h) => h.key),
    params: params.filter((p) => p.key || p.value),
    body,
    bodyType,
  }
}
