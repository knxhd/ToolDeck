<template>
  <div class="collections-tree">
    <div class="tree-toolbar">
      <span class="tree-title">Collections</span>
      <div class="toolbar-actions">
        <a-tooltip content="导出全部集合" position="top">
          <a-button size="mini" type="text" @click="onExportAll">
            <template #icon><icon-export /></template>
          </a-button>
        </a-tooltip>
        <a-tooltip content="导入集合" position="top">
          <a-button size="mini" type="text" @click="onImportClick">
            <template #icon><icon-import /></template>
          </a-button>
        </a-tooltip>
        <a-tooltip content="新建集合" position="top">
          <a-button size="mini" type="text" class="add-btn" @click="onNewCollection">
            <template #icon><icon-plus /></template>
          </a-button>
        </a-tooltip>
        <input ref="fileInput" type="file" accept="application/json,.json" style="display:none" @change="onImportFile" />
      </div>
    </div>
    <div class="tree-body">
      <template v-for="node in collections.tree" :key="node.id">
        <node-row
          :node="node"
          :depth="0"
          :expanded="expanded"
          @toggle="toggle"
          @open="(n) => $emit('open', n)"
          @add-child="onAddChild"
          @rename="onRename"
          @remove="onRemove"
          @export="onExportNode"
          @expand="onExpand"
        />
      </template>
      <a-empty v-if="!collections.tree.length" description="暂无集合，点击 + 新建" style="padding: 16px 0" />
    </div>

    <a-modal v-model:visible="conflictDialogOpen" title="导入冲突处理" :footer="false" width="420px">
      <p style="margin: 0 0 12px">导入的内容中存在同名集合 / 文件夹 / 接口，如何处理？</p>
      <div style="display: flex; gap: 8px; justify-content: flex-end">
        <a-button @click="conflictDialogOpen = false">取消</a-button>
        <a-button @click="applyImport('duplicate')">新增（重命名为 _new）</a-button>
        <a-button type="primary" @click="applyImport('overwrite')">覆盖现有</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { useCollectionsStore } from '@/stores/collections'
import { useWorkbenchStore } from '@/stores/workbench'
import { exportCollections, exportOneCollection, parseImportFile, mergeIntoTree, type ConflictPolicy } from '@/utils/io'
import { confirmDialog, promptInput, toast } from '@/utils/feedback'
import type { CollectionNode } from '@/api/types'
import NodeRow from './CollectionsNode.vue'

const emit = defineEmits<{ open: [node: CollectionNode] }>()

const collections = useCollectionsStore()
const wb = useWorkbenchStore()
const expanded = ref<Set<string>>(new Set())
const fileInput = ref<HTMLInputElement | null>(null)
const conflictDialogOpen = ref(false)
const pendingImport = ref<CollectionNode[] | null>(null)

function toggle(id: string) {
  if (expanded.value.has(id)) expanded.value.delete(id)
  else expanded.value.add(id)
}

/** 拖拽放入后仅展开目标容器（不收起）。 */
function onExpand(id: string) {
  expanded.value.add(id)
}

async function onNewCollection() {
  const value = await promptInput('新建集合', 'My Collection')
  if (!value) return
  await collections.addCollection(value)
}

async function onAddChild(payload: { parentId: string; kind: string }) {
  const { parentId, kind } = payload
  if (kind === 'folder') {
    const value = await promptInput('新建子集合', 'New Folder')
    if (!value) return
    await collections.addFolder(parentId, value)
  } else if (kind === 'http' || kind === 'websocket' || kind === 'mcp') {
    const node = await collections.addRequest(parentId, kind, kind === 'mcp' ? 'New MCP' : kind === 'websocket' ? 'New WebSocket' : 'New Request')
    if (node) emit('open', node)
  }
  if (!expanded.value.has(parentId)) toggle(parentId)
}

async function onRename(node: CollectionNode) {
  const value = await promptInput('重命名', node.name)
  if (!value) return
  await collections.renameNode(node.id, value)
  // 若该节点已在 tab 中打开，同步更新 tab 标题
  wb.syncTitleByNodeId(node.id, value)
}

async function onRemove(node: CollectionNode) {
  const ok = await confirmDialog('删除', `确定删除「${node.name}」？`)
  if (!ok) return
  await collections.removeNode(node.id)
  toast.success('已删除')
}

function onExportAll() {
  if (!collections.tree.length) {
    toast.warning('暂无集合可导出')
    return
  }
  exportCollections(collections.tree)
  toast.success('已导出全部集合')
}

function onExportNode(node: CollectionNode) {
  exportOneCollection(node)
  toast.success(`已导出「${node.name}」`)
}

function onImportClick() {
  fileInput.value?.click()
}

async function onImportFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  const text = await file.text()
  let incoming: CollectionNode[]
  try {
    incoming = parseImportFile(text)
  } catch (err) {
    toast.error('导入失败：' + (err as Error).message)
    return
  }
  if (!incoming.length) {
    toast.warning('文件中没有可导入的集合')
    return
  }
  pendingImport.value = incoming
  conflictDialogOpen.value = true
}

async function applyImport(policy: ConflictPolicy) {
  const incoming = pendingImport.value
  conflictDialogOpen.value = false
  pendingImport.value = null
  if (!incoming) return
  const { added, overwritten } = mergeIntoTree(collections.tree, incoming, policy)
  await collections.persist()
  toast.success(`导入完成：新增 ${added} 项，覆盖 ${overwritten} 项`)
}
</script>

<style lang="less" scoped>
.collections-tree {
  display: flex;
  flex-direction: column;
  height: 100%;

  .tree-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
    height: 34px;
    padding: 0 6px 0 10px;
    border-bottom: 1px solid var(--ui-border-soft);
  }

  .tree-title {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--color-text-2);
  }

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 2px;

    :deep(.arco-btn) {
      width: 24px;
      height: 24px;
      padding: 0;
      border-radius: var(--ui-radius-sm);
      color: var(--color-text-3);
      font-size: 13px;

      &:hover {
        background: var(--ui-bg-hover);
        color: var(--color-text-1);
      }
    }

    :deep(.add-btn) {
      color: rgb(var(--primary-6));
      background: rgba(var(--primary-6), 0.1);

      &:hover {
        background: rgba(var(--primary-6), 0.18);
        color: rgb(var(--primary-6));
      }
    }
  }

  .tree-body {
    flex: 1;
    overflow-y: auto;
    padding: 4px 6px 8px;
  }
}
</style>
