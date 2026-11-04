<template>
  <div class="postman-view">
    <!-- 左侧：Collections + History -->
    <aside class="sidebar" v-show="!sidebarHidden" :style="{ width: sidebarWidth + 'px' }">
      <div class="scope-bar">
        <a-radio-group
          v-model="scopeMode"
          size="mini"
          type="button"
          @change="onScopeChange"
        >
          <a-radio value="personal">我的</a-radio>
          <a-radio v-for="t in teams.myTeams" :key="t.id" :value="String(t.id)" :style="{ maxWidth: '120px' }">
            {{ t.name }}
          </a-radio>
        </a-radio-group>
        <a-button size="mini" type="text" @click="teamDialogOpen = true" title="团队管理">
          <template #icon><icon-team /></template>
        </a-button>
      </div>
      <div class="side-collections">
        <CollectionsTree @open="onOpenNode" />
      </div>
      <div class="side-section" :class="historyOpen ? 'open' : 'closed'">
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
            <span class="method-pill" :class="'m-' + item.method.toLowerCase()">{{ item.method }}</span>
            <span class="u" :title="item.url">{{ item.url }}</span>
            <span class="status-pill" :class="statusClass(item.status_code)">{{ item.status_code || '—' }}</span>
          </div>
          <div v-if="!history.length" class="history-empty">暂无历史</div>
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
            @delete="(k: string | number) => closeMany([String(k)])" @add="onAddTab">
            <a-tab-pane v-for="t in wb.tabs" :key="t.id" :closable="true">
              <template #title>
                <span class="tab-title-wrap" @contextmenu.prevent="onTabContextMenu($event, t)">
                  <span class="method-pill"
                    :class="t.kind === 'websocket' ? 'm-ws' : t.kind === 'mcp' ? 'm-mcp' : 'm-' + t.request.method.toLowerCase()">
                    {{ t.kind === 'websocket' ? 'WS' : t.kind === 'mcp' ? 'MCP' : t.request.method }}
                  </span>
                  <span class="tab-title">{{ t.title }}</span>
                  <span v-if="t.dirty" class="tab-dirty" title="有未保存的修改"></span>
                </span>
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
          <span class="tb-sep"></span>
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
          <span class="tb-sep"></span>
          <a-button size="small" @click="settingsOpen = true">
            <template #icon><icon-settings /></template>
          </a-button>
          <a-dropdown @select="onUserMenu">
            <a-button size="small" class="user-chip">
              <span class="avatar">{{ userInitial }}</span>
              {{ user.user?.display_name || user.user?.username || '未登录' }}
            </a-button>
            <template #content>
              <a-doption value="logout">退出登录</a-doption>
            </template>
          </a-dropdown>
        </div>
      </div>

      <div class="pane custom-arco-design" v-if="dataReady && wb.activeTab" :key="wb.activeTab.id">
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
      <div class="empty" v-else-if="dataReady">
        <div class="ui-empty">
          <div class="ui-empty-icon"><icon-code-square /></div>
          <div class="ui-empty-title">还没有打开的请求</div>
          <div class="ui-empty-desc">从左侧 Collections 选择一个接口，或新建一个空白请求开始调试</div>
          <div class="ui-empty-actions">
            <a-button type="primary" @click="onAddTab">
              <template #icon><icon-plus /></template>
              新建请求
            </a-button>
          </div>
        </div>
      </div>
    </section>

    <SettingsDialog v-model="settingsOpen" />
    <EnvironmentsDialog v-model:visible="envDialogOpen" />
    <CollectionPlaceholdersDialog v-model:visible="phDialogOpen" />
    <SaveRequestDialog v-model:visible="saveDialogOpen" :tab="saveDialogTab" @saved="onRequestSaved" />
    <UserSelectDialog v-if="userDialogOpen" @done="onUserSelected" />
    <TeamDialog v-if="teamDialogOpen" @close="teamDialogOpen = false" @select-team="onTeamSelected" />

    <!-- 标签页右键菜单 -->
    <Teleport to="body">
      <div v-if="ctxMenu.visible" class="ctx-overlay" @click="closeCtxMenu" @contextmenu.prevent="closeCtxMenu" />
      <div v-if="ctxMenu.visible" class="tab-ctx-menu" :style="{ left: ctxMenu.x + 'px', top: ctxMenu.y + 'px' }">
        <div class="ctx-item" @click="onCtxClose">关闭</div>
        <div class="ctx-item" :class="{ disabled: ctxIndex <= 0 }" @click="onCtxCloseLeft">关闭左侧</div>
        <div class="ctx-item" :class="{ disabled: ctxIndex < 0 || ctxIndex >= wb.tabs.length - 1 }"
          @click="onCtxCloseRight">关闭右侧</div>
        <div class="ctx-item" :class="{ disabled: wb.tabs.length <= 1 }" @click="onCtxCloseOthers">关闭其他</div>
        <div class="ctx-item" :class="{ disabled: !wb.tabs.length }" @click="onCtxCloseAll">关闭所有</div>
        <div class="ctx-divider"></div>
        <div class="ctx-item" @click="onCtxClone">克隆请求</div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
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
import UserSelectDialog from '@/components/UserSelectDialog.vue'
import TeamDialog from '@/components/TeamDialog.vue'
import { useCollectionsStore } from '@/stores/collections'
import { useWorkbenchStore } from '@/stores/workbench'
import { useEnvironmentsStore } from '@/stores/environments'
import { useHttpStore } from '@/stores/http'
import { useUserStore } from '@/stores/user'
import { useTeamsStore } from '@/stores/teams'
import { useSettingsStore } from '@/stores/settings'
import { api } from '@/api/client'
import { closeUnsavedDialog, toast } from '@/utils/feedback'
import IconShowLeft from '@/imgs/icon/show_left.svg?component'
import IconHiddenLeft from '@/imgs/icon/hidden_left.svg?component'
import IconRightLeft from '@/imgs/icon/right_left.svg?component'
import IconTopBottom from '@/imgs/icon/top_bottom.svg?component'
import IconTeam from '@/imgs/icon/add_team.svg?component'
import type { CollectionNode, HttpCallRecord, OpenTab } from '@/api/types'

const collections = useCollectionsStore()
const wb = useWorkbenchStore()
const http = useHttpStore()
const env = useEnvironmentsStore()
const user = useUserStore()
const teams = useTeamsStore()
const settingsStore = useSettingsStore()

/** 用户头像首字母（无头像时用）。 */
const userInitial = computed(() => {
  const name = user.user?.display_name || user.user?.username || '未'
  return name.trim().charAt(0).toUpperCase()
})

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
const userDialogOpen = ref(false)
const teamDialogOpen = ref(false)
/** 数据是否已加载（用户已选名后）。 */
const dataReady = ref(false)
/** 左侧空间切换：'personal' 或 team_id 字符串。 */
const scopeMode = ref<string>('personal')
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
  // 未登录先弹登录框；登录成功后再加载数据
  if (user.needsLogin) {
    userDialogOpen.value = true
  } else {
    await loadUserData()
  }
  window.addEventListener('keydown', onGlobalKeydown, true)
})

async function loadUserData() {
  await Promise.all([collections.load(), http.loadHistory(), teams.loadMyTeams()])
  history.value = http.history
  // 集合树加载完后，恢复上次打开的 tabs（nodeId 类型需要从树里重新取节点数据）
  wb.restore()
  dataReady.value = true
}

/** 切换个人/团队空间：清空 tabs，重新加载对应集合。 */
async function onScopeChange(v: string | number | boolean) {
  const val = String(v)
  wb.reset()
  dataReady.value = false
  if (val === 'personal') {
    await collections.loadPersonal()
  } else {
    await collections.loadTeam(Number(val))
  }
  wb.restore()
  dataReady.value = true
}

/** 团队对话框里选中某个团队后切过去。 */
async function onTeamSelected(team: { id: number }) {
  teamDialogOpen.value = false
  scopeMode.value = String(team.id)
  await onScopeChange(scopeMode.value)
}

/** 登录/注册成功后：加载当前用户数据。 */
async function onUserSelected() {
  userDialogOpen.value = false
  wb.reset()
  collections.clear()
  http.clearAll()
  teams.clear()
  scopeMode.value = 'personal'
  dataReady.value = false
  await loadUserData()
}

async function onUserMenu(key: string | number | Record<string, any> | undefined) {
  if (key === 'logout') {
    await user.logout()
    wb.reset()
    collections.clear()
    http.clearAll()
    teams.clear()
    scopeMode.value = 'personal'
    dataReady.value = false
    userDialogOpen.value = true
  }
}

onUnmounted(() => window.removeEventListener('keydown', onGlobalKeydown, true))

function onGlobalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    if (saveDialogOpen.value) return // 保存对话框已打开，避免覆盖等待中的流程
    const tab = wb.activeTab
    if (!tab || tab.kind !== 'http') return
    if (!tab.dirty) return
    void saveTabFlow(tab)
  }
}

const saveDialogTab = ref<OpenTab | null>(null)
let saveResolver: ((v: boolean) => void) | null = null

/** 弹出 Save Request 对话框为指定标签选择保存位置；resolve 是否真的保存了。 */
function openSaveDialogFor(t: OpenTab): Promise<boolean> {
  saveDialogTab.value = t
  saveDialogOpen.value = true
  return new Promise((resolve) => {
    saveResolver = resolve
  })
}

// 对话框被取消（未保存）时放行等待中的 Promise
watch(saveDialogOpen, (v) => {
  if (!v && saveResolver) {
    saveResolver(false)
    saveResolver = null
  }
})

/**
 * 保存标签：已绑定集合的静默写回；未绑定的弹出 Save Request 选择名称与位置。
 * resolve 是否保存成功（用户取消保存对话框时为 false）。
 */
async function saveTabFlow(t: OpenTab): Promise<boolean> {
  if (t.nodeId) {
    const node = collections.findNode(t.nodeId)
    if (node) {
      if (t.kind === 'websocket') node.ws_url = t.ws_url
      else if (t.kind === 'mcp') {
        node.mcp_url = t.mcp_url
        node.mcp_headers = t.mcp_headers
        node.mcp_tool = t.mcp_tool
        node.mcp_args = t.mcp_args
      } else {
        node.request = JSON.parse(JSON.stringify(t.request))
      }
      node.name = t.title
      await collections.persist()
      t.dirty = false
      if (wb.activeTab?.id === t.id && t.kind === 'http') requestSnapshot = JSON.stringify(t.request)
      toast.success('已保存')
      return true
    }
  }
  // 未绑定节点（或节点已被删除）：走保存对话框
  return openSaveDialogFor(t)
}

/** Save Request 对话框保存成功后的回调（对任意标签生效）。 */
function onRequestSaved() {
  const t = saveDialogTab.value
  if (t) {
    t.dirty = false
    if (wb.activeTab?.id === t.id && t.kind === 'http') requestSnapshot = JSON.stringify(t.request)
  }
  saveDialogOpen.value = false
  saveResolver?.(true)
  saveResolver = null
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
  const cont: HTMLElement = container
  const req: HTMLElement = reqEl
  const resp: HTMLElement = respEl
  const isBottom = responseLayout.value === 'bottom'
  const rect = cont.getBoundingClientRect()
  const containerSize = isBottom ? rect.height : rect.width
  const splitterSize = 6
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
      req.style.height = `${reqSize}px`
      req.style.width = ''
      resp.style.height = `${respSize}px`
      resp.style.width = ''
    } else {
      req.style.width = `${reqSize}px`
      req.style.height = ''
      resp.style.width = `${respSize}px`
      resp.style.height = ''
    }
  }
  function flush() {
    rafId = 0
    apply(pendingMouse)
  }
  function move(ev: MouseEvent) {
    const newRect = cont.getBoundingClientRect()
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
    const finalReq = isBottom ? req.getBoundingClientRect().height : req.getBoundingClientRect().width
    const ratio = Math.min(80, Math.max(20, ((containerSize - splitterSize - finalReq) / (containerSize - splitterSize)) * 100))
    responseRatio.value = ratio
    // 清掉内联 style，回到 Vue 绑定
    req.style.height = ''
    req.style.width = ''
    resp.style.height = ''
    resp.style.width = ''
  }
  document.addEventListener('mousemove', move)
  document.addEventListener('mouseup', up)
  document.body.style.cursor = isBottom ? 'row-resize' : 'col-resize'
  document.body.style.userSelect = 'none'
}

async function onOpenNode(node: CollectionNode) {
  // 已打开的请求只激活，不占新标签名额
  if (node.type === 'request' && !wb.tabs.some((t) => t.nodeId === node.id)) {
    if (!(await ensureRoom())) return
  }
  wb.openFromNode(node)
}

/** 点击「+」新建标签。 */
async function onAddTab() {
  if (!(await ensureRoom())) return
  wb.openBlank('http')
}

/**
 * 打开新标签前确保未达上限；超限时自动关闭最早的标签，
 * 若最早的标签有未保存修改则先弹框询问，取消则放弃打开。
 */
async function ensureRoom(): Promise<boolean> {
  const max = Math.max(settingsStore.maxTabsMin, settingsStore.settings.maxTabs)
  while (wb.tabs.length >= max) {
    const victim = wb.tabs[0]
    if (!victim) break
    if (victim.streaming) {
      toast.warning('已达到Tab数量，最早的标签正在发送请求，请稍后再试')
      return false
    }
    if (victim.dirty) {
      const choice = await closeUnsavedDialog(victim.title)
      if (choice === null) {
        toast.warning('已达到Tab数量，请先手动关闭部分标签页')
        return false
      }
      if (choice === 'save') {
        const saved = await saveTabFlow(victim)
        if (!saved) return false // 保存被取消，放弃打开新标签
      }
    }
    wb.closeTab(victim.id)
  }
  return true
}

/** 批量关闭标签：含未保存修改的逐个弹框询问；中途取消则中止剩余关闭。 */
async function closeMany(ids: string[]) {
  for (const id of ids) {
    const t = wb.tabs.find((x) => x.id === id)
    if (!t) continue
    if (t.dirty) {
      const choice = await closeUnsavedDialog(t.title)
      if (choice === null) return // 用户取消，中止本次批量关闭
      if (choice === 'save') {
        const saved = await saveTabFlow(t)
        if (!saved) continue // 保存位置对话框被取消 → 保留该标签，继续处理其余
      }
    }
    wb.closeTab(id)
  }
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

async function onLoadHistory(item: HttpCallRecord) {
  if (!(await ensureRoom())) return
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

// ── 标签页右键菜单 ──────────────────────────────────────────────
const ctxMenu = reactive({ visible: false, x: 0, y: 0, tabId: '' })
/** 右键目标标签当前的下标（-1 表示已不存在）。 */
const ctxIndex = computed(() => wb.tabs.findIndex((t) => t.id === ctxMenu.tabId))

function onTabContextMenu(e: MouseEvent, t: OpenTab) {
  ctxMenu.tabId = t.id
  // 避免菜单溢出视口
  ctxMenu.x = Math.min(e.clientX, window.innerWidth - 150)
  ctxMenu.y = Math.min(e.clientY, window.innerHeight - 230)
  ctxMenu.visible = true
}

function closeCtxMenu() {
  ctxMenu.visible = false
}

function onCtxClose() {
  closeCtxMenu()
  void closeMany([ctxMenu.tabId])
}

function onCtxCloseLeft() {
  const i = ctxIndex.value
  closeCtxMenu()
  if (i > 0) void closeMany(wb.tabs.slice(0, i).map((t) => t.id))
}

function onCtxCloseRight() {
  const i = ctxIndex.value
  closeCtxMenu()
  if (i >= 0 && i < wb.tabs.length - 1) void closeMany(wb.tabs.slice(i + 1).map((t) => t.id))
}

function onCtxCloseOthers() {
  const i = ctxIndex.value
  closeCtxMenu()
  if (i >= 0 && wb.tabs.length > 1) {
    void closeMany(wb.tabs.filter((_, idx) => idx !== i).map((t) => t.id))
  }
}

function onCtxCloseAll() {
  closeCtxMenu()
  void closeMany(wb.tabs.map((t) => t.id))
}

async function onCtxClone() {
  closeCtxMenu()
  const t = wb.tabs.find((x) => x.id === ctxMenu.tabId)
  if (!t) return
  if (!(await ensureRoom())) return
  wb.cloneTab(t.id)
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
  gap: 6px;
  height: 100%;
  padding: 6px;
  background: var(--ui-bg-canvas);
  color: var(--color-text-1);
  font-family: var(--app-font-family);
  font-size: var(--app-font-size);
}

.sidebar {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: var(--ui-bg-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
}

.scope-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding: 8px;
  border-bottom: 1px solid var(--ui-border-soft);

  :deep(.arco-radio-group) {
    flex: 1;
    min-width: 0;
    overflow-x: auto;
  }

  :deep(.arco-radio-button) {
    font-size: 12px;
  }
}

.side-collections {
  flex: 1 1 55%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.side-section {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-top: 1px solid var(--ui-border-soft);

  &.open {
    flex: 1 1 45%;
  }

  &.closed {
    flex: 0 0 auto;
  }
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  height: 32px;
  padding: 0 6px 0 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-2);
  cursor: pointer;
  user-select: none;
  transition: background-color 0.15s ease;

  &:hover {
    background: var(--ui-bg-hover);
  }

  > span {
    flex: 1;
  }

  :deep(.arco-btn) {
    opacity: 0;
    flex-shrink: 0;
  }

  &:hover :deep(.arco-btn) {
    opacity: 1;
  }
}

.history-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 2px 6px 8px;
}

.history-empty {
  padding: 14px 10px;
  font-size: 12px;
  color: var(--color-text-3);
  text-align: center;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 6px;
  border-radius: var(--ui-radius-sm);
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.12s ease;

  &:hover {
    background: var(--ui-bg-hover);
  }

  .u {
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--color-text-2);
  }
}

.workbench {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  min-height: 0;
}

.tab-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-shrink: 0;
  height: 44px;
  padding: 0 8px;
  background: var(--ui-bg-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
}

.tabs-left {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.workbench-tabs {
  flex: 1;
  min-width: 0;

  :deep(.arco-tabs-nav) {
    margin: 0;
    border: none;
  }

  :deep(.arco-tabs-nav::before) {
    display: none;
  }

  :deep(.arco-tabs-header) {
    border-bottom: none;
  }

  :deep(.arco-tabs-tab) {
    max-width: 200px;
    height: 30px;
    margin: 0 4px 0 0;
    padding: 0 10px;
    border: none;
    border-radius: var(--ui-radius-md);
    background: transparent;
    color: var(--color-text-2);
    font-size: 12.5px;
    transition: background-color 0.15s ease, color 0.15s ease;

    &:hover {
      background: var(--ui-bg-hover);
      color: var(--color-text-1);
    }
  }

  :deep(.arco-tabs-tab-active) {
    background: var(--ui-bg-active);
    color: rgb(var(--primary-6));
    font-weight: 600;
    box-shadow: inset 3px 0 0 rgb(var(--primary-6));
  }

  :deep(.arco-tabs-close-icon) {
    color: var(--color-text-3);
  }

  // 新增标签页 + 按钮
  :deep(.arco-tabs-add) {
    height: 26px;
    width: 26px;
    margin-left: 2px;
    border-radius: var(--ui-radius-md);
    color: var(--color-text-3);

    &:hover {
      background: var(--ui-bg-hover);
      color: var(--color-text-1);
    }
  }

  .tab-title-wrap {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
  }

  .tab-title {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tab-dirty {
    flex-shrink: 0;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgb(var(--primary-6));
  }
}

.tabs-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;

  :deep(.arco-btn) {
    height: 28px;
    padding: 0 8px;
    border-radius: var(--ui-radius-md);
    background: var(--ui-bg-subtle);
    border: 1px solid var(--ui-border-soft);
    color: var(--color-text-2);
    font-size: 12px;

    &:hover {
      background: var(--ui-bg-hover);
      border-color: var(--ui-border);
      color: var(--color-text-1);
    }
  }

  :deep(.arco-btn-icon-only) {
    width: 28px;
    padding: 0;
  }

  .tb-sep {
    flex-shrink: 0;
    width: 1px;
    height: 16px;
    background: var(--ui-border);
  }

  .ph-count {
    margin-left: 4px;
    padding: 0 5px;
    font-size: 10px;
    line-height: 15px;
    border-radius: 8px;
    background: rgba(var(--primary-6), 0.16);
    color: rgb(var(--primary-6));
  }

  .svg-icon {
    width: 14px;
    height: 14px;
  }

  .user-chip .avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    margin-right: 4px;
    border-radius: 50%;
    background: rgb(var(--primary-6));
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    line-height: 1;
  }
}

.pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
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
  overflow: hidden;
  background: var(--ui-bg-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
}

.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ui-bg-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
}

/* 拖拽条 */
.splitter {
  flex-shrink: 0;
  z-index: 5;
  position: relative;
}

.splitter::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  border-radius: 1px;
  background: var(--ui-border-strong);
  opacity: 0;
  transition: opacity 0.15s ease, width 0.15s ease, height 0.15s ease, background-color 0.15s ease;
}

.v-splitter {
  width: 6px;
  cursor: col-resize;

  &::after {
    width: 2px;
    height: 28px;
  }

  &:hover::after {
    opacity: 1;
    height: 44px;
    background: rgb(var(--primary-6));
  }
}

.h-splitter {
  height: 6px;
  cursor: row-resize;

  &::after {
    width: 28px;
    height: 2px;
  }

  &:hover::after {
    opacity: 1;
    width: 44px;
    background: rgb(var(--primary-6));
  }
}

/* 标签页右键菜单 */
.ctx-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
}

.tab-ctx-menu {
  position: fixed;
  z-index: 1001;
  min-width: 140px;
  padding: 4px;
  background: var(--ui-bg-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  box-shadow: var(--ui-shadow-pop);

  .ctx-item {
    padding: 6px 12px;
    font-size: 12.5px;
    color: var(--color-text-1);
    border-radius: var(--ui-radius-sm);
    cursor: pointer;
    white-space: nowrap;
    user-select: none;

    &:hover {
      background: var(--ui-bg-hover);
    }

    &.disabled {
      color: var(--color-text-4);
      cursor: not-allowed;

      &:hover {
        background: transparent;
      }
    }
  }

  .ctx-divider {
    height: 1px;
    margin: 4px 6px;
    background: var(--ui-border-soft);
  }
}
</style>
