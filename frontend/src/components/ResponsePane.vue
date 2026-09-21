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
      <el-tab-pane label="Body" class="body-pane">
        <div class="body-toolbar">
          <el-radio-group v-model="bodyMode" size="small">
            <el-radio-button v-if="hasStream" value="stream">Stream</el-radio-button>
            <el-radio-button value="text">Text</el-radio-button>
            <el-radio-button value="json">JSON</el-radio-button>
            <el-radio-button value="html">HTML</el-radio-button>
          </el-radio-group>
          <span class="ct">{{ contentTypeName }}</span>
        </div>
        <div class="body-view">
          <div v-if="bodyMode === 'stream'" class="stream-log" ref="streamBoxRef">
            <div v-for="(e, i) in tab.stream_events" :key="i" class="stream-row">
              <span class="stream-time">{{ e.time }}</span>
              <span class="stream-dot" :class="e.type"></span>
              <span class="stream-type">{{ e.type }}</span>
              <span class="stream-data">{{ e.data }}</span>
            </div>
            <div v-if="tab.streaming" class="stream-live">● 接收中…</div>
          </div>
          <MonacoEditor
            v-else-if="bodyMode !== 'html'"
            :model-value="displayBody"
            :language="bodyMode === 'json' ? 'json' : 'plaintext'"
            read-only
            height="100%"
          />
          <iframe v-else class="html-frame" :srcdoc="tab.body" sandbox=""></iframe>
        </div>
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
import { computed, ref, nextTick, watch } from 'vue'
import MonacoEditor from '@/components/MonacoEditor.vue'
import type { OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()

const bodyMode = ref<'stream' | 'text' | 'json' | 'html'>('text')
const streamBoxRef = ref<HTMLElement | null>(null)

const hasStream = computed(() => props.tab.stream_events.length > 0)

watch(
  () => props.tab.streaming,
  (s) => { if (s) bodyMode.value = 'stream' },
)

watch(
  () => props.tab.stream_events.length,
  async () => {
    await nextTick()
    if (streamBoxRef.value) streamBoxRef.value.scrollTop = streamBoxRef.value.scrollHeight
  },
)

const headerRows = computed(() =>
  Object.entries(props.tab.headers || {}).map(([key, value]) => ({ key, value })),
)

const contentTypeName = computed(() => (props.tab.headers || {})['content-type'] || '')

// JSON 模式下尝试格式化；失败则原样显示
const displayBody = computed(() => {
  if (bodyMode.value !== 'json') return props.tab.body
  const raw = props.tab.body
  if (!raw) return ''
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
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
.resp-tabs { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.body-toolbar { display: flex; align-items: center; gap: 12px; padding: 2px 0 6px; }
.ct { font-size: 12px; color: var(--el-text-color-placeholder); }
.body-view { flex: 1; min-height: 0; }
.html-frame { width: 100%; height: 100%; border: 1px solid var(--el-border-color); border-radius: 4px; background: #fff; }

.stream-log {
  flex: 1; overflow-y: auto; font-family: var(--app-font-family);
  font-size: 13px; padding: 6px 8px;
}
.stream-row { display: flex; align-items: baseline; gap: 8px; padding: 2px 0; line-height: 1.5; }
.stream-time { color: var(--el-text-color-placeholder); font-size: 11px; flex-shrink: 0; width: 90px; }
.stream-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; align-self: center;
  &.meta { background: #61affe; } &.chunk { background: #49cc90; }
  &.done { background: #909399; } &.error { background: #f93e3e; }
}
.stream-type { font-weight: 700; width: 56px; flex-shrink: 0; font-size: 11px; color: var(--el-text-color-secondary); }
.stream-data { white-space: pre-wrap; word-break: break-all; color: var(--el-text-color-primary); }
.stream-live { color: var(--el-color-success); font-size: 12px; margin-top: 4px; animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: 0.4; } }
</style>
