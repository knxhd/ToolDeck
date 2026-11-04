<template>
  <div class="response-pane">
    <div class="resp-meta">
      <span v-if="tab.error" class="status-pill err">请求错误</span>
      <span v-else-if="tab.status_code" class="status-pill" :class="statusClass">
        {{ tab.status_code }} {{ tab.status_text }}
      </span>
      <span v-else-if="tab.streaming" class="status-pill redirect">接收中…</span>
      <span v-if="tab.elapsed_ms" class="meta-item">{{ tab.elapsed_ms }} ms</span>
      <span v-if="tab.size_bytes" class="meta-item">{{ formatSize(tab.size_bytes) }}</span>
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
            </a-select>
          </div>
          <div class="stream-layout">
            <div v-if="mergeType" class="merge-view">
              <div v-if="merged.reasoning" class="reasoning-block">
                <div class="reasoning-header" @click="reasoningOpen = !reasoningOpen">
                  <span class="reasoning-title">
                    <span class="reasoning-icon"></span>
                  </span>
                  <span class="reasoning-toggle">{{ reasoningOpen ? '收起' : '展开' }}</span>
                </div>
                <div v-show="reasoningOpen" class="reasoning-body">
                  <v-md-preview :text="merged.reasoning" />
                </div>
              </div>
              <div class="content-block">
                <v-md-preview :text="merged.content" />
              </div>
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

const statusClass = computed(() => {
  const c = props.tab.status_code
  if (!c) return ''
  if (c < 300) return 's2'
  if (c < 400) return 's3'
  if (c < 500) return 's4'
  return 's5'
})

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const mergeType = ref('')
const reasoningOpen = ref(true)

// 合并结果：正文 + 思考过程（reasoning_content），两者分别渲染
const merged = computed(() => {
  if (!mergeType.value) {
    return { content: '', reasoning: '' }
  }
  try {
    // 把所有 chunk 拼成完整字节流，再逐行解析：
    // 单个 chunk 可能是半截 JSON，独立 parse 会丢帧；拼接后能还原完整 JSON 行。
    const all = props.tab.stream_events.map((m) => m.data).join('')
    return parseMessages(all, mergeType.value)
  } catch (error) {
    console.error(error)
    mergeType.value = ''
    return { content: '', reasoning: '' }
  }
})
</script>

<style scoped lang="less">
.response-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.resp-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  height: 38px;
  padding: 0 10px;
  border-bottom: 1px solid var(--ui-border-soft);
  font-size: 12px;
  color: var(--color-text-3);
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--ui-font-mono);
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-3);

  & + .meta-item::before {
    content: '';
    width: 1px;
    height: 10px;
    margin-right: 6px;
    background: var(--ui-border);
  }
}

.hint {
  color: var(--color-text-4);
}

.error-box {
  margin: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(220, 70, 64, 0.28);
  border-left: 3px solid var(--ui-accent-danger);
  border-radius: var(--ui-radius-md);
  background: var(--ui-status-5xx-bg);
  color: var(--ui-accent-danger);
  font-family: var(--ui-font-mono);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.resp-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;

  :deep(.arco-tabs-nav) {
    flex-shrink: 0;
    height: 34px;
    padding: 0 10px;

    &::before {
      display: none;
    }
  }

  :deep(.arco-tabs-tab) {
    height: 24px;
    margin: 0 2px 0 0;
    padding: 0 10px;
    border: none;
    border-radius: var(--ui-radius-sm);
    background: transparent;
    color: var(--color-text-3);
    font-size: 12.5px;
    transition: color 0.15s ease, background-color 0.15s ease;

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
    overflow: auto;
    padding: 0 10px 10px;
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
  gap: 10px;
}

.merge-toolbar {
  flex-shrink: 0;
  padding: 2px 0 8px;
}

/* 合并后的 Markdown 内容：占满剩余高度，超出时纵向滚动 */
.merge-view {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

/* 思考过程（reasoning_content）：弱化样式，与正文区分 */
.reasoning-block {
  margin: 10px 0;
  border: 1px solid var(--ui-border-soft);
  border-left: 2px solid var(--ui-accent-warm);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);
  overflow: hidden;
}

.reasoning-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 10px;
  cursor: pointer;
  font-size: 12px;
  color: var(--color-text-3);
  user-select: none;

  &:hover {
    background: var(--ui-bg-hover);
  }

  .reasoning-title {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    color: var(--color-text-2);
  }

  .reasoning-icon {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ui-accent-warm);
  }

  .reasoning-toggle {
    color: rgb(var(--primary-6));
    font-size: 11.5px;
  }
}

.reasoning-body {
  padding: 2px 12px 6px;
  font-size: 13px;
  color: var(--color-text-3);

  :deep(.github-markdown-body) {
    background: transparent;
    color: var(--color-text-3);
    font-size: 13px;
    padding: 0;
  }
}

/* 正文区域：保持默认 Markdown 样式 */
.content-block {
  min-width: 0;
}

.frame-list {
  width: 100%;
  min-height: 0;
  overflow-y: auto;
  padding: 2px 2px 6px;

  .frame-row {
    display: flex;
    width: 100%;
    align-items: center;
    gap: 8px;
    padding: 4px 8px;
    border-radius: var(--ui-radius-sm);
    cursor: pointer;
    font-size: 12px;

    &:hover {
      background: var(--ui-bg-hover);
    }

    &.active {
      background: var(--ui-bg-active);
    }

    .frame-idx {
      font-weight: 700;
      color: var(--color-text-3);
      width: 34px;
      flex-shrink: 0;
    }

    .frame-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      flex-shrink: 0;

      &.meta {
        background: var(--ui-method-put);
      }

      &.chunk {
        background: var(--ui-method-get);
      }

      &.done {
        background: var(--color-text-4);
      }

      &.error {
        background: var(--ui-accent-danger);
      }
    }

    .frame-time {
      color: var(--color-text-4);
      font-family: var(--ui-font-mono);
      font-size: 10.5px;
      flex-shrink: 0;
    }

    .frame-preview {
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--color-text-2);
      font-family: var(--ui-font-mono);
    }
  }
}

.stream-live {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  color: var(--ui-accent-ok);
  font-size: 12px;
  animation: blink 1s infinite;
}

.frame-time {
  font-family: var(--ui-font-mono);
  font-size: 11px;
  color: var(--color-text-4);
}

.html-frame {
  width: 100%;
  height: 100%;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: #fff;
}

/* SSE 帧折叠列表：去掉 Arco 默认的分割线与缩进 */
.custom-arco-design {
  flex: 1;
  min-width: 0;
  overflow-y: auto;

  :deep(.arco-collapse-item-header) {
    padding: 0;
    border: none;
    background: transparent;
  }

  :deep(.arco-collapse-item-content) {
    padding: 0;
    background: transparent;
  }

  :deep(.arco-collapse-item-content-box) {
    padding: 4px 8px 8px;
  }
}

@keyframes blink {
  50% {
    opacity: 0.4;
  }
}
</style>
