<template>
  <div class="mcp-pane">
    <!-- 顶部：URL 输入 + 连接 + Run -->
    <div class="mcp-top">
      <a-input v-model="tab.mcp_url" placeholder="输入 MCP 地址，如 http://127.0.0.1:8001/mcp" allow-clear style="flex: 1" @press-enter="onConnect" />
      <a-button :loading="connecting" type="primary" @click="onConnect">
        {{ connected ? '重新连接' : '连接' }}
      </a-button>
      <div class="spacer"></div>
      <a-button status="success" :loading="tab.mcp_loading" :disabled="!selectedTool" @click="onRun">
        <template #icon><icon-play-arrow /></template>
        Run
      </a-button>
    </div>

    <!-- Message / Headers -->
    <div class="mct-tabs">
      <span class="mct-tab" :class="{ active: subTab === 'message' }" @click="subTab = 'message'">Message</span>
      <span class="mct-tab" :class="{ active: subTab === 'headers' }" @click="subTab = 'headers'">Headers</span>
    </div>

    <div class="mcp-body">
      <!-- Headers 面板 -->
      <div v-if="subTab === 'headers'" class="headers-pane">
        <div class="hint">自定义连接 MCP Server 时携带的请求头（如 Authorization）</div>
        <KeyValueEditor v-model="headerRows" />
      </div>

      <!-- Message 面板：三栏 -->
      <template v-else>
        <div class="col col-tools">
          <div class="sub-tabs">
            <span class="sub-tab active">Tools</span>
            <span class="sub-tab disabled">Prompts</span>
            <span class="sub-tab disabled">Resources</span>
            <a-input v-model="keyword" size="small" placeholder="搜索" style="margin-left: auto; width: 120px">
              <template #prefix><icon-search /></template>
            </a-input>
            <a-button size="small" shape="circle" @click="onConnect">
              <template #icon><icon-refresh /></template>
            </a-button>
          </div>
          <div class="tool-list">
            <div
              v-for="(t, i) in filteredTools"
              :key="t.name"
              class="tool-item"
              :class="{ selected: selectedTool?.name === t.name }"
              @click="selectTool(t)"
            >
              <div class="tool-title"><span class="idx">{{ i + 1 }}.</span>{{ t.name }}</div>
              <div class="tool-desc" v-if="t.description">{{ t.description }}</div>
            </div>
            <a-empty v-if="!filteredTools.length" :description="connected ? '无工具' : '请先连接'" style="padding: 16px 0" />
          </div>
          <div v-if="selectedTool" class="param-form">
            <div v-for="f in fields" :key="f.key" class="field">
              <div class="field-label">
                {{ f.key }}<span class="req" v-if="f.required">*</span>
                <span class="field-type">{{ f.type }}</span>
              </div>
              <div class="field-desc" v-if="f.description">{{ f.description }}</div>
              <a-switch :model-value="boolVal(formValues[f.key])" @change="(v) => (formValues[f.key] = !!v)" />
              <a-input-number :model-value="numVal(formValues[f.key])" @change="(v?: number) => (formValues[f.key] = v ?? 0)" style="width: 100%" />
              <a-textarea :model-value="strVal(formValues[f.key])" @change="(v: string) => (formValues[f.key] = v)" :auto-size="{ minRows: 3 }" />
              <a-input :model-value="strVal(formValues[f.key])" @change="(v: string) => (formValues[f.key] = v)" />
            </div>
          </div>
        </div>

        <div class="col col-req">
          <div class="col-head">Message</div>
          <MonacoEditor :model-value="requestPreview" language="json" read-only height="100%" />
        </div>

        <div class="col col-resp">
          <div class="col-head resp-head">
            <span>Response</span>
            <a-tag v-if="connected" color="green" size="small">Connected</a-tag>
          </div>
          <div v-if="tab.mcp_result" class="resp-body">
            <MonacoEditor :model-value="tab.mcp_result" language="json" read-only height="100%" auto-scroll-to-end />
          </div>
          <div v-else class="resp-empty">运行后在此查看结果</div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import KeyValueEditor from '@/components/KeyValueEditor.vue'
import { useMcpStore, type McpTool } from '@/stores/mcp'
import { toast } from '@/utils/feedback'
import type { KeyValue, OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()
const emit = defineEmits<{ save: [] }>()

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
watch(headerRows, (rows) => {
  const out: Record<string, string> = {}
  for (const r of rows) if (r.enabled && r.key) out[r.key] = r.value
  props.tab.mcp_headers = out
  emit('save')
}, { deep: true })

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
    emit('save')
  } catch (e) {
    toast.error((e as Error).message)
  } finally {
    connecting.value = false
  }
}

function selectTool(t: McpTool) {
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
  emit('save')
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
    emit('save')
  } catch (e) {
    toast.error((e as Error).message)
  } finally {
    props.tab.mcp_loading = false
  }
}

watch(formValues, () => emit('save'), { deep: true })
</script>

<style lang="less" scoped>
.mcp-pane { display: flex; flex-direction: column; height: 100%; }
.mcp-top {
  display: flex; align-items: center; gap: 8px; padding: 8px;
  border-bottom: 1px solid var(--el-border-color);
  .spacer { flex: 1; }
}
.mct-tabs { display: flex; gap: 16px; padding: 4px 12px; border-bottom: 1px solid var(--el-border-color); }
.mct-tab {
  font-size: 13px; padding: 4px 2px; cursor: pointer; color: var(--el-text-color-secondary);
  &.active { color: var(--el-text-color-primary); font-weight: 700; border-bottom: 2px solid var(--el-color-primary); }
}
.mcp-body { flex: 1; display: flex; min-height: 0; }
.col { display: flex; flex-direction: column; min-height: 0; min-width: 0; }

.headers-pane { padding: 16px; flex: 1; overflow: auto; }
.hint { font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 12px; }

.col-tools { width: 320px; flex-shrink: 0; border-right: 1px solid var(--el-border-color); }
.sub-tabs {
  display: flex; align-items: center; gap: 12px; padding: 6px 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  .sub-tab { font-size: 13px; padding: 2px 4px;
    &.active { font-weight: 700; border-bottom: 2px solid var(--el-color-primary); }
    &.disabled { color: var(--el-text-color-placeholder); }
  }
}
.tool-list { flex: 1; overflow-y: auto; padding: 4px 0; }
.tool-item { padding: 8px 12px; cursor: pointer; border-left: 2px solid transparent;
  &.selected { background: var(--el-color-primary-light-9); border-left-color: var(--el-color-primary); }
  &:hover { background: var(--el-fill-color-light); }
  .tool-title { font-size: 13px; font-weight: 600; }
  .tool-desc { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px; white-space: pre-wrap; }
}
.param-form {
  max-height: 45%; overflow-y: auto; border-top: 1px solid var(--el-border-color);
  padding: 8px 12px;
  .field { margin-bottom: 10px; }
  .field-label { font-size: 12px; font-weight: 600;
    .req { color: var(--el-color-danger); margin-left: 2px; }
    .field-type { color: var(--el-text-color-secondary); font-weight: 400; margin-left: 6px; }
  }
  .field-desc { font-size: 11px; color: var(--el-text-color-secondary); margin: 2px 0 4px; }
}

.col-req { width: 360px; flex-shrink: 0; border-right: 1px solid var(--el-border-color); }
.col-resp { flex: 1; }
.col-head {
  padding: 6px 10px; font-weight: 600; font-size: 13px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  display: flex; align-items: center; gap: 8px;
}
.resp-body { flex: 1; padding: 8px; min-height: 0; }
.resp-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--el-text-color-placeholder); font-size: 13px; }
</style>
