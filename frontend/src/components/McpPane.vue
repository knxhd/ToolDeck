<template>
  <div class="mcp-pane">
    <div class="mcp-bar">
      <el-select v-model="tab.mcp_server" placeholder="选择 MCP Server" style="width: 240px" @change="onServerChange">
        <el-option v-for="s in mcp.servers" :key="s.name" :label="s.name" :value="s.name" />
      </el-select>
      <el-select v-model="tab.mcp_tool" placeholder="选择工具" style="width: 240px" :disabled="!tab.mcp_server">
        <el-option v-for="t in mcp.tools" :key="t.name" :label="t.name" :value="t.name" />
      </el-select>
      <el-button type="primary" :loading="tab.mcp_loading" @click="onCall">调用</el-button>
    </div>
    <div v-if="currentTool" class="tool-desc">{{ currentTool.description }}</div>
    <div class="mcp-body">
      <div class="args-col">
        <div class="col-label">参数（JSON）</div>
        <MonacoEditor v-model="tab.mcp_args" language="json" height="100%" />
      </div>
      <div class="result-col">
        <div class="col-label">结果</div>
        <MonacoEditor :model-value="tab.mcp_result" language="json" read-only height="100%" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'

import MonacoEditor from '@/components/MonacoEditor.vue'
import { useMcpStore } from '@/stores/mcp'
import type { OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()
const emit = defineEmits<{ save: [] }>()

const mcp = useMcpStore()

onMounted(() => {
  mcp.loadServers()
  if (props.tab.mcp_server) mcp.loadTools(props.tab.mcp_server)
})

const currentTool = computed(() => mcp.tools.find((t) => t.name === props.tab.mcp_tool) || null)

async function onServerChange(name: string) {
  props.tab.mcp_tool = ''
  await mcp.loadTools(name)
  emit('save')
}

async function onCall() {
  if (!props.tab.mcp_server || !props.tab.mcp_tool) {
    ElMessage.warning('请先选择 Server 和工具')
    return
  }
  let args: Record<string, unknown>
  try {
    args = JSON.parse(props.tab.mcp_args || '{}')
  } catch {
    ElMessage.error('参数不是合法 JSON')
    return
  }
  props.tab.mcp_loading = true
  try {
    await mcp.callTool(props.tab.mcp_server, props.tab.mcp_tool, args)
    props.tab.mcp_result = JSON.stringify(mcp.lastResult, null, 2)
  } finally {
    props.tab.mcp_loading = false
  }
}

watch(() => [props.tab.mcp_server, props.tab.mcp_tool, props.tab.mcp_args], () => emit('save'), { deep: true })
</script>

<style lang="less" scoped>
.mcp-pane { display: flex; flex-direction: column; height: 100%; padding: 8px; gap: 8px; }
.mcp-bar { display: flex; gap: 8px; align-items: center; }
.tool-desc { font-size: 12px; color: var(--el-text-color-secondary); }
.mcp-body { flex: 1; display: flex; gap: 8px; min-height: 0; }
.args-col, .result-col { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.col-label { font-weight: 600; margin-bottom: 4px; }
</style>
