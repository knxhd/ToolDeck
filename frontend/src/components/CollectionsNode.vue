<template>
  <div class="node-row" :style="{ paddingLeft: depth * 14 + 6 + 'px' }">
    <div class="node-line" :class="{ active: isRequest }" @click="onLineClick">
      <el-icon class="twisty" @click.stop="onToggle">
        <ArrowRight v-if="hasChildren && !expanded.has(node.id)" />
        <ArrowDown v-else-if="hasChildren" />
      </el-icon>
      <el-icon class="node-icon">
        <Folder v-if="node.type !== 'request' && !expanded.has(node.id)" />
        <FolderOpened v-else-if="node.type !== 'request'" />
        <span v-else class="method-badge" :class="methodClass">
          {{ node.kind === 'websocket' ? 'WS' : node.kind === 'mcp' ? 'MCP' : (node.request?.method || 'GET') }}
        </span>
      </el-icon>
      <span class="node-name" :title="node.name">{{ node.name }}</span>
      <span class="node-actions" @click.stop>
        <el-dropdown trigger="click" @command="onCommand" v-if="node.type !== 'request'">
          <el-icon class="action-btn" title="新建子项"><Plus /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="http">HTTP Request</el-dropdown-item>
              <el-dropdown-item command="websocket">WebSocket Request</el-dropdown-item>
              <el-dropdown-item command="mcp">MCP Request</el-dropdown-item>
              <el-dropdown-item command="folder">Folder</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-icon class="action-btn" title="重命名" @click="emit('rename', node)"><Edit /></el-icon>
        <el-icon class="action-btn danger" title="删除" @click="emit('remove', node)"><Delete /></el-icon>
      </span>
    </div>
    <div v-if="hasChildren && expanded.has(node.id)" class="node-children">
      <CollectionsNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
        :expanded="expanded"
        @toggle="onChildToggle"
        @open="onChildOpen"
        @add-child="onChildAdd"
        @rename="onChildRename"
        @remove="onChildRemove"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  ArrowRight, ArrowDown, Folder, FolderOpened, Plus, Edit, Delete,
} from '@element-plus/icons-vue'

import type { CollectionNode } from '@/api/types'

const props = defineProps<{
  node: CollectionNode
  depth: number
  expanded: Set<string>
}>()

const emit = defineEmits<{
  toggle: [id: string]
  open: [node: CollectionNode]
  addChild: [payload: { parentId: string; kind: string }]
  rename: [node: CollectionNode]
  remove: [node: CollectionNode]
}>()

const hasChildren = computed(() => !!props.node.children && props.node.children.length > 0)
const isRequest = computed(() => props.node.type === 'request')

const methodClass = computed(() => {
  if (props.node.kind === 'websocket') return 'ws'
  if (props.node.kind === 'mcp') return 'mcp'
  const m = (props.node.request?.method || 'GET').toLowerCase()
  return m
})

function onCommand(kind: string) {
  emit('addChild', { parentId: props.node.id, kind })
}

function onLineClick() {
  if (isRequest.value) emit('open', props.node)
  else emit('toggle', props.node.id)
}

function onToggle() {
  if (hasChildren.value) emit('toggle', props.node.id)
}

function onChildToggle(id: string) { emit('toggle', id) }
function onChildOpen(n: CollectionNode) { emit('open', n) }
function onChildAdd(p: { parentId: string; kind: string }) { emit('addChild', p) }
function onChildRename(n: CollectionNode) { emit('rename', n) }
function onChildRemove(n: CollectionNode) { emit('remove', n) }
</script>

<style lang="less" scoped>
.node-row {
  user-select: none;

  .node-line {
    display: flex; align-items: center; gap: 4px;
    padding: 3px 6px; border-radius: 4px; cursor: pointer; font-size: 13px;

    &:hover { background: var(--el-fill-color-light); }
    &.active .node-name { font-weight: 600; }
    &:hover .node-actions { display: inline-flex; }
  }

  .twisty { width: 14px; color: var(--el-text-color-secondary); }
  .node-icon { color: var(--el-color-warning); }
  .node-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .node-actions { display: none; align-items: center; gap: 2px; }

  .action-btn {
    cursor: pointer; padding: 2px; border-radius: 3px;
    &:hover { background: var(--el-fill-color-dark); }
    &.danger:hover { color: var(--el-color-danger); }
  }

  .method-badge {
    font-size: 10px; font-weight: 700; min-width: 34px; text-align: center;
    padding: 1px 4px; border-radius: 3px; color: #fff;

    &.get { background: #49cc90; }
    &.post { background: #fca130; }
    &.put { background: #61affe; }
    &.delete { background: #f93e3e; }
    &.patch { background: #50e3c2; }
    &.ws { background: #8e44ad; }
    &.mcp { background: #e6a23c; }
  }
}
</style>
