<template>
  <div class="node-row" :style="{ paddingLeft: depth * 8 + 'px' }">
    <div class="node-line" :class="{ active: isRequest }" @click="onLineClick">
      <icon-right v-if="node.type !== 'request' && !expanded.has(node.id)" class="twisty" @click.stop="onToggle" />
      <icon-down v-else-if="node.type !== 'request'" class="twisty" @click.stop="onToggle" />
      <span v-else class="method-badge" :class="methodClass">
        {{ node.kind === 'websocket' ? 'WS' : node.kind === 'mcp' ? 'MCP' : (node.request?.method || 'GET') }}
      </span>
      <span class="node-name" :title="node.name">{{ node.name }}</span>
      <span class="node-actions" @click.stop>
        <a-dropdown v-if="node.type !== 'request'" @select="onCommand">
          <a-button size="mini" type="text" shape="circle" title="新建子项">
            <template #icon><icon-plus /></template>
          </a-button>
          <template #content>
            <a-doption value="http">HTTP Request</a-doption>
            <a-doption value="websocket">WebSocket Request</a-doption>
            <a-doption value="mcp">MCP Request</a-doption>
            <a-doption value="folder">Folder</a-doption>
            <a-doption value="__export__">导出</a-doption>
          </template>
        </a-dropdown>
        <a-button size="mini" type="text" shape="circle" title="重命名" @click="emit('rename', node)">
          <template #icon><icon-edit /></template>
        </a-button>
        <a-button size="mini" type="text" shape="circle" title="删除" status="danger" @click="emit('remove', node)">
          <template #icon><icon-delete /></template>
        </a-button>
      </span>
    </div>
    <div v-if="expanded.has(node.id)" class="node-children">
      <CollectionsNode v-for="child in node.children" :key="child.id" :node="child" :depth="depth + 1"
        :expanded="expanded" @toggle="onChildToggle" @open="onChildOpen" @add-child="onChildAdd" @rename="onChildRename"
        @remove="onChildRemove" @export="onChildExport" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

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
  export: [node: CollectionNode]
}>()

const hasChildren = computed(() => !!props.node.children && props.node.children.length > 0)
const isRequest = computed(() => props.node.type === 'request')

const methodClass = computed(() => {
  if (props.node.kind === 'websocket') return 'ws'
  if (props.node.kind === 'mcp') return 'mcp'
  const m = (props.node.request?.method || 'GET').toLowerCase()
  return m
})

function onCommand(kind: string | number | Record<string, unknown> | undefined) {
  const k = String(kind)
  if (k === '__export__') {
    emit('export', props.node)
    return
  }
  emit('addChild', { parentId: props.node.id, kind: k })
}

function onLineClick() {
  if (isRequest.value) emit('open', props.node)
  else emit('toggle', props.node.id)
}

function onToggle() {
  if (hasChildren.value) {
    emit('toggle', props.node.id)
  }
}

function onChildToggle(id: string) { emit('toggle', id) }
function onChildOpen(n: CollectionNode) { emit('open', n) }
function onChildAdd(p: { parentId: string; kind: string }) { emit('addChild', p) }
function onChildRename(n: CollectionNode) { emit('rename', n) }
function onChildRemove(n: CollectionNode) { emit('remove', n) }
function onChildExport(n: CollectionNode) { emit('export', n) }
</script>

<style lang="less" scoped>
.node-row {
  user-select: none;

  .node-line {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;

    &:hover {
      background: var(--el-fill-color-light);
    }

    &.active .node-name {
      font-weight: 600;
    }

    &:hover .node-actions {
      visibility: visible;
    }
  }

  .twisty {
    width: 14px;
    color: var(--el-text-color-secondary);
  }

  .node-icon {
    color: var(--el-color-warning);
  }

  .node-name {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .node-actions {
    // visibility 隐藏而非 display:none：保留布局空间，保证 dropdown 打开时 trigger 的
    // getBoundingClientRect 稳定，避免弹出层定位到左上角 (0,0)。
    visibility: hidden;
    align-items: center;
    gap: 2px;
    display: inline-flex;

    .arco-btn {
      color: var(--el-text-color-secondary);
    }
  }

  .method-badge {
    font-size: 10px;
    font-weight: 700;
    min-width: 34px;
    text-align: center;
    padding: 1px 4px;
    border-radius: 3px;
    color: #fff;

    &.get {
      background: #49cc90;
    }

    &.post {
      background: #fca130;
    }

    &.put {
      background: #61affe;
    }

    &.delete {
      background: #f93e3e;
    }

    &.patch {
      background: #50e3c2;
    }

    &.ws {
      background: #8e44ad;
    }

    &.mcp {
      background: #e6a23c;
    }
  }
}
</style>
