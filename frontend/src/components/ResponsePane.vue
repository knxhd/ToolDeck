<template>
  <div class="response-pane">
    <div class="resp-meta">
      <el-tag v-if="tab.error" type="danger" size="small">请求错误</el-tag>
      <el-tag v-else-if="tab.status_code" :type="statusType" size="small">
        {{ tab.status_code }} {{ tab.status_text }}
      </el-tag>
      <el-tag v-else-if="tab.streaming" type="warning" size="small" effect="dark">接收中…</el-tag>
      <span v-if="tab.elapsed_ms">耗时 {{ tab.elapsed_ms }} ms</span>
      <span v-if="tab.size_bytes"> {{ formatSize(tab.size_bytes) }}</span>
      <span v-if="!tab.body && !tab.error && !tab.status_code && !tab.streaming" class="hint">
        发送请求后在此查看响应；流式接口将逐块实时输出
      </span>
    </div>
    <div v-if="tab.error" class="error-box">{{ tab.error }}</div>
    <el-tabs v-else class="resp-tabs">
      <el-tab-pane label="Body">
        <MonacoEditor
          :model-value="tab.body"
          :language="bodyLanguage"
          read-only
          height="calc(100% - 20px)"
        />
      </el-tab-pane>
      <el-tab-pane label="Headers">
        <el-table :data="headerRows" size="small" max-height="260" border>
          <el-table-column prop="key" label="Header" width="40%" />
          <el-table-column prop="value" label="Value" show-overflow-tooltip />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MonacoEditor from '@/components/MonacoEditor.vue'
import type { OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()

const headerRows = computed(() =>
  Object.entries(props.tab.headers || {}).map(([key, value]) => ({ key, value })),
)

const bodyLanguage = computed(() => {
  const ct = (props.tab.headers || {})['content-type'] || ''
  return ct.includes('json') ? 'json' : 'plaintext'
})

const statusType = computed(() => {
  const c = props.tab.status_code
  if (c < 300) return 'success'
  if (c < 400) return 'warning'
  return 'danger'
})

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.response-pane { display: flex; flex-direction: column; height: 100%; padding: 0 8px 8px; }
.resp-meta { display: flex; align-items: center; gap: 12px; padding: 6px 2px; font-size: 13px; color: var(--el-text-color-secondary); min-height: 30px; }
.hint { color: var(--el-text-color-placeholder); }
.error-box {
  color: var(--el-color-danger); padding: 10px; margin-top: 8px;
  background: var(--el-color-danger-light-9); border-radius: 4px;
}
.resp-tabs { flex: 1; min-height: 0; }
</style>
