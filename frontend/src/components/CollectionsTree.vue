<template>
  <div class="collections-tree">
    <div class="tree-toolbar">
      <span class="tree-title">Collections</span>
      <el-button size="small" circle :icon="Plus" title="新建集合" @click="onNewCollection" />
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
      <el-empty v-if="!collections.tree.length" description="暂无集合，点击 + 新建" :image-size="50" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import { useCollectionsStore } from '@/stores/collections'
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
  try {
    const { value } = await ElMessageBox.prompt('集合名称', '新建集合', { inputValue: 'My Collection' })
    await collections.addCollection(value)
  } catch { /* cancelled */ }
}

async function onAddChild(payload: { parentId: string; kind: string }) {
  const { parentId, kind } = payload
  if (kind === 'folder') {
    const { value } = await ElMessageBox.prompt('子集合名称', '新建子集合', { inputValue: 'New Folder' })
    await collections.addFolder(parentId, value)
  } else if (kind === 'http') {
    const node = await collections.addRequest(parentId, 'http', 'New Request')
    if (node) emit('open', node)
  } else {
    const node = await collections.addRequest(parentId, 'websocket', 'New WebSocket')
    if (node) emit('open', node)
  }
  if (!expanded.value.has(parentId)) toggle(parentId)
}

async function onRename(node: CollectionNode) {
  try {
    const { value } = await ElMessageBox.prompt('新名称', '重命名', { inputValue: node.name })
    await collections.renameNode(node.id, value)
  } catch { /* cancelled */ }
}

async function onRemove(node: CollectionNode) {
  try {
    await ElMessageBox.confirm(`确定删除「${node.name}」？`, '删除', { type: 'warning' })
    await collections.removeNode(node.id)
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.collections-tree { display: flex; flex-direction: column; height: 100%; }
.tree-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 8px; border-bottom: 1px solid var(--el-border-color-lighter);
}
.tree-title { font-weight: 600; font-size: 13px; }
.tree-body { flex: 1; overflow-y: auto; padding: 4px 0; }
</style>
