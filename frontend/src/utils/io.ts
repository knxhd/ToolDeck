/** 集合导入 / 导出工具。 */
import type { CollectionNode } from '@/api/types'

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

export function exportCollections(nodes: CollectionNode[]) {
  const payload: ExportFile = {
    version: 1,
    exportedAt: new Date().toISOString(),
    collections: JSON.parse(JSON.stringify(nodes)),
  }
  const stamp = new Date().toISOString().slice(0, 10)
  downloadJson(payload, `api-tool-collections-${stamp}.json`)
}

export function exportOneCollection(node: CollectionNode) {
  const payload: ExportFile = {
    version: 1,
    exportedAt: new Date().toISOString(),
    collections: [JSON.parse(JSON.stringify(node))],
  }
  const safeName = (node.name || 'collection').replace(/[\\/:*?"<>|]/g, '_')
  downloadJson(payload, `api-tool-${safeName}-${new Date().toISOString().slice(0, 10)}.json`)
}

/** 解析导入的文件，返回 collection 节点数组。 */
export function parseImportFile(text: string): CollectionNode[] {
  const data = JSON.parse(text) as Partial<ExportFile> | CollectionNode[]
  if (Array.isArray(data)) return data as CollectionNode[]
  if (data && Array.isArray(data.collections)) return data.collections
  throw new Error('文件格式不正确：需要导出的 JSON 文件')
}

export type ConflictPolicy = 'overwrite' | 'duplicate'

let seq = 0
const newId = () => `n_imp_${Date.now().toString(36)}_${(seq++).toString(36)}`

/**
 * 把 incoming 合并到 existingTree。
 * - 同名同类型节点：overwrite 则覆盖其内容（保留原 id），duplicate 则追加为 name_new。
 * - 递归处理 children / environments。
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
      const existing = parent.find(
        (n) => n.name === inc.name && n.type === inc.type,
      )
      if (existing) {
        if (policy === 'overwrite') {
          // 保留 existing.id，替换其余字段
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
