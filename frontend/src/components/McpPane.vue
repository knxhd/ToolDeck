<template>
  <div class="mcp-pane">
    <!-- 顶部：选择 Server + 连接 + Run -->
    <div class="mcp-top">
      <el-select v-model="tab.mcp_server" placeholder="选择 MCP Server" style="width: 260px" @change="onServerChange">
        <el-option v-for="s in mcp.servers" :key="s.name" :label="s.name" :value="s.name" />
      </el-select>
      <el-button :loading="connecting" @click="onConnect">{{ connected ? '已连接' : '连接' }}</el-button>
      <div class="spacer"></div>
      <el-button type="success" :icon="VideoPlay" :loading="tab.mcp_loading" :disabled="!selectedTool" @click="onRun">Run</el-button>
    </div>

    <div class="mcp-body">
      <!-- 左：工具列表 + 参数表单 -->
      <div class="col col-tools">
        <div class="tabs">
          <span class="tab active">Tools</span>
          <span class="tab disabled">Prompts</span>
          <span class="tab disabled">Resources</span>
          <el-input v-model="keyword" size="small" placeholder="搜索" :prefix-icon="Search" style="margin-left: auto; width: 130px" />
          <el-button size="small" :icon="Refresh" circle @click="reloadTools" />
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
          <el-empty v-if="!filteredTools.length" :description="connected ? '无工具' : '请先连接 Server'" :image-size="50" />
        </div>

        <!-- 选中工具的参数表单 -->
        <div v-if="selectedTool" class="param-form">
          <div v-for="f in fields" :key="f.key" class="field">
            <div class="field-label">
              {{ f.key }}<span class="req" v-if="f.required">*</span>
              <span class="field-type">{{ f.type }}</span>
            </div>
            <div class="field-desc" v-if="f.description">{{ f.description }}</div>
            <el-switch v-if="f.type === 'boolean'" v-model="formValues[f.key]" />
            <el-input-number v-else-if="f.type === 'number' || f.type === 'integer'" v-model="formValues[f.key]" style="width: 100%" />
            <el-input
              v-else
              v-model="formValues[f.key]"
              :type="f.longText ? 'textarea' : 'text'"
              :rows="3"
              :placeholder="f.type === 'object' || f.type === 'array' ? '{}' : ''"
            />
          </div>
        </div>
      </div>

      <!-- 中：请求预览 -->
      <div class="col col-req">
        <div class="col-head">Message</div>
        <MonacoEditor :model-value="requestPreview" language="json" read-only height="100%" />
      </div>

      <!-- 右：响应 -->
      <div class="col col-resp">
        <div class="col-head resp-head">
          <span>Response</span>
          <el-tag v-if="connected" type="success" size="small" effect="plain">Connected</el-tag>
        </div>
        <div v-if="tab.mcp_result" class="resp-body">
          <MonacoEditor :model-value="tab.mcp_result" language="json" read-only height="100%" auto-scroll-to-end />
        </div>
        <div v-else class="resp-empty">运行后在此查看结果</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, VideoPlay } from '@element-plus/icons-vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import { useMcpStore, type McpTool } from '@/stores/mcp'
import type { OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()
const emit = defineEmits<{ save: [] }>()

const mcp = useMcpStore()
const connecting = ref(false)
const connected = ref(false)
const keyword = ref('')
const selectedTool = ref<McpTool | null>(null)
const formValues = ref<Record<string, unknown>>({})

onMounted(async () => {
  await mcp.loadServers()
  if (props.tab.mcp_server) {
    await onConnect()
    if (props.tab.mcp_tool) {
      const t = mcp.tools.find((x) => x.name === props.tab.mcp_tool)
      if (t) selectTool(t)
    }
  }
})

const filteredTools = computed(() =>
  mcp.tools.filter((t) => !keyword.value || t.name.toLowerCase().includes(keyword.value.toLowerCase())),
)

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
  return Object.entries(props_).map(([key, def]) => {
    const desc = def.description || ''
    return {
      key,
      type: def.type || 'string',
      description: desc,
      required: required.includes(key),
      longText: desc.length > 40 || desc.includes('\n'),
    }
  })
})

async function onServerChange() {
  selectedTool.value = null
  formValues.value = {}
  connected.value = false
  emit('save')
}

async function onConnect() {
  if (!props.tab.mcp_server) {
    ElMessage.warning('请先选择 Server')
    return
  }
  connecting.value = true
  try {
    await mcp.loadTools(props.tab.mcp_server)
    connected.value = true
  } finally {
    connecting.value = false
  }
}

function reloadTools() {
  if (props.tab.mcp_server) onConnect()
}

function selectTool(t: McpTool) {
  selectedTool.value = t
  props.tab.mcp_tool = t.name
  // 用已有参数回填
  try {
    const existing = JSON.parse(props.tab.mcp_args || '{}')
    formValues.value = { ...existing }
  } catch {
    formValues.value = {}
  }
  // 缺省补空
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
    {
      method: 'tools/call',
      params: { name: selectedTool.value.name, arguments: buildArgs() },
    },
    null,
    2,
  )
})

async function onRun() {
  if (!selectedTool.value) return
  props.tab.mcp_args = JSON.stringify(buildArgs())
  props.tab.mcp_loading = true
  try {
    await mcp.callTool(props.tab.mcp_server, selectedTool.value.name, buildArgs())
    props.tab.mcp_result = JSON.stringify(mcp.lastResult, null, 2)
    emit('save')
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
.mcp-body { flex: 1; display: flex; min-height: 0; }
.col { display: flex; flex-direction: column; min-height: 0; min-width: 0; }

.col-tools { width: 320px; flex-shrink: 0; border-right: 1px solid var(--el-border-color); }
.tabs {
  display: flex; align-items: center; gap: 12px; padding: 6px 8px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  .tab { font-size: 13px; padding: 2px 4px; cursor: pointer;
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
