<template>
  <div class="history-view">
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="HTTP 调用" name="http">
        <div class="history-toolbar">
          <el-button size="small" type="danger" plain :disabled="!httpStore.history.length" @click="clearHttp">清空</el-button>
        </div>
        <el-table :data="httpStore.history" size="small" border max-height="calc(100vh - 200px)">
          <el-table-column prop="method" label="方法" width="80" />
          <el-table-column prop="url" label="URL" show-overflow-tooltip />
          <el-table-column prop="status_code" label="状态" width="70" />
          <el-table-column prop="elapsed_ms" label="耗时(ms)" width="90" />
          <el-table-column prop="timestamp" label="时间" width="180" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" link @click="loadHttp(row)">加载</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="MCP 调用" name="mcp">
        <el-table :data="mcpStore.history" size="small" border max-height="calc(100vh - 200px)">
          <el-table-column prop="server" label="Server" width="120" />
          <el-table-column prop="tool" label="工具" width="140" />
          <el-table-column label="参数">
            <template #default="{ row }"><pre class="cell-json">{{ JSON.stringify(row.args) }}</pre></template>
          </el-table-column>
          <el-table-column label="错误" width="80">
            <template #default="{ row }"><el-tag :type="row.is_error ? 'danger' : 'success'" size="small">{{ row.is_error ? '是' : '否' }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="timestamp" label="时间" width="180" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" link @click="showDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="LLM 调用" name="llm">
        <el-table :data="llmStore.history" size="small" border max-height="calc(100vh - 200px)">
          <el-table-column prop="provider" label="Provider" width="120" />
          <el-table-column prop="model" label="模型" width="140" />
          <el-table-column label="内容摘要" show-overflow-tooltip>
            <template #default="{ row }">{{ (row.content || '').slice(0, 80) }}</template>
          </el-table-column>
          <el-table-column label="Tokens" width="80">
            <template #default="{ row }">{{ row.usage?.total_tokens || 0 }}</template>
          </el-table-column>
          <el-table-column prop="timestamp" label="时间" width="180" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" link @click="showDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="detailVisible" title="详情" width="720px">
      <MonacoEditor :model-value="detailText" language="json" read-only height="420px" auto-scroll-to-end />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'

import MonacoEditor from '@/components/MonacoEditor.vue'
import { useHttpStore } from '@/stores/http'
import { useMcpStore } from '@/stores/mcp'
import { useLlmStore } from '@/stores/llm'

const httpStore = useHttpStore()
const mcpStore = useMcpStore()
const llmStore = useLlmStore()
const router = useRouter()

const activeTab = ref('http')
const detailVisible = ref(false)
const detailText = ref('{}')

onMounted(() => {
  httpStore.loadHistory()
  mcpStore.loadHistory()
  llmStore.loadHistory()
})

function onTabChange() {
  // 切换 tab 时按需刷新
  if (activeTab.value === 'mcp' && !mcpStore.history.length) mcpStore.loadHistory()
  if (activeTab.value === 'llm' && !llmStore.history.length) llmStore.loadHistory()
}

function loadHttp(row: { method: string; url: string; headers: unknown[]; body_type: string; body: string }) {
  httpStore.loadFromHistory(row as never)
  router.push('/http')
}

function showDetail(row: unknown) {
  detailText.value = JSON.stringify(row, null, 2)
  detailVisible.value = true
}

async function clearHttp() {
  await ElMessageBox.confirm('清空所有 HTTP 历史？', '确认', { type: 'warning' })
  await httpStore.clearHistory()
}
</script>

<style lang="less" scoped>
.history-view { padding: 12px; height: 100%; overflow: auto; background: #fff; }
.history-toolbar { margin-bottom: 8px; }
.cell-json { margin: 0; white-space: pre-wrap; word-break: break-all; font-size: 12px; max-height: 60px; overflow: hidden; }
</style>
