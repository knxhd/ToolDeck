<template>
  <div class="mcp-pane">
    <!-- 顶部请求条：与 HTTP 请求条同一套尺寸与配色 -->
    <div class="mcp-bar">
      <div class="url-group">
        <span class="kind-badge">MCP</span>
        <span class="url-divider"></span>
        <a-input :border="false" v-model="tab.mcp_url" class="url-input" allow-clear
          placeholder="输入 MCP 地址，如 http://127.0.0.1:8001/mcp" @press-enter="onConnect" />
      </div>
      <a-button class="bar-btn" html-type="button" :loading="connecting" @click="onConnect">
        {{ connected ? '重新连接' : '连接' }}
      </a-button>
      <a-tooltip content="保存到集合（无节点时选择位置）" position="top">
        <button type="button" class="save-btn" aria-label="保存" @click="emit('saveClick')">
          <svg class="ico-save" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M8.7 1.9H4.6c-.7 0-1.2.5-1.2 1.2v9.8c0 .7.5 1.2 1.2 1.2h6.8c.7 0 1.2-.5 1.2-1.2V5.9L8.7 1.9Z" />
            <path d="M8.5 2v3.6h3.7" />
            <path d="M8 8v3.3" />
            <path d="M6.7 10.1 8 11.4l1.3-1.3" />
          </svg>
        </button>
      </a-tooltip>
      <a-button type="primary" class="run-btn" :loading="tab.mcp_loading" :disabled="!selectedTool"
        @click="onRun">
        <template #icon><icon-play-arrow /></template>
        Run
      </a-button>
    </div>

    <!-- 正文卡片：标签栏 + 三栏，与 HTTP 的请求/响应卡片同构 -->
    <div class="mcp-card">
      <div class="pane-tabs">
        <span class="pane-tab" :class="{ active: subTab === 'message' }" @click="subTab = 'message'">Message</span>
        <span class="pane-tab" :class="{ active: subTab === 'headers' }" @click="subTab = 'headers'">Headers</span>
      </div>

      <div ref="bodyRef" class="mcp-body">
        <!-- Headers 面板 -->
        <div v-if="subTab === 'headers'" class="headers-pane">
          <div class="hint">自定义连接 MCP Server 时携带的请求头（如 Authorization）</div>
          <KeyValueEditor v-model="headerRows" />
        </div>

        <!-- Message 面板：三栏 -->
        <template v-else>
          <div class="col col-tools" :style="{ width: toolsW + 'px' }">
            <div class="col-head">
              <span class="sub-tabs">
                <span class="pane-tab active">Tools</span>
                <span class="pane-tab disabled">Prompts</span>
                <span class="pane-tab disabled">Resources</span>
              </span>
              <span class="col-head-extra">
                <a-input v-model="keyword" class="search-input" size="small" placeholder="搜索" />
                <a-button class="icon-btn" html-type="button" aria-label="刷新工具列表" @click="onConnect">
                  <template #icon><icon-refresh /></template>
                </a-button>
              </span>
            </div>
            <div class="tool-list">
              <div v-for="(t, i) in filteredTools" :key="t.name" class="tool-row">
                <div class="tool-item" :class="{ selected: selectedTool?.name === t.name }"
                  @click="selectTool(t, $event)">
                  <div class="tool-title"><span class="idx">{{ i + 1 }}.</span>{{ t.name }}</div>
                  <div class="tool-desc" v-if="t.description">{{ t.description }}</div>
                </div>

                <!-- 参数内联在所选工具下方，不脱离列表上下文 -->
                <div v-if="selectedTool?.name === t.name" class="tool-args">
                  <div class="args-title">
                    <span>参数</span>
                    <span class="args-count">{{ fields.length ? `${fields.length} 项` : '无参数' }}</span>
                  </div>
                  <div v-for="f in fields" :key="f.key" class="field">
                    <div class="field-label">
                      <span class="field-name">{{ f.key }}</span>
                      <span class="req" v-if="f.required" title="必填">*</span>
                      <span class="field-type">{{ f.type }}</span>
                    </div>
                    <div class="field-desc" v-if="f.description">{{ f.description }}</div>
                    <a-switch v-if="f.type === 'boolean'" size="small"
                      :model-value="boolVal(formValues[f.key])"
                      @change="(v) => (formValues[f.key] = !!v)" />
                    <a-input-number v-else-if="f.type === 'number' || f.type === 'integer'" size="small"
                      :model-value="numVal(formValues[f.key])"
                      @change="(v?: number) => (formValues[f.key] = v ?? 0)" style="width: 100%" />
                    <a-textarea v-else-if="f.type === 'array' || f.type === 'object' || f.longText" size="small"
                      :model-value="strVal(formValues[f.key])"
                      @input="(v: string) => (formValues[f.key] = v)"
                      :auto-size="{ minRows: 2, maxRows: 6 }" />
                    <a-input v-else size="small" :model-value="strVal(formValues[f.key])"
                      @input="(v: string) => (formValues[f.key] = v)" />
                  </div>
                </div>
              </div>
              <a-empty v-if="!filteredTools.length" :description="connected ? '无工具' : '请先连接'"
                style="padding: 16px 0" />
            </div>
          </div>

          <!-- 拖拽分隔条：调整工具列 / Message 列宽度 -->
          <div class="col-splitter" role="separator" aria-orientation="vertical"
            @mousedown="startResize('tools', $event)" />

          <div class="col col-req" :style="{ width: reqW + 'px' }">
            <div class="col-head">Message</div>
            <div class="col-body">
              <MonacoEditor :model-value="requestPreview" language="json" read-only height="100%" />
            </div>
          </div>

          <div class="col-splitter" role="separator" aria-orientation="vertical"
            @mousedown="startResize('req', $event)" />

          <div class="col col-resp">
            <div class="col-head">
              <span>Response</span>
              <span v-if="connected" class="state-pill">Connected</span>
            </div>
            <div v-if="tab.mcp_result" class="col-body">
              <MonacoEditor :model-value="tab.mcp_result" language="json" read-only height="100%" auto-scroll-to-end />
            </div>
            <div v-else class="resp-empty">运行后在此查看结果</div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import KeyValueEditor from '@/components/KeyValueEditor.vue'
import { useMcpStore, type McpTool } from '@/stores/mcp'
import { toast } from '@/utils/feedback'
import type { KeyValue, OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()
const emit = defineEmits<{ save: []; saveClick: [] }>()

const mcp = useMcpStore()
const connecting = ref(false)
const connected = ref(false)
const keyword = ref('')
const subTab = ref<'message' | 'headers'>('message')
const selectedTool = ref<McpTool | null>(null)
const formValues = ref<Record<string, unknown>>({})

// headers: Record <-> KeyValue[]
const headerRows = ref<KeyValue[]>(
  Object.entries(props.tab.mcp_headers || {}).map(([key, value]) => ({ key, value, enabled: true })),
)

// 三栏宽度：可拖拽，记忆到标签上
const toolsW = ref(props.tab.mcp_tools_w || 336)
const reqW = ref(props.tab.mcp_req_w || 360)
const bodyRef = ref<HTMLElement>()
let drag: { kind: 'tools' | 'req'; x: number; w: number } | null = null

const clamp = (v: number, min: number, max: number) => Math.min(Math.max(v, min), max)

function startResize(kind: 'tools' | 'req', e: MouseEvent) {
  drag = { kind, x: e.clientX, w: kind === 'tools' ? toolsW.value : reqW.value }
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', stopResize)
  e.preventDefault()
}

function onResizeMove(e: MouseEvent) {
  if (!drag) return
  const total = bodyRef.value?.clientWidth ?? 1200
  const other = drag.kind === 'tools' ? reqW.value : toolsW.value
  // 至少给右侧响应栏留 240px
  const maxSelf = Math.max(240, total - other - 240)
  const delta = e.clientX - drag.x
  if (drag.kind === 'tools') {
    toolsW.value = clamp(drag.w + delta, 220, Math.min(600, maxSelf))
  } else {
    reqW.value = clamp(drag.w + delta, 240, Math.min(800, maxSelf))
  }
}

function stopResize() {
  if (!drag) return
  drag = null
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('mousemove', onResizeMove)
  window.removeEventListener('mouseup', stopResize)
  props.tab.mcp_tools_w = toolsW.value
  props.tab.mcp_req_w = reqW.value
}

// 保存调度：编辑时防抖写入集合节点，切换标签 / 点选工具 / 运行时立即落盘
let saveTimer: number | undefined
let savePending = false

function scheduleSave() {
  savePending = true
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    savePending = false
    emit('save')
  }, 400)
}

function flushSave() {
  window.clearTimeout(saveTimer)
  savePending = false
  emit('save')
}

watch(() => props.tab.mcp_url, scheduleSave)

// 请求头变动同样走防抖落盘
watch(headerRows, (rows) => {
  const out: Record<string, string> = {}
  for (const r of rows) if (r.enabled && r.key) out[r.key] = r.value
  props.tab.mcp_headers = out
  scheduleSave()
}, { deep: true })

onBeforeUnmount(() => {
  // 防抖窗口内切换标签也要落盘，否则刚改的内容会丢
  if (savePending) flushSave()
  window.clearTimeout(saveTimer)
  window.removeEventListener('mousemove', onResizeMove)
  window.removeEventListener('mouseup', stopResize)
})

onMounted(() => {
  if (props.tab.mcp_url) onConnect()
})

const filteredTools = computed(() =>
  mcp.tools.filter((t) => !keyword.value || t.name.toLowerCase().includes(keyword.value.toLowerCase())),
)

const strVal = (v: unknown): string => (typeof v === 'string' ? v : String(v ?? ''))
const numVal = (v: unknown): number | undefined => (typeof v === 'number' ? v : Number(v) || 0)
const boolVal = (v: unknown): boolean => !!v

interface FieldDef {
  key: string
  type: string
  description: string
  required: boolean
  longText: boolean
}

const fields = computed<FieldDef[]>(() => {
  if (!selectedTool.value) return []
  const schema: { properties?: Record<string, { type?: string; description?: string }>; required?: string[] } =
    selectedTool.value.input_schema || {}
  const props_ = schema.properties || {}
  const required: string[] = schema.required || []
  return Object.entries(props_).map(([key, def]) => ({
    key,
    type: def.type || 'string',
    description: def.description || '',
    required: required.includes(key),
    longText: (def.description || '').length > 40,
  }))
})

async function onConnect() {
  if (!props.tab.mcp_url) {
    toast.warning('请输入 MCP 地址')
    return
  }
  connecting.value = true
  try {
    mcp.tools = await mcp.adHocTools(props.tab.mcp_url, props.tab.mcp_headers || {})
    connected.value = true
    flushSave()
  } catch (e) {
    toast.error((e as Error).message)
  } finally {
    connecting.value = false
  }
}

function selectTool(t: McpTool, ev?: MouseEvent) {
  selectedTool.value = t
  props.tab.mcp_tool = t.name
  try {
    formValues.value = { ...JSON.parse(props.tab.mcp_args || '{}') }
  } catch {
    formValues.value = {}
  }
  for (const f of fields.value) {
    if (!(f.key in formValues.value)) {
      formValues.value[f.key] = f.type === 'boolean' ? false : f.type === 'number' || f.type === 'integer' ? 0 : ''
    }
  }
  props.tab.mcp_args = JSON.stringify(buildArgs())
  flushSave()
  // 展开后把参数区带入可视范围（工具多时也不会被挤出列表）
  nextTick(() => {
    const row = (ev?.currentTarget as HTMLElement | null)?.parentElement
    row?.querySelector('.tool-args')?.scrollIntoView({ block: 'nearest' })
  })
}

function buildArgs(): Record<string, unknown> {
  const args: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(formValues.value)) {
    if (v === '' || v === undefined) continue
    args[k] = v
  }
  return args
}

const requestPreview = computed(() => {
  if (!selectedTool.value) return ''
  return JSON.stringify(
    { method: 'tools/call', params: { name: selectedTool.value.name, arguments: buildArgs() } },
    null,
    2,
  )
})

async function onRun() {
  if (!selectedTool.value) return
  props.tab.mcp_args = JSON.stringify(buildArgs())
  props.tab.mcp_loading = true
  try {
    const res = await mcp.adHocCall(props.tab.mcp_url, props.tab.mcp_headers || {}, selectedTool.value.name, buildArgs())
    mcp.lastResult = res
    props.tab.mcp_result = JSON.stringify(res, null, 2)
    flushSave()
  } catch (e) {
    toast.error((e as Error).message)
  } finally {
    props.tab.mcp_loading = false
  }
}

// 参数填写：先把值回写到标签（刷新后能恢复），再并入防抖保存
watch(formValues, () => {
  props.tab.mcp_args = JSON.stringify(buildArgs())
  scheduleSave()
}, { deep: true })
</script>

<style lang="less" scoped>
.mcp-pane {
  display: flex;
  flex-direction: column;
  gap: 6px;
  height: 100%;
  min-height: 0;
}

/* 顶部请求条：尺寸与 RequestBar 一致 */
.mcp-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  height: 48px;
  padding: 0 10px;
  background: var(--ui-bg-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
}

/* 输入组：徽标 + 地址共用一层边框，聚焦时整组高亮 */
.url-group {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  height: 32px;
  padding-right: 2px;
  background: var(--ui-bg-subtle);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;

  &:focus-within {
    background: var(--ui-bg-panel);
    border-color: rgb(var(--primary-6));
    box-shadow: 0 0 0 3px rgba(var(--primary-6), 0.12);
  }
}

.kind-badge {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  height: 100%;
  padding: 0 10px;
  border-radius: var(--ui-radius-sm);
  color: var(--ui-method-mcp);
  font-family: var(--ui-font-mono);
  font-size: 0.86em;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.url-divider {
  flex-shrink: 0;
  width: 1px;
  height: 16px;
  margin-right: 2px;
  background: var(--ui-border);
}

.url-input {
  flex: 1;
  min-width: 0;
  height: 100%;

  :deep(.arco-input-wrapper) {
    height: 100%;
    padding: 0 8px 0 4px;
    background: transparent;
  }

  :deep(.arco-input) {
    font-family: var(--ui-font-mono);
    font-size: 12px;
  }
}

/* 次要操作：描边按钮，不与主操作争主色 */
.bar-btn.arco-btn,
.bar-btn.arco-btn:not(.arco-btn-disabled):hover {
  flex-shrink: 0;
  height: 32px;
  padding: 0 14px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: transparent;
  color: var(--color-text-2);
  font-size: 0.93em;
  font-weight: 500;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.bar-btn.arco-btn:not(.arco-btn-disabled):hover {
  background: var(--ui-bg-hover);
  border-color: var(--ui-border-strong);
  color: var(--color-text-1);
}

/* 保存按钮：与 URL 输入组同高 */
.save-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: transparent;
  color: var(--color-text-3);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;

  &:hover {
    background: var(--ui-bg-hover);
    border-color: var(--ui-border-strong);
    color: var(--color-text-1);
  }

  &:active {
    transform: translateY(0.5px);
  }

  .ico-save {
    display: block;
    width: 15px;
    height: 15px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.4;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
}

.run-btn.arco-btn {
  flex-shrink: 0;
  min-width: 84px;
  height: 32px;
  border-radius: var(--ui-radius-md);
  font-weight: 600;
}

.mcp-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--ui-bg-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
  overflow: hidden;
}

/* 标签栏：与 HTTP 的 tabs 同一套数值（38px 栏、26px 胶囊） */
.pane-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  height: 38px;
  padding: 0 12px;
  border-bottom: 1px solid var(--ui-border-soft);
}

.pane-tab {
  display: inline-flex;
  align-items: center;
  height: 26px;
  padding: 0 10px;
  flex-shrink: 0;
  border-radius: var(--ui-radius-sm);
  color: var(--color-text-3);
  font-size: 0.89em;
  cursor: pointer;
  transition: color 0.15s ease, background-color 0.15s ease;

  &:hover {
    color: var(--color-text-1);
    background: var(--ui-bg-hover);
  }

  &.active {
    background: var(--ui-bg-active);
    color: rgb(var(--primary-6));
    font-weight: 600;
  }

  &.disabled {
    color: var(--color-text-4);
    cursor: not-allowed;

    &:hover {
      background: transparent;
      color: var(--color-text-4);
    }
  }
}

.mcp-body {
  flex: 1;
  display: flex;
  min-height: 0;
}

.col {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}

/* 拖拽分隔条：常态细线，hover / 拖拽时显主色竖条 */
.col-splitter {
  position: relative;
  flex-shrink: 0;
  width: 6px;
  cursor: col-resize;
  outline: none;

  &::before {
    content: '';
    position: absolute;
    left: 50%;
    top: 0;
    bottom: 0;
    width: 1px;
    transform: translateX(-50%);
    background: var(--ui-border-soft);
  }

  &::after {
    content: '';
    position: absolute;
    left: 50%;
    top: 50%;
    width: 2px;
    height: 28px;
    transform: translate(-50%, -50%);
    border-radius: 1px;
    background: var(--ui-border-strong);
    opacity: 0;
    transition: opacity 0.15s ease, height 0.15s ease, background-color 0.15s ease;
  }

  &:hover::after {
    opacity: 1;
    height: 44px;
    background: rgb(var(--primary-6));
  }
}

.headers-pane {
  flex: 1;
  overflow: auto;
  padding: 12px;
}

.hint {
  margin-bottom: 12px;
  padding: 8px 10px;
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);
  color: var(--color-text-3);
  font-size: 0.86em;
  line-height: 1.7;
}

.col-tools {
  flex-shrink: 0;
}

.col-req {
  flex-shrink: 0;
}

.col-resp {
  flex: 1;
}

/* 列头：白底 + 细分隔线，与 HTTP 卡片头部一致 */
.col-head {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  height: 38px;
  padding: 0 10px;
  border-bottom: 1px solid var(--ui-border-soft);
  background: var(--ui-bg-panel);
  color: var(--color-text-2);
  font-size: 0.89em;
  font-weight: 600;
}

.sub-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  overflow: hidden;

  .pane-tab {
    padding: 0 8px;
  }
}

.col-head-extra {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  flex-shrink: 0;
}

.search-input {
  width: 64px;

  :deep(.arco-input-wrapper) {
    height: 26px;
    border-radius: var(--ui-radius-sm);
  }

  :deep(.arco-input) {
    font-size: 0.86em;
  }
}

.icon-btn.arco-btn,
.icon-btn.arco-btn:not(.arco-btn-disabled):hover {
  width: 24px;
  height: 24px;
  min-width: 24px;
  padding: 0;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-sm);
  background: transparent;
  color: var(--color-text-3);
}

.icon-btn.arco-btn:not(.arco-btn-disabled):hover {
  background: var(--ui-bg-hover);
  border-color: var(--ui-border-strong);
  color: var(--color-text-1);
}

.state-pill {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 7px;
  border-radius: 9px;
  background: var(--ui-status-2xx-bg);
  color: var(--ui-status-2xx);
  font-family: var(--ui-font-mono);
  font-size: 0.71em;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.col-body {
  flex: 1;
  min-height: 0;
  padding: 10px;
}

.tool-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 8px;
}

.tool-item {
  margin-bottom: 2px;
  padding: 6px 16px;
  border-radius: var(--ui-radius-sm);
  cursor: pointer;
  background: transparent;
  transition: background-color 0.12s ease, box-shadow 0.12s ease;

  &:hover {
    background: var(--ui-bg-hover);
  }

  &.selected {
    background: var(--ui-bg-active);
    box-shadow: inset 3px 0 0 rgb(var(--primary-6));
  }

  .tool-title {
    color: var(--color-text-1);
    font-family: var(--ui-font-mono);
    font-size: 0.86em;
    font-weight: 600;
  }

  .tool-desc {
    margin-top: 2px;
    color: var(--color-text-4);
    font-size: 0.86em;
    white-space: pre-wrap;
  }
}

/* 参数区：紧贴所选工具展开的白色详情卡 */
.tool-args {
  margin: 4px 4px 6px;
  padding: 10px 10px 12px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-panel);
  animation: args-in 0.16s ease;

  .args-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 9px;
    padding-bottom: 7px;
    border-bottom: 1px solid var(--ui-border-soft);
    color: var(--color-text-2);
    font-size: 0.86em;
    font-weight: 600;
  }

  .args-count {
    color: var(--color-text-4);
    font-family: var(--ui-font-mono);
    font-size: 0.86em;
    font-weight: 400;
  }

  .field {
    margin-bottom: 10px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  .field-label {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--color-text-1);
    font-size: 0.86em;
    font-weight: 600;

    .field-name {
      font-family: var(--ui-font-mono);
    }

    .req {
      margin-left: -1px;
      color: var(--ui-accent-danger);
      font-weight: 700;
    }
  }

  /* 类型做成小徽标，避免与参数名糊在一起 */
  .field-type {
    margin-left: 2px;
    height: 16px;
    padding: 0 5px;
    border-radius: 8px;
    background: var(--ui-bg-subtle);
    color: var(--color-text-4);
    font-family: var(--ui-font-mono);
    font-size: 0.71em;
    font-weight: 500;
    line-height: 16px;
  }

  .field-desc {
    margin: 3px 0 5px;
    color: var(--color-text-4);
    font-size: 0.79em;
    line-height: 1.5;
  }

  /* 控件统一 28px 高，与左栏密度一致 */
  :deep(.arco-input-wrapper),
  :deep(.arco-input-number),
  :deep(.arco-select-view) {
    height: 28px;
    font-size: 12px;
  }

  :deep(.arco-input-number) {
    width: 100%;
  }

  :deep(.arco-textarea) {
    font-size: 12px;
    line-height: 1.6;
  }
}

@keyframes args-in {
  from {
    opacity: 0;
    transform: translateY(-2px);
  }

  to {
    opacity: 1;
    transform: none;
  }
}

.resp-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-4);
  font-size: 0.89em;
}
</style>
