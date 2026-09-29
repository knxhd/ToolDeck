<template>
  <div class="collections-tree">
    <div class="tree-toolbar">
      <span class="tree-title">Collections</span>
      <a-button size="small" shape="circle" title="新建集合" @click="onNewCollection">
        <template #icon><icon-plus /></template>
      </a-button>
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
        />
      </template>
      <a-empty v-if="!collections.tree.length" description="暂无集合，点击 + 新建" style="padding: 16px 0" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { useCollectionsStore } from '@/stores/collections'
import { confirmDialog, promptInput, toast } from '@/utils/feedback'
import type { CollectionNode } from '@/api/types'
import NodeRow from './CollectionsNode.vue'

const emit = defineEmits<{ open: [node: CollectionNode] }>()

const collections = useCollectionsStore()
const expanded = ref<Set<string>>(new Set())

function toggle(id: string) {
  if (expanded.value.has(id)) expanded.value.delete(id)
  else expanded.value.add(id)
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
}

async function onRemove(node: CollectionNode) {
  const ok = await confirmDialog('删除', `确定删除「${node.name}」？`)
  if (!ok) return
  await collections.removeNode(node.id)
  toast.success('已删除')
}
</script>

<style lang="less" scoped>
.collections-tree {
  display: flex; flex-direction: column; height: 100%;

  .tree-toolbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 6px 8px; border-bottom: 1px solid var(--el-border-color-lighter);
  }
  .tree-title { font-weight: 600; font-size: 13px; }
  .tree-body { flex: 1; overflow-y: auto; padding: 4px 0; }
}
</style>
