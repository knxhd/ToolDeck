/** Collections 树 Pinia store：整棵树在前端持有，变更后整体回写后端。 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/api/client'
import type { CollectionNode, HttpRequestData } from '@/api/types'

let seq = 0
const uid = () => `n_${Date.now().toString(36)}_${(seq++).toString(36)}`

const emptyRequest = (): HttpRequestData => ({
  method: 'GET',
  url: '',
  headers: [{ key: '', value: '', enabled: true }],
  params: [{ key: '', value: '', enabled: true }],
  body_type: 'none',
  body: '',
})

export const useCollectionsStore = defineStore('collections', () => {
  const tree = ref<CollectionNode[]>([])
  /** 当前作用域：personal 或 team。 */
  const scope = ref<'personal' | 'team'>('personal')
  /** 当前 team_id（scope=team 时有效）。 */
  const teamId = ref<number | null>(null)

  function scopeQuery(): string {
    if (scope.value === 'team' && teamId.value != null) {
      return `?scope=team&team_id=${teamId.value}`
    }
    return '?scope=personal'
  }

  async function load() {
    tree.value = await api.get<CollectionNode[]>(`/api/collections${scopeQuery()}`)
  }

  async function persist() {
    await api.put(`/api/collections${scopeQuery()}`, tree.value)
  }

  /** 切换到个人空间。 */
  async function loadPersonal() {
    scope.value = 'personal'
    teamId.value = null
    await load()
  }

  /** 切换到团队空间。 */
  async function loadTeam(id: number) {
    scope.value = 'team'
    teamId.value = id
    await load()
  }

  function findNode(id: string, nodes: CollectionNode[] = tree.value): CollectionNode | null {
    for (const n of nodes) {
      if (n.id === id) return n
      if (n.children) {
        const f = findNode(id, n.children)
        if (f) return f
      }
    }
    return null
  }

  function findParent(id: string, nodes: CollectionNode[] = tree.value, parent: CollectionNode | null = null): CollectionNode | null {
    for (const n of nodes) {
      if (n.id === id) return parent
      if (n.children) {
        const f = findParent(id, n.children, n)
        if (f !== null) return f
      }
    }
    return null
  }

  async function addCollection(name: string) {
    tree.value.push({ id: uid(), type: 'collection', name: name || 'New Collection', children: [] })
    await persist()
  }

  async function addFolder(parentId: string, name: string) {
    const parent = findNode(parentId)
    if (!parent) return
    parent.children = parent.children || []
    parent.children.push({ id: uid(), type: 'folder', name: name || 'New Folder', children: [] })
    await persist()
  }

  async function addRequest(parentId: string, kind: 'http' | 'websocket' | 'mcp', name: string) {
    const parent = findNode(parentId)
    if (!parent) return null
    parent.children = parent.children || []
    const node: CollectionNode = {
      id: uid(),
      type: 'request',
      kind,
      name: name || (kind === 'websocket' ? 'New WebSocket' : kind === 'mcp' ? 'New MCP' : 'New Request'),
    }
    if (kind === 'http') node.request = emptyRequest()
    else if (kind === 'websocket') node.ws_url = 'wss://'
    else {
      node.mcp_url = ''
      node.mcp_headers = {}
      node.mcp_tool = ''
      node.mcp_args = '{}'
    }
    parent.children.push(node)
    await persist()
    return node
  }

  async function renameNode(id: string, name: string) {
    const n = findNode(id)
    if (!n) return
    n.name = name
    await persist()
  }

  async function removeNode(id: string) {
    const walk = (nodes: CollectionNode[]): boolean => {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].id === id) {
          nodes.splice(i, 1)
          return true
        }
        if (nodes[i].children && walk(nodes[i].children!)) return true
      }
      return false
    }
    walk(tree.value)
    await persist()
  }

  async function saveRequest(id: string, request: HttpRequestData) {
    const n = findNode(id)
    if (!n) return
    n.request = JSON.parse(JSON.stringify(request))
    await persist()
  }

  return {
    tree,
    scope,
    teamId,
    load,
    loadPersonal,
    loadTeam,
    persist,
    findNode,
    findParent,
    addCollection,
    addFolder,
    addRequest,
    renameNode,
    removeNode,
    saveRequest,
  }
})

if (import.meta.hot) import.meta.hot.accept(acceptHMRUpdate(useCollectionsStore, import.meta.hot))
