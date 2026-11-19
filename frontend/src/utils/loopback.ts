/**
 * 回环地址解析：工具部署在服务器时，URL 里的 127.0.0.1 只有服务端自己能访问，
 * 浏览器所在机器上的服务连不上。这里在「发送前」把回环 host 换成一个可达地址。
 *
 * 解析策略（设置里可改，见 设置 → 网络）：
 * - auto   浏览器访问本工具用的地址（window.location.hostname），适合「工具与被测服务同机/同域名」
 * - origin 后端看到的调用方 IP（/api/net/host 的 client_ip），适合「被测服务在调用方本机、同内网」
 * - custom 手填地址（如 10.18.217.60:48088 或内网别名）
 * - off    不改写
 */
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/settings'

export type LoopbackMode = 'auto' | 'origin' | 'custom' | 'off'

export const LOOPBACK_HOSTS = ['127.0.0.1', 'localhost', '::1', '0.0.0.0', '127.0.1.1', 'host.docker.internal']

const SCHEMES = ['http://', 'https://', 'ws://', 'wss://']

/** 后端看到的调用方信息，进入页面后拉一次缓存起来。 */
interface NetHostInfo {
  client_ip: string
  browser_host: string
}

const netHost: NetHostInfo = { client_ip: '', browser_host: '' }
let probe: Promise<NetHostInfo> | null = null

/** 拉取调用方地址信息（幂等，只发一次请求，失败不重试）。 */
export async function loadNetHost(force = false): Promise<NetHostInfo> {
  if (!force && probe) return probe
  if (!probe) {
    probe = api
      .get<NetHostInfo>('/api/net/host')
      .then((info) => {
        netHost.client_ip = (info?.client_ip || '').trim()
        netHost.browser_host = (info?.browser_host || '').trim()
        return netHost
      })
      .catch(() => netHost)
  }
  await probe
  return netHost
}

/** 是否回环 host（去方括号、忽略大小写）。 */
export function isLoopbackHost(host: string): boolean {
  const h = (host || '').trim().toLowerCase().replace(/^\[|\]$/g, '')
  return LOOPBACK_HOSTS.includes(h)
}

/** URL 里是否含回环 host（用于在界面上提示"将被解析"）。 */
export function hasLoopback(url: string): boolean {
  if (!url) return false
  const lower = url.toLowerCase()
  if (!SCHEMES.some((s) => lower.startsWith(s))) return false
  try {
    return isLoopbackHost(new URL(url).hostname)
  } catch {
    return false
  }
}

function stripScheme(target: string): string {
  const t = (target || '').trim()
  const lower = t.toLowerCase()
  for (const s of SCHEMES) {
    if (lower.startsWith(s)) return t.slice(s.length).replace(/\/+$/, '')
  }
  return t.replace(/\/+$/, '')
}

function browserHost(): string {
  if (typeof window === 'undefined') return ''
  const h = window.location.hostname || ''
  return isLoopbackHost(h) ? '' : h
}

/** 当前设置下、回环 host 应该被替换成什么；空串表示不改写。 */
export function getLoopbackTarget(): string {
  const store = useSettingsStore()
  const mode = (store.settings.loopbackMode || 'auto') as LoopbackMode
  if (mode === 'off') return ''
  if (mode === 'custom') {
    const host = stripScheme(store.settings.loopbackHost || '')
    return !host || isLoopbackHost(host) ? '' : host
  }
  if (mode === 'origin') {
    const ip = netHost.client_ip
    if (ip && !isLoopbackHost(ip)) return ip
    // 还没拉到 / 拿不到，退回到浏览器访问地址
    return browserHost()
  }
  return browserHost()
}

/**
 * 把 url 里的回环 host 换成 target（target 带端口时端口一起换）。
 * 返回改写结果与是否发生改写；target 为空或 url 不含回环 host 时原样返回。
 */
export function rewriteLoopbackUrl(
  url: string,
  target = getLoopbackTarget(),
): { url: string; changed: boolean; target: string } {
  const tgt = stripScheme(target)
  if (!url || !tgt) return { url, changed: false, target: '' }
  const lower = url.toLowerCase()
  if (!SCHEMES.some((s) => lower.startsWith(s))) return { url, changed: false, target: '' }
  let parsed: URL
  try {
    parsed = new URL(url)
  } catch {
    return { url, changed: false, target: '' }
  }
  if (!isLoopbackHost(parsed.hostname)) return { url, changed: false, target: '' }

  // 拆出目标里的 host / port（支持 [::1]:8080 与 10.0.0.1:9000）
  let host = tgt
  let port = ''
  if (tgt.startsWith('[') && tgt.includes(']:')) {
    const idx = tgt.indexOf(']:')
    host = tgt.slice(0, idx + 1)
    port = tgt.slice(idx + 2).replace(/^:/, '')
  } else if (tgt.indexOf(':') > 0 && tgt.lastIndexOf(':') === tgt.indexOf(':')) {
    const idx = tgt.lastIndexOf(':')
    host = tgt.slice(0, idx)
    port = tgt.slice(idx + 1)
  } else if (tgt.indexOf(':') > 0) {
    // 裸 IPv6
    host = `[${tgt}]`
  }
  if (!port) port = parsed.port

  parsed.hostname = host.replace(/^\[|\]$/g, '')
  parsed.port = port || ''
  return { url: parsed.toString(), changed: true, target: tgt }
}

/** 只提示一次：同一目标地址不重复弹提示。 */
const notified = new Set<string>()
export function shouldNotifyRewrite(target: string): boolean {
  if (!target || notified.has(target)) return false
  notified.add(target)
  return true
}
