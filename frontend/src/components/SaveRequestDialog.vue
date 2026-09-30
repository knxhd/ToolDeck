<template>
  <a-modal
    :visible="visible"
    width="560px"
    :footer="false"
    @cancel="onClose"
  >
    <template #title>Save Request</template>

    <div class="field">
      <div class="field-label">Request name</div>
      <a-input v-model="name" autofocus @press-enter="onSave" />
    </div>

    <div class="field">
      <div class="field-label">Save to Collections</div>
      <!-- 面包屑 -->
      <div class="crumb">
        <span class="crumb-item" @click="goRoot">Collections</span>
        <template v-for="(n, i) in path" :key="n.id">
          <span class="crumb-sep">›</span>
          <span class="crumb-item" @click="goTo(i)">{{ n.name }}</span>
        </template>
      </div>

      <a-input v-model="filter" placeholder="Search for folder..." allow-clear style="margin: 8px 0" />

      <div class="folder-list">
        <div
          v-for="f in visibleFolders"
          :key="f.id"
          class="folder-item"
          @click="enterFolder(f)"
        >
          <span class="folder-icon">📁</span>
          <span class="folder-name">{{ f.name }}</span>
          <span class="folder-arrow">›</span>
        </div>
        <a-empty v-if="!visibleFolders.length" description="无文件夹" :image-size="40" />
      </div>

      <div class="dialog-actions">
        <a-button type="text" @click="onNewFolder">📁 New Folder</a-button>
        <a-button v-if="atRoot" type="text" @click="onNewCollection">+ New Collection</a-button>
        <div class="right">
          <a-button @click="onClose">Cancel</a-button>
          <a-button type="primary" @click="onSave">Save</a-button>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useCollectionsStore } from '@/stores/collections'
import { promptInput, toast } from '@/utils/feedback'
import type { CollectionNode, OpenTab } from '@/api/types'

const props = defineProps<{ visible: boolean; tab: OpenTab | null }>()
const emit = defineEmits<{ 'update:visible': [v: boolean]; saved: [nodeId: string] }>()

const collections = useCollectionsStore()

const name = ref('')
const filter = ref('')
/** 从根集合到当前所在文件夹的路径（不含根 Collections 虚拟层）。 */
const path = ref<CollectionNode[]>([])

watch(
  () => props.visible,
  (v) => {
    if (v) init()
  },
)

function init() {
  filter.value = ''
  const tab = props.tab
  name.value = tab?.title || ''
  // 若当前标签已挂在某个请求节点上，定位到它所在的集合/文件夹
  if (tab?.nodeId) {
    const found = findPath(tab.nodeId)
    if (found) path.value = found
    else path.value = []
  } else {
    path.value = []
  }
}

/** 找 nodeId 从根到其父目录的路径（collection 根 → ... → 所在 folder）。 */
function findPath(nodeId: string): CollectionNode[] | null {
  function walk(nodes: CollectionNode[], trail: CollectionNode[]): CollectionNode[] | null {
    for (const n of nodes) {
      const next = n.type === 'request' ? trail : [...trail, n]
      if (n.id === nodeId) return trail
      if (n.children) {
        const f = walk(n.children, next)
        if (f) return f
      }
    }
    return null
  }
  return walk(collections.tree, [])
}

/** 当前所在节点：path 最后一项；根层级为 null。 */
const current = computed<CollectionNode | null>(() => path.value[path.value.length - 1] || null)

const atRoot = computed(() => path.value.length === 0)

const childNodes = computed<CollectionNode[]>(() => {
  if (!current.value) return collections.tree
  return current.value.children || []
})

const visibleFolders = computed<CollectionNode[]>(() => {
  const q = filter.value.trim().toLowerCase()
  // 根层级显示 collection；下钻后显示 folder
  return childNodes.value
    .filter((n) => atRoot.value ? n.type === 'collection' : n.type === 'folder')
    .filter((n) => !q || n.name.toLowerCase().includes(q))
})

function goRoot() {
  path.value = []
}

function goTo(i: number) {
  path.value = path.value.slice(0, i + 1)
}

function enterFolder(n: CollectionNode) {
  path.value = [...path.value, n]
}

async function onNewFolder() {
  if (atRoot.value) {
    toast.warning('请先进入一个集合，再在其中新建文件夹')
    return
  }
  const label = await promptInput('新建文件夹', 'New Folder')
  if (!label || !current.value) return
  collections.addFolder(current.value.id, label)
}

async function onNewCollection() {
  const label = await promptInput('新建集合', 'My Collection')
  if (!label) return
  await collections.addCollection(label)
}

async function onSave() {
  const tab = props.tab
  if (!tab) return
  const trimmed = name.value.trim()
  if (!trimmed) {
    toast.warning('请输入请求名称')
    return
  }
  // 父节点：当前所在 folder；若在根层级，必须选一个 collection
  let parent = current.value
  if (atRoot.value) {
    toast.warning('请选择一个集合')
    return
  }
  if (!parent) return

  if (tab.nodeId) {
    // 已存在：重命名 + 更新 request
    const node = collections.findNode(tab.nodeId)
    if (node) {
      node.name = trimmed
      node.request = JSON.parse(JSON.stringify(tab.request))
      await collections.persist()
      tab.title = trimmed
      toast.success('已保存')
      emit('saved', node.id)
      emit('update:visible', false)
      return
    }
  }

  // 新建 request 节点
  const node: CollectionNode = {
    id: `n_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    type: 'request',
    kind: tab.kind === 'websocket' ? 'websocket' : tab.kind === 'mcp' ? 'mcp' : 'http',
    name: trimmed,
  }
  if (node.kind === 'http') node.request = JSON.parse(JSON.stringify(tab.request))
  else if (node.kind === 'websocket') node.ws_url = tab.ws_url
  else {
    node.mcp_url = tab.mcp_url
    node.mcp_headers = tab.mcp_headers
    node.mcp_tool = tab.mcp_tool
    node.mcp_args = tab.mcp_args
  }
  parent.children = parent.children || []
  parent.children.push(node)
  await collections.persist()
  tab.nodeId = node.id
  tab.title = trimmed
  toast.success('已保存到集合')
  emit('saved', node.id)
  emit('update:visible', false)
}

function onClose() {
  emit('update:visible', false)
}
</script>

<style lang="less" scoped>
.field-label {
  font-weight: 600;
  margin-bottom: 6px;
}

.crumb {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 4px 0 8px;

  .crumb-item {
    cursor: pointer;
    &:hover { color: var(--el-color-primary); }
  }
  .crumb-sep { margin: 0 6px; }
}

.folder-list {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  padding: 4px;
  max-height: 220px;
  overflow-y: auto;
}

.folder-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;

  &:hover { background: var(--el-fill-color-light); }

  .folder-name { flex: 1; }
  .folder-arrow { color: var(--el-text-color-secondary); }
}

.dialog-actions {
  display: flex;
  align-items: center;
  margin-top: 12px;
  gap: 8px;

  .right {
    margin-left: auto;
    display: flex;
    gap: 8px;
  }
}
</style>
