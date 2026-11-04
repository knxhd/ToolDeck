<template>
  <div class="node-row" :style="{ paddingLeft: depth * 8 + 'px' }">
    <div class="node-line" :class="{ active: isRequest, 'drop-target': dropHover }" :draggable="draggable"
      @click="onLineClick" @dragstart="onDragStart" @dragend="onDragEnd" @dragover="onDragOver"
      @dragleave="onDragLeave" @drop.prevent="onDrop">
      <icon-right v-if="node.type !== 'request' && !expanded.has(node.id)" class="twisty" @click.stop="onToggle" />
      <icon-down v-else-if="node.type !== 'request'" class="twisty" @click.stop="onToggle" />
      <span v-else class="method-pill" :class="'m-' + methodClass">
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
        @remove="onChildRemove" @export="onChildExport" @expand="onChildExpand" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { useCollectionsStore } from '@/stores/collections'
import { treeDrag } from '@/utils/treeDrag'
import { toast } from '@/utils/feedback'
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
  expand: [id: string]
}>()

const collections = useCollectionsStore()

const hasChildren = computed(() => !!props.node.children && props.node.children.length > 0)
const isRequest = computed(() => props.node.type === 'request')
/** 请求和文件夹可拖拽；根级集合不支持移动。 */
const draggable = computed(() => props.node.type !== 'collection')
/** 拖拽悬停高亮（仅合法目标时点亮）。 */
const dropHover = ref(false)

const methodClass = computed(() => {
  if (props.node.kind === 'websocket') return 'ws'
  if (props.node.kind === 'mcp') return 'mcp'
  const m = (props.node.request?.method || 'GET').toLowerCase()
  return m
})

// ── 拖拽移动 ────────────────────────────────────────────────────
function onDragStart(e: DragEvent) {
  treeDrag.id = props.node.id
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    // Firefox 需要 setData 才会触发拖拽
    e.dataTransfer.setData('text/plain', props.node.id)
  }
}

function onDragEnd() {
  treeDrag.id = null
  dropHover.value = false
}

/** 作为放置目标时实际接收的容器 id：request 落到其父级，collection/folder 为自身。 */
function dropContainerId(): string | null {
  if (props.node.type !== 'request') return props.node.id
  return collections.findParent(props.node.id)?.id ?? null
}

function containsId(n: CollectionNode, id: string): boolean {
  if (n.id === id) return true
  if (n.children) return n.children.some((c) => containsId(c, id))
  return false
}

function canDrop(): boolean {
  const dragId = treeDrag.id
  if (!dragId || dragId === props.node.id) return false
  const dragged = collections.findNode(dragId)
  const containerId = dropContainerId()
  if (!dragged || !containerId) return false
  // 不能放入自身或自己的子孙节点（防环）
  if (containsId(dragged, containerId)) return false
  return true
}

function onDragOver(e: DragEvent) {
  if (!treeDrag.id) return // 忽略外部来源的拖拽（如文件）
  if (canDrop()) {
    e.preventDefault()
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
    dropHover.value = true
  } else {
    dropHover.value = false
  }
}

function onDragLeave() {
  dropHover.value = false
}

async function onDrop(e: DragEvent) {
  const dragId = treeDrag.id || e.dataTransfer?.getData('text/plain') || null
  dropHover.value = false
  treeDrag.id = null
  const containerId = dropContainerId()
  if (!dragId || !containerId) return
  const result = await collections.moveNode(dragId, containerId)
  if (result === 'moved') {
    emit('expand', containerId) // 展开目标，让用户看到移动结果
    toast.success('已移动')
  } else if (result === 'unchanged') {
    toast.info('位置未变化')
  } else {
    toast.warning('无法移动到该位置')
  }
}

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
function onChildExpand(id: string) { emit('expand', id) }
</script>

<style lang="less" scoped>
.node-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  user-select: none;

  // 子级列表同样保留行间距，避免选中背景连成一片
  .node-children {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .node-line {
    display: flex;
    align-items: center;
    gap: 6px;
    min-height: 26px;
    padding: 3px 6px;
    border-radius: var(--ui-radius-sm);
    cursor: pointer;
    font-size: 12.5px;
    color: var(--color-text-1);
    transition: background-color 0.12s ease, color 0.12s ease;

    &:hover {
      background: var(--ui-bg-hover);
    }

    &.active {
      background: var(--ui-bg-active);

      .node-name {
        font-weight: 600;
        color: rgb(var(--primary-6));
      }
    }

    // 拖拽悬停的合法放置目标
    &.drop-target {
      background: var(--ui-bg-active);
      box-shadow: inset 0 0 0 1.5px rgb(var(--primary-6));
    }

    &:hover .node-actions {
      visibility: visible;
    }
  }

  .twisty {
    width: 14px;
    flex-shrink: 0;
    color: var(--color-text-3);
  }

  .node-icon {
    color: var(--ui-method-mcp);
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
    gap: 0;
    display: inline-flex;

    .arco-btn {
      width: 20px;
      height: 20px;
      padding: 0;
      font-size: 12px;
      color: var(--color-text-3);

      &:hover {
        background: var(--ui-bg-hover);
        color: var(--color-text-1);
      }
    }
  }
}
</style>
