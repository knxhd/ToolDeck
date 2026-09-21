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
        发送请求后在此查看响应
      </span>
    </div>
    <div v-if="tab.error" class="error-box">{{ tab.error }}</div>
    <el-tabs v-else class="resp-tabs">
      <el-tab-pane label="Body" class="body-pane">
        <div class="body-toolbar">
          <el-select v-model="fmt" size="small" style="width: 110px">
            <el-option label="Text" value="text" />
            <el-option label="JSON" value="json" />
            <el-option label="HTML" value="html" />
          </el-select>
          <span class="ct">{{ contentTypeName }}</span>
        </div>

        <div class="body-view">
          <!-- 流式：左帧列表 + 右详情 -->
          <template v-if="contentTypeName && contentTypeName.includes('text/event-stream')">
            <div class="frame-list">
              <div v-for="(e, i) in tab.stream_events" :key="i" class="frame-row"
                :class="{ active: i === selectedFrame }" @click="selectedFrame = i">
                <template v-if="e.data.trim().length > 0">
                  <div v-if="e.data.trim().length > 0">
                    <span class="frame-dot" :class="e.type"></span>
                    <span class="frame-preview">{{ preview(e.data) }}</span>
                  </div>
                  <div>
                    <span class="frame-time">{{ e.time }}</span>
                  </div>
                </template>

              </div>
              <div v-if="tab.streaming" class="stream-live">● 接收中…</div>
            </div>
          </template>

          <!-- 非流式：单视图 -->
          <template v-else>
            <MonacoEditor v-if="fmt !== 'html'" :model-value="rendered(tab.body)"
              :language="fmt === 'json' ? 'json' : 'plaintext'" read-only height="100%" />
            <iframe v-else class="html-frame" :srcdoc="tab.body" sandbox=""></iframe>
          </template>
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
import { computed, ref, watch } from 'vue'
import MonacoEditor from '@/components/MonacoEditor.vue'
import type { OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()

const fmt = ref<'text' | 'json' | 'html'>('text')
const selectedFrame = ref(0)

const headerRows = computed(() =>
  Object.entries(props.tab.headers || {}).map(([key, value]) => ({ key, value })),
)


const contentTypeName = computed(() => {
  const headers = props.tab.headers || {}
  const contentType = headers['content-type'] || ''
  return contentType
})
const currentFrame = computed(() => props.tab.stream_events[selectedFrame.value] || null)

// 流式到达时自动选中最新一帧
watch(
  () => props.tab.stream_events.length,
  () => { selectedFrame.value = props.tab.stream_events.length - 1 },
)

function preview(data: string) {
  const s = (data || '').replace(/\s+/g, ' ').trim()
  return s.length > 60 ? s.slice(0, 60) + '…' : s
}

function rendered(raw: string) {
  if (fmt.value !== 'json' || !raw) return raw || ''
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}

function tagType(type: string) {
  if (type === 'error') return 'danger'
  if (type === 'meta' || type === 'done') return 'info'
  return 'success'
}

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

<style scoped lang="less">
.response-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0 8px 8px;
}

.resp-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 2px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  min-height: 30px;
}

.hint {
  color: var(--el-text-color-placeholder);
}

.error-box {
  color: var(--el-color-danger);
  padding: 10px;
  margin-top: 8px;
  background: var(--el-color-danger-light-9);
  border-radius: 4px;
}

.resp-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.body-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 2px 0 6px;
}

.ct {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.frame-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.body-view {
  flex: 1;
  min-height: 0;
  display: flex;
}

.frame-list {
  width: 100%;
  flex-shrink: 0;
  border-right: 1px solid var(--el-border-color);
  overflow-y: auto;
  padding: 4px;

  .frame-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    padding: 5px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;

    &:hover {
      background: var(--el-fill-color-light);
    }

    &.active {
      background: var(--el-color-primary-light-9);
    }

    .frame-idx {
      font-weight: 700;
      color: var(--el-text-color-secondary);
      width: 34px;
      flex-shrink: 0;
    }

    .frame-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;

      &.meta {
        background: #61affe;
      }

      &.chunk {
        background: #49cc90;
      }

      &.done {
        background: #909399;
      }

      &.error {
        background: #f93e3e;
      }
    }

    .frame-time {
      color: var(--el-text-color-placeholder);
      font-size: 11px;
      flex-shrink: 0;
    }

    .frame-preview {
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--el-text-color-secondary);
    }
  }
}



.stream-live {
  color: var(--el-color-success);
  font-size: 12px;
  padding: 6px 8px;
  animation: blink 1s infinite;
}

.frame-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.html-frame {
  width: 100%;
  height: 100%;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: #fff;
}

@keyframes blink {
  50% {
    opacity: 0.4;
  }
}
</style>
