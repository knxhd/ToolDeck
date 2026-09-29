<template>
  <div class="history-view">
    <a-tabs v-model="activeTab" @change="onTabChange">
      <a-tab-pane key="http" title="HTTP 调用">
        <div class="history-toolbar">
          <a-button size="small" status="danger" type="secondary" :disabled="!httpStore.history.length" @click="clearHttp">清空</a-button>
        </div>
        <a-table :data="httpStore.history" :pagination="false" :scroll="{ y: 480 }" size="small">
          <template #columns>
            <a-table-column data-index="method" title="方法" :width="80" />
            <a-table-column data-index="url" title="URL" ellipsis tooltip />
            <a-table-column data-index="status_code" title="状态" :width="70" />
            <a-table-column data-index="elapsed_ms" title="耗时(ms)" :width="90" />
            <a-table-column data-index="timestamp" title="时间" :width="180" />
            <a-table-column title="操作" :width="80">
              <template #cell="{ record }">
                <a-button size="mini" type="text" @click="loadHttp(record)">加载</a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="mcp" title="MCP 调用">
        <a-table :data="mcpStore.history" :pagination="false" :scroll="{ y: 480 }" size="small">
          <template #columns>
            <a-table-column data-index="server" title="Server" :width="120" />
            <a-table-column data-index="tool" title="工具" :width="140" />
            <a-table-column title="参数">
              <template #cell="{ record }"><pre class="cell-json">{{ JSON.stringify(record.args) }}</pre></template>
            </a-table-column>
            <a-table-column title="错误" :width="80">
              <template #cell="{ record }">
                <a-tag :color="record.is_error ? 'red' : 'green'" size="small">{{ record.is_error ? '是' : '否' }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column data-index="timestamp" title="时间" :width="180" />
            <a-table-column title="操作" :width="80">
              <template #cell="{ record }">
                <a-button size="mini" type="text" @click="showDetail(record)">详情</a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="llm" title="LLM 调用">
        <a-table :data="llmStore.history" :pagination="false" :scroll="{ y: 480 }" size="small">
          <template #columns>
            <a-table-column data-index="provider" title="Provider" :width="120" />
            <a-table-column data-index="model" title="模型" :width="140" />
            <a-table-column title="内容摘要" ellipsis tooltip>
              <template #cell="{ record }">{{ (record.content || '').slice(0, 80) }}</template>
            </a-table-column>
            <a-table-column title="Tokens" :width="80">
              <template #cell="{ record }">{{ record.usage?.total_tokens || 0 }}</template>
            </a-table-column>
            <a-table-column data-index="timestamp" title="时间" :width="180" />
            <a-table-column title="操作" :width="80">
              <template #cell="{ record }">
                <a-button size="mini" type="text" @click="showDetail(record)">详情</a-button>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:visible="detailVisible" title="详情" width="720px" :footer="false">
      <MonacoEditor :model-value="detailText" language="json" read-only height="420px" auto-scroll-to-end />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import MonacoEditor from '@/components/MonacoEditor.vue'
import { useHttpStore } from '@/stores/http'
import { useMcpStore } from '@/stores/mcp'
import { useLlmStore } from '@/stores/llm'
import { confirmDialog } from '@/utils/feedback'

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
  const ok = await confirmDialog('确认', '清空所有 HTTP 历史？')
  if (!ok) return
  await httpStore.clearHistory()
}
</script>

<style lang="less" scoped>
.history-view { padding: 12px; height: 100%; overflow: auto; background: var(--el-bg-color); }
.history-toolbar { margin-bottom: 8px; }
.cell-json { margin: 0; white-space: pre-wrap; word-break: break-all; font-size: 12px; max-height: 60px; overflow: hidden; }
</style>
