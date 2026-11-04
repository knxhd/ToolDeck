<template>
  <div class="history-view">
    <a-tabs v-model="activeTab" @change="onTabChange">
      <a-tab-pane key="http" title="HTTP 调用">
        <div class="history-toolbar">
          <a-button size="small" status="danger" type="secondary" :disabled="!httpStore.history.length" @click="clearHttp">清空</a-button>
        </div>
        <a-table :data="httpStore.history" :pagination="false" :scroll="{ y: 480 }" size="small">
          <template #columns>
            <a-table-column data-index="method" title="方法" :width="88">
              <template #cell="{ record }">
                <span class="method-pill" :class="'m-' + String(record.method).toLowerCase()">{{ record.method }}</span>
              </template>
            </a-table-column>
            <a-table-column data-index="url" title="URL" ellipsis tooltip />
            <a-table-column data-index="status_code" title="状态" :width="84">
              <template #cell="{ record }">
                <span class="status-pill" :class="statusClass(record.status_code)">
                  {{ record.status_code || '—' }}
                </span>
              </template>
            </a-table-column>
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

function statusClass(code?: number) {
  if (!code) return ''
  if (code < 300) return 's2'
  if (code < 400) return 's3'
  if (code < 500) return 's4'
  return 's5'
}

async function clearHttp() {
  const ok = await confirmDialog('确认', '清空所有 HTTP 历史？')
  if (!ok) return
  await httpStore.clearHistory()
}
</script>

<style lang="less" scoped>
.history-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 6px;
  background: var(--ui-bg-canvas);
  overflow: hidden;

  :deep(.arco-tabs) {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 2px 12px 10px;
    border: 1px solid var(--ui-border);
    border-radius: var(--ui-radius-lg);
    background: var(--ui-bg-panel);
    overflow: hidden;
  }

  :deep(.arco-tabs-nav) {
    flex-shrink: 0;
    height: 42px;

    &::before {
      display: none;
    }
  }

  :deep(.arco-tabs-tab) {
    height: 26px;
    margin: 0 2px 0 0;
    padding: 0 10px;
    border: none;
    border-radius: var(--ui-radius-sm);
    color: var(--color-text-3);
    font-size: 12.5px;

    &:hover {
      color: var(--color-text-1);
      background: var(--ui-bg-hover);
    }
  }

  :deep(.arco-tabs-tab-active) {
    background: var(--ui-bg-active);
    color: rgb(var(--primary-6));
    font-weight: 600;
  }

  :deep(.arco-tabs-ink-bar) {
    display: none;
  }

  :deep(.arco-tabs-content) {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  :deep(.arco-tabs-content-item-active) {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
}

.history-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  height: 40px;

  :deep(.arco-btn) {
    height: 26px;
    padding: 0 10px;
    border-radius: var(--ui-radius-sm);
    font-size: 12px;
  }
}

.cell-json {
  margin: 0;
  max-height: 60px;
  overflow: hidden;
  font-family: var(--ui-font-mono);
  font-size: 11.5px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
