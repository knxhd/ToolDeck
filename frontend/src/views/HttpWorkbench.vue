<template>
  <div class="http-workbench">
    <!-- 左：历史 -->
    <div class="panel history-panel">
      <div class="panel-header">
        <span>历史</span>
        <el-button size="small" type="danger" plain :disabled="!store.history.length" @click="onClear">清空</el-button>
      </div>
      <div class="history-list">
        <div
          v-for="(item, i) in store.history"
          :key="i"
          class="history-item"
          @click="store.loadFromHistory(item)"
        >
          <el-tag size="small" :type="methodTag(item.method)">{{ item.method }}</el-tag>
          <span class="history-url" :title="item.url">{{ item.url }}</span>
          <span class="history-status" :class="statusClass(item.status_code)">{{ item.status_code || '—' }}</span>
        </div>
        <el-empty v-if="!store.history.length" description="暂无历史" :image-size="60" />
      </div>
    </div>

    <!-- 中：请求编辑 -->
    <div class="panel request-panel">
      <div class="url-bar">
        <el-select v-model="store.request.method" style="width: 120px">
          <el-option v-for="m in methods" :key="m" :label="m" :value="m" />
        </el-select>
        <el-input v-model="store.request.url" placeholder="https://api.example.com/path" @keyup.enter="store.send" />
        <el-button type="primary" :loading="store.loading" @click="store.send">发送</el-button>
      </div>
      <el-tabs class="request-tabs">
        <el-tab-pane label="Params">
          <KeyValueEditor v-model="store.request.params" />
        </el-tab-pane>
        <el-tab-pane label="Headers">
          <KeyValueEditor v-model="store.request.headers" />
        </el-tab-pane>
        <el-tab-pane label="Body">
          <el-radio-group v-model="store.request.body_type" style="margin-bottom: 8px">
            <el-radio-button value="none">none</el-radio-button>
            <el-radio-button value="json">JSON</el-radio-button>
            <el-radio-button value="raw">raw</el-radio-button>
            <el-radio-button value="form-data">form-data</el-radio-button>
          </el-radio-group>
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
          <el-empty v-else description="无 Body" :image-size="40" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 右：响应 -->
    <div class="panel response-panel">
      <div v-if="store.error" class="error-box">{{ store.error }}</div>
      <template v-else-if="store.response">
        <div class="response-meta">
          <el-tag :type="statusTagType(store.response.status_code)">
            {{ store.response.status_code }} {{ store.response.status_text }}
          </el-tag>
          <span>耗时 {{ store.response.elapsed_ms }} ms</span>
          <span>{{ formatSize(store.response.size_bytes) }}</span>
        </div>
        <el-input v-model="headerSearch" placeholder="搜索响应头" size="small" style="margin: 8px 0" />
        <el-table :data="filteredHeaders" size="small" max-height="180" border>
          <el-table-column prop="key" label="Header" />
          <el-table-column prop="value" label="Value" show-overflow-tooltip />
        </el-table>
        <div class="response-body-label">响应体</div>
        <MonacoEditor
          :model-value="responseBody"
          :language="bodyLanguage"
          read-only
          height="calc(100% - 280px)"
        />
      </template>
      <el-empty v-else description="发送请求后查看响应" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'

import MonacoEditor from '@/components/MonacoEditor.vue'
import KeyValueEditor from '@/components/KeyValueEditor.vue'
import { useHttpStore } from '@/stores/http'
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
  await ElMessageBox.confirm('确定清空所有 HTTP 历史？', '确认', { type: 'warning' })
  await store.clearHistory()
}

function methodTag(m: string) {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    GET: 'success', POST: 'warning', DELETE: 'danger', PUT: 'info',
  }
  return map[m] || 'info'
}

function statusClass(code: number) {
  if (!code) return ''
  if (code < 300) return 'ok'
  if (code < 400) return 'redirect'
  return 'err'
}

function statusTagType(code: number) {
  if (code === 0) return 'info'
  if (code < 300) return 'success'
  if (code < 400) return 'warning'
  return 'danger'
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

watch(() => store.history, () => {}, { deep: true })
</script>

<style lang="less" scoped>
.http-workbench {
  display: flex;
  height: 100%;
  gap: 1px;
  background: var(--el-border-color);
}
.panel {
  background: #fff;
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
}
.history-item:hover { background: var(--el-fill-color-light); }
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
