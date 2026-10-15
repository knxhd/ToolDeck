/** 环境变量 store：围绕「当前请求所属集合」管理多套环境。
 *
 * - 环境挂在 collection 根节点上（environments / activeEnvId 字段），随整树一起持久化。
 * - PostmanView 在切换标签页时调用 setCurrentNode(nodeId)，本 store 据此向上找到所属集合。
 * - 发送请求前，workbench 从这里取 vars 做 {{var}} 插值。
 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { useCollectionsStore } from './collections'
import type { CollectionNode, Environment } from '@/api/types'

let seq = 0
const envId = () => `env_${Date.now().toString(36)}_${(seq++).toString(36)}`

/** 在树中找 nodeId 所属的 collection 根节点（folder 不算集合）。 */
function findOwningCollection(
  nodes: CollectionNode[],
  nodeId: string,
  current: CollectionNode | null = null,
): CollectionNode | null {
  for (const n of nodes) {
    const cur = n.type === 'collection' ? n : current
    if (n.id === nodeId) {
      // 若点中的本身就是集合节点，就返回它自己
      return n.type === 'collection' ? n : cur
    }
    if (n.children) {
      const found = findOwningCollection(n.children, nodeId, cur)
      if (found) return found
    }
  }
  return null
}

export const useEnvironmentsStore = defineStore('environments', () => {
  const collections = useCollectionsStore()

  /** 当前激活标签页对应的请求节点 id。 */
  const currentNodeId = ref<string | null>(null)

  /** 当前环境管理对话框正在编辑的集合 id（默认跟随 currentNodeId 所属集合）。 */
  const dialogCollectionId = ref<string | null>(null)

  const collection = computed<CollectionNode | null>(
    () => (currentNodeId.value ? findOwningCollection(collections.tree, currentNodeId.value) : null),
  )

  const envs = computed<Environment[]>(() => collection.value?.environments ?? [])

  const activeEnvId = computed<string | null>(() => collection.value?.activeEnvId ?? null)

  const activeEnv = computed<Environment | null>(
    () => envs.value.find((e) => e.id === activeEnvId.value) ?? null,
  )

  /** 当前激活环境中启用的变量表（发送请求时用于插值）。 */
  const vars = computed<Record<string, string>>(() => {
    const out: Record<string, string> = {}
    for (const item of activeEnv.value?.variables ?? []) {
      if (item.enabled && item.key) out[item.key] = item.value
    }
    return out
  })

  function setCurrentNode(nodeId: string | null) {
    currentNodeId.value = nodeId
  }

  /** 对话框要编辑的集合；若未指定则跟随当前所属集合。 */
  function targetCollection(): CollectionNode | null {
    if (dialogCollectionId.value) {
      return collections.findNode(dialogCollectionId.value)
    }
    return collection.value
  }

  async function setActiveEnv(id: string | null) {
    const c = collection.value
    if (!c) return
    c.activeEnvId = id
    await collections.persist()
  }

  /** 用整组 environments 覆盖某个集合（对话框 Save 时调用）。 */
  async function replaceEnvs(envList: Environment[]) {
    const c = targetCollection()
    if (!c) return
    c.environments = envList
    // 当前激活环境若已被删，回退到 null
    if (c.activeEnvId && !envList.some((e) => e.id === c.activeEnvId)) {
      c.activeEnvId = null
    }
    await collections.persist()
  }

  function openDialog(collectionId?: string) {
    dialogCollectionId.value = collectionId ?? null
  }

  function closeDialog() {
    dialogCollectionId.value = null
  }

  return {
    currentNodeId,
    dialogCollectionId,
    collection,
    envs,
    activeEnvId,
    activeEnv,
    vars,
    setCurrentNode,
    setActiveEnv,
    targetCollection,
    replaceEnvs,
    openDialog,
    closeDialog,
    // 暴露给对话框用
    envId,
  }
})

if (import.meta.hot) import.meta.hot.accept(acceptHMRUpdate(useEnvironmentsStore, import.meta.hot))
