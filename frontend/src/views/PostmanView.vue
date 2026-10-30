<template>
  <div class="postman-view">
    <!-- 左侧：Collections + History -->
    <aside class="sidebar" v-show="!sidebarHidden" :style="{ width: sidebarWidth + 'px' }">
      <div class="side-collections">
        <CollectionsTree @open="onOpenNode" />
      </div>
      <div class="side-divider"></div>
      <div class="side-section"
        :style="{ flex: historyOpen ? '1 1 45%' : '', marginBottom: historyOpen ? '0' : '8px', marginTop: historyOpen ? '0' : '8px' }">
        <div class="section-header" @click="historyOpen = !historyOpen">
          <icon-down v-if="historyOpen" />
          <icon-right v-else />
          <span>History</span>

          <a-button v-if="history.length" size="mini" status="danger" type="text" :disabled="!history.length"
            @click.stop="onClear">
            <template #icon>
              <icon-delete />
            </template>
          </a-button>
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
        <div class="tabs-left custom-arco-design">
          <a-tabs :active-key="wb.activeId ?? ''" :hide-content="true" :editable="true" :show-add-button="true"
            type="card-gutter" class="workbench-tabs" @change="(k: string | number) => wb.setActive(String(k))"
            @delete="(k: string | number) => wb.closeTab(String(k))" @add="() => wb.openBlank('http')">
            <a-tab-pane v-for="t in wb.tabs" :key="t.id" :closable="true">
              <template #title>
                <span class="tab-method"
                  :class="t.kind === 'websocket' ? 'ws' : t.kind === 'mcp' ? 'mcp' : t.request.method.toLowerCase()">
                  {{ t.kind === 'websocket' ? 'WS' : t.kind === 'mcp' ? 'MCP' : t.request.method }}
                </span>
                <span class="tab-title">{{ t.dirty ? '* ' : '' }}{{ t.title }}</span>
              </template>
            </a-tab-pane>
          </a-tabs>
        </div>
        <div class="tabs-right">
          <!-- 集合级占位符 -->
          <a-tooltip :content="env.collection ? `编辑集合「${env.collection.name}」的占位符` : '请先从集合打开请求'">
            <a-button size="small" class="env-btn" :disabled="!env.collection" @click="phDialogOpen = true">
              <template #icon><icon-code-block /></template>
              占位符
              <span v-if="collectionPhCount" class="ph-count">{{ collectionPhCount }}</span>
            </a-button>
          </a-tooltip>
          <!-- 环境切换 -->
          <a-dropdown @select="onEnvSelect" :disabled="!env.collection">
            <a-button size="small" class="env-btn">
              <template #icon><icon-cloud /></template>
              {{ env.activeEnv ? env.activeEnv.name : 'No Environment' }}
            </a-button>
            <template #content>
              <a-doption value="__none">No Environment</a-doption>
              <a-doption v-for="e in env.envs" :key="e.id" :value="e.id">
                <span v-if="e.id === env.activeEnvId">✓ </span>{{ e.name }}
              </a-doption>
              <a-doption v-if="env.envs.length" disabled>────────</a-doption>
              <a-doption value="__manage">管理环境…</a-doption>
            </template>
          </a-dropdown>
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
            <div class="half" ref="reqPaneRef"
              :style="responseLayout === 'bottom' ? { height: (100 - responseRatio) + '%' } : { width: (100 - responseRatio) + '%' }">
              <RequestPane :tab="wb.activeTab" />
            </div>
            <div class="splitter" :class="responseLayout === 'bottom' ? 'h-splitter' : 'v-splitter'"
              @mousedown="startRespDrag" />
            <div class="half" ref="respPaneRef"
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
    <EnvironmentsDialog v-model:visible="envDialogOpen" />
    <CollectionPlaceholdersDialog v-model:visible="phDialogOpen" />
    <SaveRequestDialog v-model:visible="saveDialogOpen" :tab="wb.activeTab" @saved="onRequestSaved" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Modal } from '@arco-design/web-vue'

import CollectionsTree from '@/components/CollectionsTree.vue'
import RequestBar from '@/components/RequestBar.vue'
import RequestPane from '@/components/RequestPane.vue'
import ResponsePane from '@/components/ResponsePane.vue'
import WebSocketPane from '@/components/WebSocketPane.vue'
import McpPane from '@/components/McpPane.vue'
import SettingsDialog from '@/components/SettingsDialog.vue'
import EnvironmentsDialog from '@/components/EnvironmentsDialog.vue'
import CollectionPlaceholdersDialog from '@/components/CollectionPlaceholdersDialog.vue'
import SaveRequestDialog from '@/components/SaveRequestDialog.vue'
import { useCollectionsStore } from '@/stores/collections'
import { useWorkbenchStore } from '@/stores/workbench'
import { useEnvironmentsStore } from '@/stores/environments'
import { useHttpStore } from '@/stores/http'
import { api } from '@/api/client'
import { toast } from '@/utils/feedback'
import IconShowLeft from '@/imgs/icon/show_left.svg?component'
import IconHiddenLeft from '@/imgs/icon/hidden_left.svg?component'
import IconRightLeft from '@/imgs/icon/right_left.svg?component'
import IconTopBottom from '@/imgs/icon/top_bottom.svg?component'
import type { CollectionNode, HttpCallRecord } from '@/api/types'

const collections = useCollectionsStore()
const wb = useWorkbenchStore()
const http = useHttpStore()
const env = useEnvironmentsStore()

const history = ref<HttpCallRecord[]>([])
const historyOpen = ref(false)

// 布局状态
const sidebarHidden = ref(false)
const sidebarWidth = ref(280)
const responseLayout = ref<'bottom' | 'right'>('right')
const responseRatio = ref(50)
const settingsOpen = ref(false)
const envDialogOpen = ref(false)
const phDialogOpen = ref(false)
/** 当前集合启用的占位符数量（显示在按钮角标）。 */
const collectionPhCount = computed(() => Object.keys(env.collectionPlaceholderVars).length)
const saveDialogOpen = ref(false)
const paneRef = ref<HTMLElement | null>(null)
const reqPaneRef = ref<HTMLElement | null>(null)
const respPaneRef = ref<HTMLElement | null>(null)

// 切换标签页时，把当前请求节点 id 同步给环境 store，据此找到所属集合
watch(
  () => wb.activeTab?.nodeId ?? null,
  (id) => env.setCurrentNode(id),
)

// track dirty: refresh snapshot on tab switch, mark dirty on edit
let requestSnapshot = ''
watch(
  () => wb.activeTab?.id,
  () => {
    const t = wb.activeTab
    requestSnapshot = t && t.kind === 'http' ? JSON.stringify(t.request) : ''
  },
  { immediate: true },
)
watch(
  () => wb.activeTab?.request,
  (req) => {
    const t = wb.activeTab
    if (!t || t.kind !== 'http') return
    if (JSON.stringify(req) !== requestSnapshot) t.dirty = true
  },
  { deep: true },
)


function onEnvSelect(value: string | number | Record<string, unknown> | undefined) {
  const v = String(value)
  if (v === '__manage') {
    env.openDialog()
    envDialogOpen.value = true
    return
  }
  env.setActiveEnv(v === '__none' ? null : v)
}

onMounted(async () => {
  await Promise.all([collections.load(), http.loadHistory()])
  history.value = http.history
  window.addEventListener('keydown', onGlobalKeydown, true)
})

onUnmounted(() => window.removeEventListener('keydown', onGlobalKeydown, true))

function onGlobalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    const tab = wb.activeTab
    if (!tab || tab.kind !== 'http') return
    if (!tab.dirty) return
    if (tab.nodeId) silentSave(tab)
    else saveDialogOpen.value = true
  }
}

/** 已绑定节点的请求：直接写回集合树，不弹框。 */
async function silentSave(tab: NonNullable<typeof wb.activeTab>) {
  if (!tab.nodeId) return
  const node = collections.findNode(tab.nodeId)
  if (!node) return
  node.request = JSON.parse(JSON.stringify(tab.request))
  node.name = tab.title
  await collections.persist()
  tab.dirty = false
  requestSnapshot = JSON.stringify(tab.request)
  toast.success('已保存')
}

function onRequestSaved() {
  const t = wb.activeTab
  if (t && t.kind === 'http') {
    t.dirty = false
    requestSnapshot = JSON.stringify(t.request)
  }
}

function toggleLayout() {
  responseLayout.value = responseLayout.value === 'bottom' ? 'right' : 'bottom'
}

// 通用拖拽：监听 mousemove / mouseup
function startDrag(e: MouseEvent, onMove: (dx: number, dy: number) => void) {
  e.preventDefault()
  const startX = e.clientX
  const startY = e.clientY
  let rafId = 0
  let pendingDx = 0
  let pendingDy = 0

  function flush() {
    rafId = 0
    const dx = pendingDx
    const dy = pendingDy
    pendingDx = 0
    pendingDy = 0
    onMove(dx, dy)
  }
  function move(ev: MouseEvent) {
    pendingDx = ev.clientX - startX
    pendingDy = ev.clientY - startY
    // 用 rAF 合并高频 mousemove，避免每帧触发多次 Vue 响应式更新导致卡顿
    if (!rafId) rafId = requestAnimationFrame(flush)
  }
  function up() {
    if (rafId) cancelAnimationFrame(rafId)
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
  const container = paneRef.value
  const reqEl = reqPaneRef.value
  const respEl = respPaneRef.value
  if (!container || !reqEl || !respEl) return
  const isBottom = responseLayout.value === 'bottom'
  const rect = container.getBoundingClientRect()
  const containerSize = isBottom ? rect.height : rect.width
  const splitterSize = 4
  // mousedown 时分隔条应在的位置（req 区域像素宽度）
  const startReqSize = (responseRatio.value / 100) * (containerSize - splitterSize)
  // 鼠标在容器内的起始位置
  const startMouse = isBottom ? e.clientY - rect.top : e.clientX - rect.left
  // 鼠标相对分隔条中心的偏移（抓住时不跳变）
  const grabOffset = startMouse - startReqSize

  e.preventDefault()
  let rafId = 0
  let pendingMouse = 0

  function apply(mouseInContainer: number) {
    // 分隔条 = 鼠标位置 - 抓取偏移
    let reqSize = mouseInContainer - grabOffset
    reqSize = Math.min(containerSize - splitterSize - 20, Math.max(20, reqSize))
    const respSize = containerSize - splitterSize - reqSize
    if (isBottom) {
      reqEl.style.height = `${reqSize}px`
      reqEl.style.width = ''
      respEl.style.height = `${respSize}px`
      respEl.style.width = ''
    } else {
      reqEl.style.width = `${reqSize}px`
      reqEl.style.height = ''
      respEl.style.width = `${respSize}px`
      respEl.style.height = ''
    }
  }
  function flush() {
    rafId = 0
    apply(pendingMouse)
  }
  function move(ev: MouseEvent) {
    const newRect = container.getBoundingClientRect()
    pendingMouse = isBottom ? ev.clientY - newRect.top : ev.clientX - newRect.left
    if (!rafId) rafId = requestAnimationFrame(flush)
  }
  function up() {
    if (rafId) cancelAnimationFrame(rafId)
    document.removeEventListener('mousemove', move)
    document.removeEventListener('mouseup', up)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    // 用最终像素换算回百分比
    const finalReq = isBottom ? reqEl.getBoundingClientRect().height : reqEl.getBoundingClientRect().width
    const ratio = Math.min(80, Math.max(20, ((containerSize - splitterSize - finalReq) / (containerSize - splitterSize)) * 100))
    responseRatio.value = ratio
    // 清掉内联 style，回到 Vue 绑定
    reqEl.style.height = ''
    reqEl.style.width = ''
    respEl.style.height = ''
    respEl.style.width = ''
  }
  document.addEventListener('mousemove', move)
  document.addEventListener('mouseup', up)
  document.body.style.cursor = isBottom ? 'row-resize' : 'col-resize'
  document.body.style.userSelect = 'none'
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
  flex: 1;
  min-width: 0;
}

.workbench-tabs {
  flex: 1;
  min-width: 0;

  :deep(.arco-tabs-nav) {
    margin-bottom: 0;
    border-bottom: none;
  }

  :deep(.arco-tabs-header) {
    border-bottom: none;
  }

  :deep(.arco-tabs-tab) {
    max-width: 220px;
    border: none;
    background: transparent;
    border-radius: 6px;
    margin-right: 4px;
    transition: background 0.15s;

    &:hover {
      background: var(--el-fill-color-light);
    }
  }

  :deep(.arco-tabs-tab-active) {
    background: var(--el-fill-color);
    font-weight: 600;
  }

  .tab-method {
    font-size: 10px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
    color: #fff;
    margin-right: 4px;

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
}

.tabs-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;

  .ph-count {
    margin-left: 4px;
    padding: 0 5px;
    font-size: 11px;
    line-height: 16px;
    border-radius: 8px;
    background: rgba(255, 176, 32, 0.22);
    color: #d48806;
  }

  .svg-icon {
    width: 14px;
    height: 14px;
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
