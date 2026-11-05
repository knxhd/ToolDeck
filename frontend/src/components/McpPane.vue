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
.mcp-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.mcp-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  height: 44px;
  padding: 0 10px;
  border-bottom: 1px solid var(--ui-border-soft);

  .spacer {
    flex: 1;
  }
}

.mct-tabs {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
  padding: 5px 10px;
  border-bottom: 1px solid var(--ui-border-soft);
}

.mct-tab {
  padding: 3px 10px;
  border-radius: var(--ui-radius-sm);
  color: var(--color-text-3);
  font-size: 12.5px;
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease;

  &:hover {
    color: var(--color-text-1);
    background: var(--ui-bg-hover);
  }

  &.active {
    background: var(--ui-bg-active);
    color: rgb(var(--primary-6));
    font-weight: 600;
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

.headers-pane {
  flex: 1;
  overflow: auto;
  padding: 14px;
}

.hint {
  margin-bottom: 12px;
  padding: 8px 10px;
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);
  color: var(--color-text-3);
  font-size: 11.5px;
  line-height: 1.7;
}

.col-tools {
  width: 320px;
  flex-shrink: 0;
  border-right: 1px solid var(--ui-border-soft);
}

.sub-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  height: 34px;
  padding: 0 8px;
  border-bottom: 1px solid var(--ui-border-soft);

  .sub-tab {
    padding: 2px 8px;
    border-radius: var(--ui-radius-sm);
    color: var(--color-text-3);
    font-size: 0.86em;
    cursor: pointer;

    &:hover {
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
    }
  }
}

.tool-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px;
}

.tool-item {
  margin-bottom: 2px;
  padding: 7px 9px;
  border-radius: var(--ui-radius-sm);
  cursor: pointer;
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
    font-size: 11.5px;
    white-space: pre-wrap;
  }
}

.param-form {
  max-height: 45%;
  overflow-y: auto;
  padding: 10px 12px;
  border-top: 1px solid var(--ui-border-soft);

  .field {
    margin-bottom: 10px;
  }

  .field-label {
    color: var(--color-text-2);
    font-size: 11.5px;
    font-weight: 600;

    .req {
      margin-left: 2px;
      color: var(--ui-accent-danger);
    }

    .field-type {
      margin-left: 6px;
      color: var(--color-text-4);
      font-family: var(--ui-font-mono);
      font-weight: 400;
    }
  }

  .field-desc {
    margin: 2px 0 4px;
    color: var(--color-text-4);
    font-size: 0.79em;
  }
}

.col-req {
  width: 360px;
  flex-shrink: 0;
  border-right: 1px solid var(--ui-border-soft);
}

.col-resp {
  flex: 1;
}

.col-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  height: 36px;
  padding: 0 10px;
  border-bottom: 1px solid var(--ui-border-soft);
  background: var(--ui-bg-subtle);
  color: var(--color-text-2);
  font-size: 0.86em;
  font-weight: 600;
}

.resp-body {
  flex: 1;
  min-height: 0;
  padding: 8px;
}

.resp-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-4);
  font-size: 12.5px;
}
</style>
