/** 集合导入 / 导出工具：兼容 Postman Collection v2.1 和本工具自定义格式。 */
import type { CollectionNode, HttpRequestData, KeyValue } from '@/api/types'

export interface ExportFile {
  version: 1
  exportedAt: string
  collections: CollectionNode[]
}

/** 触发浏览器下载 JSON 文件。 */
export function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ---------- Postman v2.1 导出 ----------

function nodeToPostmanItem(node: CollectionNode): any {
  if (node.type === 'request' && node.request) {
    const req = node.request
    const headers = (req.headers || [])
      .filter((h) => h.key)
      .map((h) => ({ key: h.key, value: h.value, disabled: !h.enabled }))
    const params = (req.params || [])
      .filter((p) => p.key)
      .map((p) => ({ key: p.key, value: p.value, disabled: !p.enabled }))
    const urlRaw = req.url || ''
    const urlObj: any = { raw: urlRaw }
    if (urlRaw.includes('://')) {
      const [proto, rest] = urlRaw.split('://', 2)
      urlObj.protocol = proto
      const hostPath = rest.split('/', 2)
      urlObj.host = hostPath[0].split('.')
      if (hostPath[1]) {
        urlObj.path = hostPath[1].split('?')[0].split('/').filter(Boolean)
      }
    }
    if (params.length) urlObj.query = params
    let body: any = { mode: 'raw', raw: req.body || '' }
    if (req.body_type === 'json') body.options = { raw: { language: 'json' } }
    else if (req.body_type === 'form-data') {
      body = { mode: 'formdata', formdata: [] }
      try {
        const items = JSON.parse(req.body || '[]') as Array<Record<string, any>>
        body.formdata = items.map((i) => ({
          key: i.key || '',
          value: String(i.value ?? ''),
          type: i.type || 'text',
        }))
      } catch { /* ignore */ }
    }
    return {
      name: node.name,
      request: {
        method: (req.method || 'GET').toUpperCase(),
        header: headers,
        url: urlObj,
        body,
        ...(req.docs ? { description: req.docs } : {}),
      },
      response: [],
    }
  }
  // folder / collection
  return {
    name: node.name,
    item: (node.children || []).map(nodeToPostmanItem),
  }
}

function stamp(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
}

function exportPostman(tree: CollectionNode[], name: string) {
  const payload = {
    info: {
      _postman_id: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
      name,
      schema: 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
    },
    item: tree.map(nodeToPostmanItem),
  }
  downloadJson(payload, `ToolDeck-api-${stamp()}.json`)
}

// ---------- 对外导出 ----------

export function exportCollections(nodes: CollectionNode[]) {
  exportPostman(nodes, 'api-tool')
}

export function exportOneCollection(node: CollectionNode) {
  const safeName = (node.name || 'collection').replace(/[\\/:*?"<>|]/g, '_')
  exportPostman([JSON.parse(JSON.stringify(node))], safeName)
}

// ---------- 导入：自动识别格式 ----------

function urlToStr(url: any): string {
  if (typeof url === 'string') return url
  if (!url) return ''
  if (url.raw) return url.raw
  const proto = url.protocol || 'https'
  const host = (url.host || []).join('.')
  const path = (url.path || []).join('/')
  const query = (url.query || []).filter((q: any) => !q.disabled && q.key)
  const qs = query.map((q: any) => `${q.key}=${q.value ?? ''}`).join('&')
  return `${proto}://${host}${path ? '/' + path : ''}${qs ? '?' + qs : ''}`
}

function bodyTypeFromMode(mode: string, options: any): string {
  if (mode === 'raw') {
    const lang = options?.raw?.language || 'text'
    if (lang === 'json') return 'json'
    if (lang === 'xml') return 'xml'
    if (lang === 'html') return 'html'
    return 'text'
  }
  if (mode === 'formdata') return 'form-data'
  if (mode === 'urlencoded') return 'text'
  return 'none'
}

let impSeq = 0
const impId = () => `n_imp_${Date.now().toString(36)}_${(impSeq++).toString(36)}`

function postmanItemToNode(item: any): CollectionNode | null {
  if (item.request && typeof item.request === 'object') {
    const rp = item.request
    const headers: KeyValue[] = (rp.header || [])
      .filter((h: any) => h.key)
      .map((h: any) => ({ key: h.key, value: h.value || '', enabled: !h.disabled }))
    const body = rp.body || {}
    const mode = body.mode || 'raw'
    let bodyRaw = ''
    let bodyType = 'none'
    if (mode === 'raw') {
      bodyRaw = body.raw || ''
      bodyType = bodyTypeFromMode(mode, body.options || {})
    } else if (mode === 'formdata') {
      const fd = body.formdata || []
      bodyRaw = JSON.stringify(
        fd.map((f: any) => ({ key: f.key || '', value: f.value || '', type: f.type || 'text', enabled: true })),
      )
      bodyType = 'form-data'
    } else if (mode === 'urlencoded') {
      bodyRaw = (body.urlencoded || []).map((f: any) => `${f.key}=${f.value ?? ''}`).join('&')
      bodyType = 'text'
    }
    const req: HttpRequestData = {
      method: (rp.method || 'GET').toUpperCase() as HttpRequestData['method'],
      url: urlToStr(rp.url),
      headers: headers.length ? headers : [{ key: '', value: '', enabled: true }],
      params: [{ key: '', value: '', enabled: true }],
      body_type: bodyType as HttpRequestData['body_type'],
      body: bodyRaw,
      ...(rp.description ? { docs: typeof rp.description === 'string' ? rp.description : rp.description?.content || '' } : {}),
    }
    return {
      id: impId(),
      type: 'request',
      name: item.name || 'Untitled',
      kind: 'http',
      request: req,
    }
  }
  const children = (item.item || []).map(postmanItemToNode).filter(Boolean) as CollectionNode[]
  return {
    id: impId(),
    type: 'folder',
    name: item.name || 'Folder',
    children,
  }
}

/** 解析导入的文件，自动识别 Postman v2.1 或本工具自定义格式。 */
export function parseImportFile(text: string): CollectionNode[] {
  const data = JSON.parse(text) as any
  // Postman v2.1: 有 info.schema 且含 "collection/v2.1"
  if (data?.info?.schema && typeof data.info.schema === 'string' && data.info.schema.includes('collection/v2')) {
    const items = data.item || []
    return items.map(postmanItemToNode).filter(Boolean) as CollectionNode[]
  }
  // 自定义格式
  if (Array.isArray(data)) return data as CollectionNode[]
  if (data && Array.isArray(data.collections)) return data.collections
  throw new Error('无法识别的文件格式：需要 Postman Collection v2.1 或 api-tool 导出文件')
}

export type ConflictPolicy = 'overwrite' | 'duplicate'

function newId() {
  return `n_imp_${Date.now().toString(36)}_${(impSeq++).toString(36)}`
}

/**
 * 把 incoming 合并到 existingTree。
 */
export function mergeIntoTree(
  existingTree: CollectionNode[],
  incoming: CollectionNode[],
  policy: ConflictPolicy,
): { added: number; overwritten: number } {
  let added = 0
  let overwritten = 0

  function cloneFresh(node: CollectionNode): CollectionNode {
    const copy: CollectionNode = JSON.parse(JSON.stringify(node))
    copy.id = newId()
    return copy
  }

  function mergeChildren(parent: CollectionNode[], incomingNodes: CollectionNode[]) {
    for (const inc of incomingNodes) {
      const existing = parent.find((n) => n.name === inc.name && n.type === inc.type)
      if (existing) {
        if (policy === 'overwrite') {
          existing.children = inc.children ? [] : undefined
          const keepId = existing.id
          Object.assign(existing, JSON.parse(JSON.stringify(inc)), { id: keepId })
          overwritten++
          if (inc.children && existing.children) {
            mergeChildren(existing.children, inc.children)
          }
        } else {
          const fresh = cloneFresh(inc)
          fresh.name = dedupName(parent, inc.name)
          parent.push(fresh)
          added++
        }
      } else {
        const fresh = cloneFresh(inc)
        parent.push(fresh)
        added++
      }
    }
  }

  mergeChildren(existingTree, incoming)
  return { added, overwritten }
}

function dedupName(siblings: CollectionNode[], name: string): string {
  let candidate = `${name}_new`
  let i = 2
  while (siblings.some((s) => s.name === candidate)) {
    candidate = `${name}_new${i++}`
  }
  return candidate
}
