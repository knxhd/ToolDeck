<template>
  <div class="response-pane">
    <div class="resp-meta">
      <a-tag v-if="tab.error" color="red" size="small">请求错误</a-tag>
      <a-tag v-else-if="tab.status_code" :color="statusType" size="small">
        {{ tab.status_code }} {{ tab.status_text }}
      </a-tag>
      <a-tag v-else-if="tab.streaming" color="orange" size="small">接收中…</a-tag>
      <span v-if="tab.elapsed_ms">耗时 {{ tab.elapsed_ms }} ms</span>
      <span v-if="tab.size_bytes"> {{ formatSize(tab.size_bytes) }}</span>
      <span v-if="!tab.body && !tab.error && !tab.status_code && !tab.streaming" class="hint">
        发送请求后在此查看响应
      </span>
    </div>
    <div v-if="tab.error" class="error-box">{{ tab.error }}</div>
    <a-tabs v-else class="resp-tabs">
      <a-tab-pane key="body" title="Body" class="body-pane">
        <template v-if="contentTypeName && contentTypeName.includes('text/event-stream')">
          <div class="merge-toolbar">
            <a-select v-model="mergeType" :style="{ width: '320px' }" placeholder="数据合并" :allow-clear="true">
              <a-option value="OpenAi">OpenAi</a-option>
              <a-option value="Qwen">Qwen协议</a-option>
              <a-option value="Qwen3">Qwen3协议</a-option>
            </a-select>
          </div>
          <div class="stream-layout">
            <div v-if="mergeType" class="merge-view">
              <v-md-preview :text="mergeMessage(tab.stream_events)" />
            </div>
            <div class="frame-list custom-arco-design" v-else>
              <a-collapse :show-expand-icon="false" :bordered="false">
                <template v-for="(item, index) in tab.stream_events" :key="index">
                  <a-collapse-item v-if="item.data.trim().length > 0" :key="index">
                    <template #header>
                      <div class="frame-row" :class="{ active: index === selectedFrame }"
                        @click="selectedFrame = index">
                        <span class="frame-dot" :class="item.type"></span>
                        <span class="frame-preview">{{ item.data }}</span>
                        <span class="frame-time">{{ item.time }}</span>
                      </div>
                    </template>
                    <div style="width: 100%;height: 200px;overflow: auto;">
                      <SingleDataView :data="item.data || ''" />
                    </div>
                  </a-collapse-item>
                </template>
              </a-collapse>
              <div v-if="tab.streaming" class="stream-live">● 接收中…</div>
            </div>
          </div>
        </template>
        <SingleDataView v-else :data="tab.body" />
      </a-tab-pane>
      <a-tab-pane key="headers" title="Headers">
        <a-table :data="headerRows" :pagination="false" :scroll="{ y: 260 }" size="small">
          <template #columns>
            <a-table-column data-index="key" title="Header" :width="200" />
            <a-table-column data-index="value" title="Value" ellipsis tooltip />
          </template>
        </a-table>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import SingleDataView from '@/components/response/SingleDataView.vue';
import type { OpenTab } from '@/api/types'
import { parseMessages } from '@/utils/llmUtil'

const props = defineProps<{ tab: OpenTab }>()

const selectedFrame = ref(0)

const headerRows = computed(() =>
  Object.entries(props.tab.headers || {}).map(([key, value]) => ({ key, value })),
)

const contentTypeName = computed(() => {
  const headers = props.tab.headers || {}
  return headers['content-type'] || ''
})

// 流式到达时自动选中最新一帧
watch(
  () => props.tab.stream_events.length,
  () => { selectedFrame.value = props.tab.stream_events.length - 1 },
)

const statusType = computed(() => {
  const c = props.tab.status_code
  if (c < 300) return 'green'
  if (c < 400) return 'orange'
  return 'red'
})

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const mergeType = ref('')
const mergeMessage = (messages: Array<{ data: string }>) => {
  try {
    // 把所有 chunk 拼成完整字节流，再逐行解析：
    // 单个 chunk 可能是半截 JSON，独立 parse 会丢帧；拼接后能还原完整 JSON 行。
    const all = messages.map((m) => m.data).join('')
    return parseMessages(all, mergeType.value)
  } catch (error) {
    console.error(error)
    mergeType.value = ''
    return ''
  }
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

  :deep(.arco-tabs-nav) {
    flex-shrink: 0;
  }

  :deep(.arco-tabs-content) {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  :deep(.arco-tabs-content-list) {
    height: 100%;
  }

  :deep(.arco-tabs-content-item) {
    height: 100%;
    overflow: auto;
  }

  :deep(.arco-tabs-content-item-active) {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  :deep(.arco-tabs-content-item-active .arco-tabs-pane) {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
}

.body-pane {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.stream-layout {
  flex: 1;
  min-height: 0;
  display: flex;
}

.merge-toolbar {
  flex-shrink: 0;
}

/* 合并后的 Markdown 内容：占满剩余高度，超出时纵向滚动 */
.merge-view {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
}

.frame-list {
  width: 100%;
  min-height: 0;
  border-right: 1px solid var(--el-border-color);
  overflow-y: auto;
  padding: 4px;

  .frame-row {
    display: flex;
    width: 100%;
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
