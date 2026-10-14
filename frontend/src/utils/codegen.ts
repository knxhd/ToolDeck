/** 请求代码生成：把当前 HTTP 请求转换为 curl / Java / Python 等调用代码。 */
import type { HttpRequestData } from '@/api/types'
import { parseUrlQuery } from '@/utils/parseCurl'

export type CodeLang = 'shell' | 'java' | 'python'

export interface CodeVariant {
  key: string
  label: string
}

export interface CodeLanguage {
  key: CodeLang
  label: string
  /** Monaco 语言 id，用于语法高亮。 */
  monaco: string
  variants: CodeVariant[]
}

export const CODE_LANGUAGES: CodeLanguage[] = [
  { key: 'shell', label: 'Shell', monaco: 'shell', variants: [{ key: 'curl', label: 'curl' }] },
  {
    key: 'java',
    label: 'Java',
    monaco: 'java',
    variants: [
      { key: 'httpclient', label: 'HttpClient' },
      { key: 'okhttp', label: 'OkHttp' },
    ],
  },
  {
    key: 'python',
    label: 'Python',
    monaco: 'python',
    variants: [
      { key: 'requests', label: 'requests' },
      { key: 'http.client', label: 'http.client' },
    ],
  },
]

type Pair = [string, string]

/** 归一化后的请求：与后端实际发送行为保持一致。 */
interface PreparedRequest {
  method: string
  url: string
  headers: Pair[]
  bodyKind: 'none' | 'text' | 'form'
  /** bodyKind = text 时的原始 body。 */
  body: string
  /** bodyKind = form 时的表单项（后端以 application/x-www-form-urlencoded 发送）。 */
  form: Pair[]
}

/** 按 {{var}} 占位符切分（捕获组保留占位符本身）。 */
const VAR_SPLIT_RE = /(\{\{\s*[A-Za-z0-9_.-]+\s*\}\})/

/** URL 编码，但保留未插值的 {{var}} 占位符原样，便于阅读。 */
function encodeKeepVars(s: string): string {
  return s
    .split(VAR_SPLIT_RE)
    .map((part, i) => (i % 2 === 1 ? part : encodeURIComponent(part)))
    .join('')
}

function urlEncodePairs(pairs: Pair[]): string {
  return pairs.map(([k, v]) => `${encodeKeepVars(k)}=${encodeKeepVars(v)}`).join('&')
}

function findHeader(headers: Pair[], name: string): string | undefined {
  const lower = name.toLowerCase()
  return headers.find(([k]) => k.toLowerCase() === lower)?.[1]
}

function prepare(req: HttpRequestData): PreparedRequest {
  const method = (req.method || 'GET').toUpperCase()

  // URL：与发送逻辑一致——剥离 URL 自带 query，用 Params 表重新拼接
  let url = (req.url || '').trim()
  const params: Pair[] = (req.params || [])
    .filter((p) => p.enabled && p.key)
    .map((p): Pair => [p.key, p.value ?? ''])
  if (params.length) {
    const { baseUrl } = parseUrlQuery(url)
    url = `${baseUrl}?${urlEncodePairs(params)}`
  }

  const headers: Pair[] = (req.headers || [])
    .filter((h) => h.enabled && h.key)
    .map((h): Pair => [h.key, h.value ?? ''])

  let bodyKind: PreparedRequest['bodyKind'] = 'none'
  let body = ''
  let form: Pair[] = []

  if (req.body_type === 'json' || req.body_type === 'raw') {
    if (req.body) {
      bodyKind = 'text'
      body = req.body
    }
    if (req.body_type === 'json' && !findHeader(headers, 'content-type')) {
      headers.push(['Content-Type', 'application/json'])
    }
  } else if (req.body_type === 'form-data') {
    try {
      const arr = JSON.parse(req.body || '[]')
      if (Array.isArray(arr)) {
        form = arr
          .filter((i) => i && i.key)
          .map((i): Pair => [String(i.key), String(i.value ?? '')])
      }
    } catch {
      form = []
    }
    if (form.length) {
      bodyKind = 'form'
      if (!findHeader(headers, 'content-type')) {
        headers.push(['Content-Type', 'application/x-www-form-urlencoded'])
      }
    }
  }

  return { method, url, headers, bodyKind, body, form }
}

/** 按行切分并保留每行末尾的换行符。 */
function splitKeepNewline(s: string): string[] {
  return s.split(/(?<=\n)/)
}

// ---------------------------------------------------------------- Shell / curl

function shQuote(s: string): string {
  return `'${s.replace(/'/g, `'\\''`)}'`
}

function genCurl(p: PreparedRequest): string {
  const lines: string[] = []
  lines.push(p.method === 'HEAD' ? 'curl --head' : `curl --request ${p.method}`)
  lines.push(`  --url ${shQuote(p.url)}`)
  for (const [k, v] of p.headers) lines.push(`  --header ${shQuote(`${k}: ${v}`)}`)
  if (p.bodyKind === 'text') {
    lines.push(`  -d ${shQuote(p.body)}`)
  } else if (p.bodyKind === 'form') {
    for (const [k, v] of p.form) lines.push(`  --data-urlencode ${shQuote(`${encodeKeepVars(k)}=${v}`)}`)
  }
  return lines.join(' \\\n')
}

// ---------------------------------------------------------------- Java

/** Java 字符串字面量（控制字符用八进制转义，避免 \\u 预处理问题）。 */
function javaStr(s: string): string {
  const body = s
    .replace(/\\/g, '\\\\')
    .replace(/"/g, '\\"')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '\\r')
    .replace(/\t/g, '\\t')
    .replace(/[\u0000-\u001f]/g, (c) => '\\' + c.charCodeAt(0).toString(8).padStart(3, '0'))
  return `"${body}"`
}

/** 多行文本拆为 "a\n" + "b" 形式，便于阅读。 */
function javaMultiline(s: string, indent: string): string {
  const lines = splitKeepNewline(s)
  if (lines.length <= 1) return javaStr(s)
  return lines.map(javaStr).join(` +\n${indent}`)
}

/** java.net.http.HttpClient 禁止手动设置的请求头。 */
const JDK_RESTRICTED_HEADERS = new Set(['connection', 'content-length', 'expect', 'host', 'upgrade'])

function genJavaHttpClient(p: PreparedRequest): string {
  const I2 = ' '.repeat(8)
  const I4 = ' '.repeat(16)
  const out: string[] = [
    'import java.net.URI;',
    'import java.net.http.HttpClient;',
    'import java.net.http.HttpRequest;',
    'import java.net.http.HttpResponse;',
    '',
    'public class Main {',
    '    public static void main(String[] args) throws Exception {',
    `${I2}HttpClient client = HttpClient.newHttpClient();`,
  ]

  let publisher = 'HttpRequest.BodyPublishers.noBody()'
  if (p.bodyKind === 'text') {
    out.push(`${I2}String body = ${javaMultiline(p.body, I4)};`)
    publisher = 'HttpRequest.BodyPublishers.ofString(body)'
  } else if (p.bodyKind === 'form') {
    out.push(`${I2}String body = ${javaStr(urlEncodePairs(p.form))};`)
    publisher = 'HttpRequest.BodyPublishers.ofString(body)'
  }

  const skipped = p.headers.filter(([k]) => JDK_RESTRICTED_HEADERS.has(k.toLowerCase())).map(([k]) => k)
  if (skipped.length) {
    out.push(`${I2}// 注意：HttpClient 不允许手动设置以下请求头，已忽略：${skipped.join(', ')}`)
  }

  out.push(`${I2}HttpRequest request = HttpRequest.newBuilder()`)
  out.push(`${I4}.uri(URI.create(${javaStr(p.url)}))`)
  for (const [k, v] of p.headers) {
    if (JDK_RESTRICTED_HEADERS.has(k.toLowerCase())) continue
    out.push(`${I4}.header(${javaStr(k)}, ${javaStr(v)})`)
  }
  out.push(`${I4}.method(${javaStr(p.method)}, ${publisher})`)
  out.push(`${I4}.build();`)
  out.push(`${I2}HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());`)
  out.push(`${I2}System.out.println(response.statusCode());`)
  out.push(`${I2}System.out.println(response.body());`)
  out.push('    }', '}')
  return out.join('\n')
}

/** OkHttp 中必须携带 body 的方法。 */
const OKHTTP_REQUIRES_BODY = new Set(['POST', 'PUT', 'PATCH'])
/** OkHttp 中不允许携带 body 的方法。 */
const OKHTTP_FORBIDS_BODY = new Set(['GET', 'HEAD'])

function genJavaOkHttp(p: PreparedRequest): string {
  const I2 = ' '.repeat(8)
  const I4 = ' '.repeat(16)
  const out: string[] = [
    'import okhttp3.*;',
    '',
    'public class Main {',
    '    public static void main(String[] args) throws Exception {',
    `${I2}OkHttpClient client = new OkHttpClient();`,
  ]

  let bodyArg = 'null'
  const hasBody = p.bodyKind !== 'none'
  if (hasBody && OKHTTP_FORBIDS_BODY.has(p.method)) {
    out.push(`${I2}// 注意：OkHttp 不允许 ${p.method} 请求携带 body，已忽略请求体`)
  } else if (p.bodyKind === 'text') {
    const ct = findHeader(p.headers, 'content-type')
    out.push(`${I2}MediaType mediaType = ${ct ? `MediaType.parse(${javaStr(ct)})` : 'null'};`)
    out.push(`${I2}RequestBody body = RequestBody.create(mediaType, ${javaMultiline(p.body, I4)});`)
    bodyArg = 'body'
  } else if (p.bodyKind === 'form') {
    out.push(`${I2}RequestBody body = new FormBody.Builder()`)
    for (const [k, v] of p.form) out.push(`${I4}.add(${javaStr(k)}, ${javaStr(v)})`)
    out.push(`${I4}.build();`)
    bodyArg = 'body'
  } else if (OKHTTP_REQUIRES_BODY.has(p.method)) {
    out.push(`${I2}RequestBody body = RequestBody.create(null, new byte[0]);`)
    bodyArg = 'body'
  }

  out.push(`${I2}Request request = new Request.Builder()`)
  out.push(`${I4}.url(${javaStr(p.url)})`)
  out.push(`${I4}.method(${javaStr(p.method)}, ${bodyArg})`)
  for (const [k, v] of p.headers) out.push(`${I4}.addHeader(${javaStr(k)}, ${javaStr(v)})`)
  out.push(`${I4}.build();`)
  out.push(`${I2}try (Response response = client.newCall(request).execute()) {`)
  out.push(`${I2}    System.out.println(response.code());`)
  out.push(`${I2}    System.out.println(response.body().string());`)
  out.push(`${I2}}`)
  out.push('    }', '}')
  return out.join('\n')
}

// ---------------------------------------------------------------- Python

function pyStr(s: string): string {
  const body = s
    .replace(/\\/g, '\\\\')
    .replace(/"/g, '\\"')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '\\r')
    .replace(/\t/g, '\\t')
    .replace(/[\u0000-\u001f\u007f]/g, (c) => '\\x' + c.charCodeAt(0).toString(16).padStart(2, '0'))
  return `"${body}"`
}

/** 多行文本拆为括号内相邻字符串字面量拼接。 */
function pyMultiline(s: string): string {
  const lines = splitKeepNewline(s)
  if (lines.length <= 1) return pyStr(s)
  return `(\n${lines.map((l) => `    ${pyStr(l)}`).join('\n')}\n)`
}

function pyDict(pairs: Pair[]): string {
  if (!pairs.length) return '{}'
  return `{\n${pairs.map(([k, v]) => `    ${pyStr(k)}: ${pyStr(v)}`).join(',\n')}\n}`
}

/** 存在重复 key 时用元组列表，避免 dict 覆盖。 */
function pyFormData(pairs: Pair[]): string {
  const keys = new Set(pairs.map(([k]) => k))
  if (keys.size === pairs.length) return pyDict(pairs)
  return `[\n${pairs.map(([k, v]) => `    (${pyStr(k)}, ${pyStr(v)})`).join(',\n')}\n]`
}

function genPythonRequests(p: PreparedRequest): string {
  const out: string[] = ['import requests', '', `url = ${pyStr(p.url)}`, '']
  const args: string[] = [pyStr(p.method), 'url']

  if (p.bodyKind === 'text') {
    out.push(`payload = ${pyMultiline(p.body)}`)
  } else if (p.bodyKind === 'form') {
    out.push(`payload = ${pyFormData(p.form)}`)
  }
  if (p.headers.length) {
    out.push(`headers = ${pyDict(p.headers)}`)
    args.push('headers=headers')
  }
  if (p.bodyKind === 'text') args.push('data=payload.encode("utf-8")')
  else if (p.bodyKind === 'form') args.push('data=payload')
  if (p.bodyKind !== 'none' || p.headers.length) out.push('')

  out.push(`response = requests.request(${args.join(', ')})`)
  out.push('', 'print(response.status_code)', 'print(response.text)')
  return out.join('\n')
}

/** 拆出 scheme / host[:port] / path?query，兼容未插值的 {{var}}。 */
function splitUrl(url: string): { https: boolean; host: string; path: string } {
  const m = /^(https?):\/\/([^/?#]*)([^#]*)/i.exec(url)
  if (m) return { https: m[1].toLowerCase() === 'https', host: m[2], path: m[3] || '/' }
  const n = /^([^/?#]*)([^#]*)/.exec(url)
  return { https: false, host: n?.[1] || '', path: n?.[2] || '/' }
}

function genPythonHttpClient(p: PreparedRequest): string {
  const { https, host, path } = splitUrl(p.url)
  const out: string[] = [
    'import http.client',
    '',
    `conn = http.client.${https ? 'HTTPSConnection' : 'HTTPConnection'}(${pyStr(host)})`,
  ]
  const args: string[] = [pyStr(p.method), pyStr(path.startsWith('/') ? path : `/${path}`)]

  if (p.bodyKind === 'text') {
    out.push(`payload = ${pyMultiline(p.body)}`)
    args.push('body=payload.encode("utf-8")')
  } else if (p.bodyKind === 'form') {
    out.push(`payload = ${pyStr(urlEncodePairs(p.form))}`)
    args.push('body=payload')
  }
  if (p.headers.length) {
    out.push(`headers = ${pyDict(p.headers)}`)
    args.push('headers=headers')
  }

  out.push(`conn.request(${args.join(', ')})`)
  out.push('res = conn.getresponse()')
  out.push('print(res.status, res.reason)')
  out.push('print(res.read().decode("utf-8"))')
  out.push('conn.close()')
  return out.join('\n')
}

// ---------------------------------------------------------------- 入口

const GENERATORS: Record<string, (p: PreparedRequest) => string> = {
  'shell:curl': genCurl,
  'java:httpclient': genJavaHttpClient,
  'java:okhttp': genJavaOkHttp,
  'python:requests': genPythonRequests,
  'python:http.client': genPythonHttpClient,
}

/** 生成指定语言 / 实现方式的调用代码。 */
export function generateCode(req: HttpRequestData, lang: CodeLang, variant: string): string {
  const gen = GENERATORS[`${lang}:${variant}`]
  if (!gen) return `// 暂不支持：${lang} / ${variant}`
  return gen(prepare(req))
}
