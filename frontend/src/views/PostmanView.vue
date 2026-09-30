<template>
  <div class="postman-view">
    <!-- 左侧：Collections + History -->
    <aside class="sidebar" v-show="!sidebarHidden" :style="{ width: sidebarWidth + 'px' }">
      <div class="side-collections">
        <CollectionsTree @open="onOpenNode" />
      </div>
      <div class="side-divider"></div>
      <div class="side-section">
        <div class="section-header" @click="historyOpen = !historyOpen">
          <icon-down v-if="historyOpen" />
          <icon-right v-else />
          <span>History</span>
          <a-button v-if="history.length" size="mini" status="danger" type="secondary" :disabled="!history.length"
            @click.stop="onClear">清空</a-button>
        </div>
        <div v-if="historyOpen" class="history-list">
          <div v-for="(item, i) in history" :key="i" class="history-item" @click="onLoadHistory(item)">
            <span class="m" :class="item.method.toLowerCase()">{{ item.method }}</span>
            <span class="u" :title="item.url">{{ item.url }}</span>
            <span class="s" :class="statusClass(item.status_code)">{{ item.status_code || '—' }}</span>
          </div>
          <a-empty v-if="!history.length" description="暂无历史" style="padding: 12px 0" />
        </div>
      </div>
    </aside>
    <!-- 侧边栏拖拽条 -->
    <div v-if="!sidebarHidden" class="splitter v-splitter" @mousedown="startSidebarDrag" />

    <!-- 右侧：标签页 + 工作区 -->
    <section class="workbench">
      <div class="tab-bar">
        <div class="tabs-left">
          <div v-for="t in wb.tabs" :key="t.id" class="tab" :class="{ active: t.id === wb.activeId }"
            @click="wb.setActive(t.id)">
            <span class="tab-method"
              :class="t.kind === 'websocket' ? 'ws' : t.kind === 'mcp' ? 'mcp' : t.request.method.toLowerCase()">
              {{ t.kind === 'websocket' ? 'WS' : t.kind === 'mcp' ? 'MCP' : t.request.method }}
            </span>
            <span class="tab-title">{{ t.title }}</span>
            <icon-close class="tab-close" @click.stop="wb.closeTab(t.id)" />
          </div>
          <a-dropdown @select="(k) => wb.openBlank(String(k) as 'http' | 'websocket' | 'mcp')">
            <a-button shape="circle" size="small"><icon-plus /></a-button>
            <template #content>
              <a-doption value="http">HTTP Request</a-doption>
              <a-doption value="websocket">WebSocket</a-doption>
              <a-doption value="mcp">MCP Request</a-doption>
            </template>
          </a-dropdown>
        </div>
        <div class="tabs-right">
          <a-button size="small" @click="sidebarHidden = !sidebarHidden">
            <template #icon>
              <IconShowLeft v-if="sidebarHidden" class="svg-icon" />
              <IconHiddenLeft v-else class="svg-icon" />
            </template>
          </a-button>
          <a-button size="small" @click="toggleLayout">
            <template #icon>
              <IconRightLeft v-if="responseLayout === 'bottom'" class="svg-icon" />
              <IconTopBottom v-else class="svg-icon" />
            </template>
          </a-button>
          <a-button size="small" @click="settingsOpen = true">
            <template #icon><icon-settings /></template>
          </a-button>
        </div>
      </div>

      <div class="pane custom-arco-design" v-if="wb.activeTab" :key="wb.activeTab.id">
        <template v-if="wb.activeTab.kind === 'http'">
          <RequestBar :tab="wb.activeTab" @send="onSend" @cancel="wb.cancel" @save="onSaveRequest" />
          <div class="http-body" ref="paneRef"
            :style="{ flexDirection: responseLayout === 'bottom' ? 'column' : 'row' }">
            <div class="half"
              :style="responseLayout === 'bottom' ? { height: (100 - responseRatio) + '%' } : { width: (100 - responseRatio) + '%' }">
              <RequestPane :tab="wb.activeTab" />
            </div>
            <div class="splitter" :class="responseLayout === 'bottom' ? 'h-splitter' : 'v-splitter'"
              @mousedown="startRespDrag" />
            <div class="half"
              :style="responseLayout === 'bottom' ? { height: responseRatio + '%' } : { width: responseRatio + '%' }">
              <ResponsePane :tab="wb.activeTab" />
            </div>
          </div>
        </template>
        <McpPane v-else-if="wb.activeTab.kind === 'mcp'" :tab="wb.activeTab" @save="onSaveMcp" />
        <WebSocketPane v-else :tab="wb.activeTab" />
      </div>
      <div class="empty" v-else>
        <a-empty description="从左侧 Collections 选择请求，或点击 + 新建" />
      </div>
    </section>

    <SettingsDialog v-model="settingsOpen" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Modal } from '@arco-design/web-vue'

import CollectionsTree from '@/components/CollectionsTree.vue'
import RequestBar from '@/components/RequestBar.vue'
import RequestPane from '@/components/RequestPane.vue'
import ResponsePane from '@/components/ResponsePane.vue'
import WebSocketPane from '@/components/WebSocketPane.vue'
import McpPane from '@/components/McpPane.vue'
import SettingsDialog from '@/components/SettingsDialog.vue'
import { useCollectionsStore } from '@/stores/collections'
import { useWorkbenchStore } from '@/stores/workbench'
import { useHttpStore } from '@/stores/http'
import { api } from '@/api/client'
import IconShowLeft from '@/imgs/icon/show_left.svg?component'
import IconHiddenLeft from '@/imgs/icon/hidden_left.svg?component'
import IconRightLeft from '@/imgs/icon/right_left.svg?component'
import IconTopBottom from '@/imgs/icon/top_bottom.svg?component'
import type { CollectionNode, HttpCallRecord } from '@/api/types'

const collections = useCollectionsStore()
const wb = useWorkbenchStore()
const http = useHttpStore()

const history = ref<HttpCallRecord[]>([])
const historyOpen = ref(true)

// 布局状态
const sidebarHidden = ref(false)
const sidebarWidth = ref(280)
const responseLayout = ref<'bottom' | 'right'>('right')
const responseRatio = ref(50)
const settingsOpen = ref(false)
const paneRef = ref<HTMLElement | null>(null)

onMounted(async () => {
  await Promise.all([collections.load(), http.loadHistory()])
  history.value = http.history
})

function toggleLayout() {
  responseLayout.value = responseLayout.value === 'bottom' ? 'right' : 'bottom'
}

// 通用拖拽：监听 mousemove / mouseup
function startDrag(e: MouseEvent, onMove: (dx: number, dy: number) => void) {
  e.preventDefault()
  const startX = e.clientX
  const startY = e.clientY
  function move(ev: MouseEvent) {
    onMove(ev.clientX - startX, ev.clientY - startY)
  }
  function up() {
    document.removeEventListener('mousemove', move)
    document.removeEventListener('mouseup', up)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }
  document.addEventListener('mousemove', move)
  document.addEventListener('mouseup', up)
  document.body.style.cursor = responseLayout.value === 'bottom' ? 'row-resize' : 'col-resize'
  document.body.style.userSelect = 'none'
}

function startSidebarDrag(e: MouseEvent) {
  startDrag(e, (dx) => {
    const next = sidebarWidth.value + dx
    sidebarWidth.value = Math.min(480, Math.max(180, next))
  })
}

function startRespDrag(e: MouseEvent) {
  const rect = paneRef.value?.getBoundingClientRect()
  const total = responseLayout.value === 'bottom' ? rect?.height || 1 : rect?.width || 1
  const startRatio = responseRatio.value
  startDrag(e, (dx, dy) => {
    const delta = responseLayout.value === 'bottom' ? dy : dx
    responseRatio.value = Math.min(80, Math.max(20, startRatio + (delta / total) * 100))
  })
}

function onOpenNode(node: CollectionNode) {
  wb.openFromNode(node)
}

function onSend() {
  const tab = wb.activeTab
  if (!tab) return
  wb.send(tab, (req) => {
    if (tab.nodeId) collections.saveRequest(tab.nodeId, req)
  })
}

function onSaveMcp() {
  const tab = wb.activeTab
  if (!tab?.nodeId) return
  const node = collections.findNode(tab.nodeId)
  if (!node) return
  node.mcp_url = tab.mcp_url
  node.mcp_headers = tab.mcp_headers
  node.mcp_tool = tab.mcp_tool
  node.mcp_args = tab.mcp_args
  collections.persist()
}

/** 从 curl 导入等操作后，把当前请求持久化到集合节点。 */
function onSaveRequest() {
  const tab = wb.activeTab
  if (!tab?.nodeId) return
  const node = collections.findNode(tab.nodeId)
  if (!node || node.type !== 'request') return
  node.request = JSON.parse(JSON.stringify(tab.request))
  collections.persist()
}

function onLoadHistory(item: HttpCallRecord) {
  wb.openBlank('http')
  const tab = wb.activeTab
  if (!tab) return
  tab.request.method = item.method as typeof tab.request.method
  tab.request.url = item.url
  tab.request.headers = item.headers?.length ? JSON.parse(JSON.stringify(item.headers)) : [{ key: '', value: '', enabled: true }]
  tab.request.body_type = (item.body_type as typeof tab.request.body_type) || 'none'
  tab.request.body = item.body || ''
  tab.title = `${item.method} ${item.url}`
}

async function onClear() {
  try {
    await new Promise<void>((resolve, reject) => {
      Modal.confirm({
        title: '确认',
        content: '确定清空所有 HTTP 历史？',
        onOk: () => { resolve() },
        onCancel: () => { reject(new Error('cancel')) },
      })
    })
  } catch {
    return
  }
  await api.del('/api/http/history')
  await http.loadHistory()
  history.value = http.history
}

function statusClass(code: number) {
  if (!code) return ''
  if (code < 300) return 'ok'
  if (code < 400) return 'redirect'
  return 'err'
}
</script>

<style lang="less" scoped>
.postman-view {
  display: flex;
  height: 100%;
  background: var(--el-bg-color-page);
  color: var(--el-text-color-primary);
  font-family: var(--app-font-family);
  font-size: var(--app-font-size);
}

.sidebar {
  flex-shrink: 0;
  border-right: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;
  background: var(--el-bg-color);
  overflow: hidden;
}

.side-collections {
  flex: 1 1 55%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.side-divider {
  height: 1px;
  background: var(--el-border-color-lighter);
  flex-shrink: 0;
}

.side-section {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1 1 45%;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
}

.history-list {
  flex: 1;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 12px;

  &:hover {
    background: var(--el-fill-color-light);
  }

  .m {
    font-weight: 700;
    width: 48px;
  }

  .m.get {
    color: #49cc90;
  }

  .m.post {
    color: #fca130;
  }

  .m.put {
    color: #61affe;
  }

  .m.delete {
    color: #f93e3e;
  }

  .u {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .s.ok {
    color: var(--el-color-success);
  }

  .s.err {
    color: var(--el-color-danger);
  }
}

.workbench {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--el-bg-color);
}

.tab-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 8px 0;
  border-bottom: 1px solid var(--el-border-color);
  background: var(--el-bg-color-page);
}

.tabs-left {
  display: flex;
  align-items: center;
  gap: 2px;
  overflow-x: auto;
}

.tabs-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;

  .svg-icon {
    width: 14px;
    height: 14px;
  }
}

.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: 1px solid var(--el-border-color);
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  cursor: pointer;
  font-size: 12px;
  background: var(--el-bg-color);
  max-width: 200px;
  flex-shrink: 0;

  &.active {
    font-weight: 600;
    background: var(--el-color-primary-light-9);
  }

  .tab-method {
    font-size: 10px;
    font-weight: 700;
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

  .tab-title {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tab-close {
    cursor: pointer;
    border-radius: 50%;

    &:hover {
      background: var(--el-fill-color-dark);
    }
  }
}

.pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.http-body {
  flex: 1;
  min-height: 0;
  display: flex;
}

.half {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}

.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 拖拽条 */
.splitter {
  flex-shrink: 0;
  z-index: 5;
}

.v-splitter {
  width: 4px;
  cursor: col-resize;
  background: transparent;

  &:hover {
    background: var(--el-color-primary-light-5);
  }
}

.h-splitter {
  height: 4px;
  cursor: row-resize;
  background: transparent;

  &:hover {
    background: var(--el-color-primary-light-5);
  }
}
</style>
