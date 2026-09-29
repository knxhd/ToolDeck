<template>
  <div class="http-workbench">
    <!-- 左：历史 -->
    <div class="panel history-panel">
      <div class="panel-header">
        <span>历史</span>
        <a-button size="small" status="danger" type="secondary" :disabled="!store.history.length" @click="onClear">清空</a-button>
      </div>
      <div class="history-list">
        <div
          v-for="(item, i) in store.history"
          :key="i"
          class="history-item"
          @click="store.loadFromHistory(item)"
        >
          <a-tag size="small" :color="methodTag(item.method)">{{ item.method }}</a-tag>
          <span class="history-url" :title="item.url">{{ item.url }}</span>
          <span class="history-status" :class="statusClass(item.status_code)">{{ item.status_code || '—' }}</span>
        </div>
        <a-empty v-if="!store.history.length" description="暂无历史" style="padding: 16px 0" />
      </div>
    </div>

    <!-- 中：请求编辑 -->
    <div class="panel request-panel">
      <div class="url-bar">
        <a-select v-model="store.request.method" style="width: 120px">
          <a-option v-for="m in methods" :key="m" :value="m">{{ m }}</a-option>
        </a-select>
        <a-input v-model="store.request.url" placeholder="https://api.example.com/path" allow-clear @press-enter="store.send" />
        <a-button type="primary" :loading="store.loading" @click="store.send">发送</a-button>
      </div>
      <a-tabs class="request-tabs">
        <a-tab-pane key="params" title="Params">
          <KeyValueEditor v-model="store.request.params" />
        </a-tab-pane>
        <a-tab-pane key="headers" title="Headers">
          <KeyValueEditor v-model="store.request.headers" />
        </a-tab-pane>
        <a-tab-pane key="body" title="Body">
          <a-radio-group v-model="store.request.body_type" type="button" style="margin-bottom: 8px">
            <a-radio value="none">none</a-radio>
            <a-radio value="json">JSON</a-radio>
            <a-radio value="raw">raw</a-radio>
            <a-radio value="form-data">form-data</a-radio>
          </a-radio-group>
          <MonacoEditor
            v-if="store.request.body_type !== 'none' && store.request.body_type !== 'form-data'"
            v-model="store.request.body"
            :language="store.request.body_type === 'json' ? 'json' : 'plaintext'"
            height="300px"
          />
          <KeyValueEditor
            v-else-if="store.request.body_type === 'form-data'"
            :model-value="formPairs"
            @update:model-value="onFormChange"
          />
          <a-empty v-else description="无 Body" style="padding: 12px 0" />
        </a-tab-pane>
      </a-tabs>
    </div>

    <!-- 右：响应 -->
    <div class="panel response-panel">
      <div v-if="store.error" class="error-box">{{ store.error }}</div>
      <template v-else-if="store.response">
        <div class="response-meta">
          <a-tag :color="statusTagType(store.response.status_code)">
            {{ store.response.status_code }} {{ store.response.status_text }}
          </a-tag>
          <span>耗时 {{ store.response.elapsed_ms }} ms</span>
          <span>{{ formatSize(store.response.size_bytes) }}</span>
        </div>
        <a-input v-model="headerSearch" placeholder="搜索响应头" size="small" allow-clear style="margin: 8px 0" />
        <a-table :data="filteredHeaders" :pagination="false" :scroll="{ y: 180 }" size="small">
          <template #columns>
            <a-table-column data-index="key" title="Header" />
            <a-table-column data-index="value" title="Value" ellipsis tooltip />
          </template>
        </a-table>
        <div class="response-body-label">响应体</div>
        <MonacoEditor
          :model-value="responseBody"
          :language="bodyLanguage"
          read-only
          height="calc(100% - 280px)"
        />
      </template>
      <a-empty v-else description="发送请求后查看响应" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import KeyValueEditor from '@/components/KeyValueEditor.vue'
import { useHttpStore } from '@/stores/http'
import { confirmDialog } from '@/utils/feedback'
import type { HttpMethod, KeyValue } from '@/api/types'

const store = useHttpStore()
const methods: HttpMethod[] = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
const headerSearch = ref('')

onMounted(() => store.loadHistory())

const filteredHeaders = computed(() =>
  Object.entries(store.response?.headers || {})
    .filter(([k]) => k.toLowerCase().includes(headerSearch.value.toLowerCase()))
    .map(([k, v]) => ({ key: k, value: v })),
)

const responseBody = computed(() => {
  const body = store.response?.body || ''
  if (body.length > 5 * 1024 * 1024) return body.slice(0, 5 * 1024 * 1024) + '\n\n[内容过大已截断]'
  return body
})

const bodyLanguage = computed(() => {
  const ct = store.response?.headers?.['content-type'] || ''
  return ct.includes('json') ? 'json' : 'plaintext'
})

// form-data 编解码
const formPairs = computed<KeyValue[]>(() => {
  try {
    const arr = JSON.parse(store.request.body || '[]')
    return arr.map((i: { key: string; value: string }) => ({ key: i.key, value: i.value, enabled: true }))
  } catch {
    return []
  }
})

function onFormChange(pairs: KeyValue[]) {
  store.request.body = JSON.stringify(pairs.map((p) => ({ key: p.key, value: p.value })))
}

async function onClear() {
  const ok = await confirmDialog('确认', '确定清空所有 HTTP 历史？')
  if (!ok) return
  await store.clearHistory()
}

function methodTag(m: string) {
  const map: Record<string, 'green' | 'orange' | 'red' | 'blue'> = {
    GET: 'green', POST: 'orange', DELETE: 'red', PUT: 'blue',
  }
  return map[m] || 'blue'
}

function statusClass(code: number) {
  if (!code) return ''
  if (code < 300) return 'ok'
  if (code < 400) return 'redirect'
  return 'err'
}

function statusTagType(code: number) {
  if (code === 0) return 'blue'
  if (code < 300) return 'green'
  if (code < 400) return 'orange'
  return 'red'
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style lang="less" scoped>
.http-workbench {
  display: flex;
  height: 100%;
  gap: 1px;
  background: var(--el-border-color);
}
.panel {
  background: var(--el-bg-color);
  overflow: auto;
  display: flex;
  flex-direction: column;
}
.history-panel { width: 280px; flex-shrink: 0; }
.request-panel { flex: 1; min-width: 0; }
.response-panel { width: 420px; flex-shrink: 0; padding: 8px; }
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color);
  font-weight: 600;
}
.history-list { flex: 1; overflow-y: auto; }
.history-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-lighter);
  &:hover { background: var(--el-fill-color-light); }
}
.history-url {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
}
.history-status { font-size: 12px; }
.history-status.ok { color: var(--el-color-success); }
.history-status.redirect { color: var(--el-color-warning); }
.history-status.err { color: var(--el-color-danger); }
.url-bar {
  display: flex;
  gap: 8px;
  padding: 8px;
  border-bottom: 1px solid var(--el-border-color);
}
.request-tabs { padding: 0 8px; flex: 1; overflow: auto; }
.response-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 4px 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.error-box {
  color: var(--el-color-danger);
  padding: 12px;
  background: var(--el-color-danger-light-9);
  border-radius: 4px;
}
.response-body-label { font-weight: 600; margin: 8px 0 4px; }
</style>
