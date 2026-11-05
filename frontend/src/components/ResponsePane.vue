<template>
  <div class="response-pane">
    <div class="resp-meta">
      <span v-if="tab.error" class="status-pill err large">请求错误</span>
      <span v-else-if="tab.status_code" class="status-pill large" :class="statusClass">
        {{ tab.status_code }}
      </span>
      <span v-else-if="tab.streaming" class="status-pill redirect large">接收中…</span>
      <span v-if="tab.status_code" class="meta-item status-text">{{ tab.status_text }}</span>
      <span v-if="tab.elapsed_ms" class="meta-item">
        <span class="meta-label">耗时</span>{{ tab.elapsed_ms }} ms
      </span>
      <span v-if="tab.size_bytes" class="meta-item">
        <span class="meta-label">大小</span>{{ formatSize(tab.size_bytes) }}
      </span>
      <span v-if="!tab.body && !tab.error && !tab.status_code && !tab.streaming" class="hint">
        发送请求后在此查看响应
      </span>
      <div class="meta-actions">
        <a-button size="mini" type="text" :disabled="!tab.body" @click="copyBody">
          <template #icon><icon-copy /></template>
        </a-button>
        <a-button size="mini" type="text" :disabled="!tab.body && !tab.status_code && !tab.stream_events.length"
          @click="clearResponse">
          <template #icon><icon-delete /></template>
        </a-button>
      </div>
    </div>
    <div v-if="tab.error" class="error-box">
      <div class="error-icon">⚠</div>
      <div class="error-body">
        <div class="error-title">{{ errorTitle }}</div>
        <div class="error-msg">{{ tab.error }}</div>
        <div v-if="errorHint" class="error-hint">{{ errorHint }}</div>
      </div>
    </div>
    <a-tabs v-else class="resp-tabs" :lazy-load="true" :destroy-on-hide="true">
      <a-tab-pane key="body" title="Body" class="body-pane">
        <template v-if="contentTypeName && contentTypeName.includes('text/event-stream')">
          <div class="merge-toolbar">
            <span class="merge-label">响应格式</span>
            <a-select v-model="mergeType" :style="{ width: '200px' }" placeholder="选择解析格式" :allow-clear="true">
              <a-option value="OpenAi">OpenAI 兼容</a-option>
              <a-option value="Qwen">Qwen 协议</a-option>
            </a-select>
            <span class="merge-tip muted">按所选格式把 SSE 帧合并为完整正文</span>
          </div>
          <div class="stream-layout">
            <div v-if="mergeType" class="merge-view">
              <div v-if="merged.reasoning" class="reasoning-block">
                <div class="reasoning-header" @click="reasoningOpen = !reasoningOpen">
                  <span class="reasoning-title">
                    <span class="reasoning-icon"></span>
                    思考过程
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
            <div v-else class="frame-list-wrap">
              <div class="frame-list-head">
                <span>SSE 事件帧</span>
                <span class="frame-count muted">{{ tab.stream_events.length }} 帧</span>
              </div>
              <div v-if="!tab.stream_events.length && !tab.streaming" class="frame-empty muted">
                等待数据流…
              </div>
              <div class="frame-list custom-arco-design">
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
          </div>
        </template>
        <SingleDataView v-else :data="tab.body" :content-type="contentTypeName" />
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

const errorTitle = computed(() => {
  const e = props.tab.error || ''
  if (/超时|timeout/i.test(e)) return '请求超时'
  if (/connect|连接|refused|getaddrinfo|name or service/i.test(e)) return '无法连接服务器'
  if (/ssl|certificate|证书|verify/i.test(e)) return 'SSL 证书错误'
  if (/5\d\d/.test(e)) return '服务器内部错误'
  if (/4\d\d/.test(e)) return '请求被拒绝'
  return '请求失败'
})

const errorHint = computed(() => {
  const e = props.tab.error || ''
  if (/超时|timeout/i.test(e)) return '提示：可点击请求栏齿轮图标调大超时时间（默认 30 秒），或检查目标服务是否响应缓慢。'
  if (/connect|连接|refused|getaddrinfo|name or service/i.test(e)) return '提示：检查 URL 是否正确、目标服务是否启动、网络是否可达（内网需确认 VPN/代理）。'
  if (/ssl|certificate|证书|verify/i.test(e)) return '提示：自签证书可在请求栏齿轮里关闭"校验 SSL 证书"。'
  if (/5\d\d/.test(e)) return '提示：服务端内部错误，请检查接口日志或稍后重试。'
  if (/4\d\d/.test(e)) return '提示：检查请求参数、Header、鉴权是否正确。'
  return ''
})

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function copyBody() {
  const text = props.tab.body || ''
  try {
    await navigator.clipboard.writeText(text)
    // 简单提示：用 title 变更即可，避免引入 toast
  } catch {
    /* ignore */
  }
}

function clearResponse() {
  const t = props.tab
  t.body = ''
  t.status_code = 0
  t.status_text = ''
  t.headers = {}
  t.error = ''
  t.elapsed_ms = 0
  t.size_bytes = 0
  t.stream_events = []
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
  height: 40px;
  padding: 0 12px;
  border-bottom: 1px solid var(--ui-border-soft);
  font-size: 0.86em;
  color: var(--color-text-3);
}

.status-pill.large {
  font-size: 0.93em;
  font-weight: 700;
  min-width: 48px;
  padding: 3px 10px;
  border-radius: var(--ui-radius-sm);
}

.status-text {
  font-weight: 500;
  color: var(--color-text-2);
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--ui-font-mono);
  font-size: 0.82em;
  font-variant-numeric: tabular-nums;
  color: var(--color-text-3);

  .meta-label {
    font-family: var(--app-font-family);
    color: var(--color-text-4);
    margin-right: 2px;
  }

  &+.meta-item::before {
    content: '';
    width: 1px;
    height: 10px;
    margin-right: 6px;
    background: var(--ui-border);
  }
}

.meta-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 2px;
}

.hint {
  color: var(--color-text-4);
}

.error-box {
  margin: 10px;
  padding: 12px 14px;
  display: flex;
  gap: 10px;
  border: 1px solid rgba(220, 70, 64, 0.28);
  border-left: 3px solid var(--ui-accent-danger);
  border-radius: var(--ui-radius-md);
  background: var(--ui-status-5xx-bg);
  font-size: 0.93em;
  line-height: 1.5;

  .error-icon {
    font-size: 1.29em;
    color: var(--ui-accent-danger);
    flex-shrink: 0;
  }

  .error-title {
    font-weight: 600;
    color: var(--ui-accent-danger);
    margin-bottom: 2px;
  }

  .error-msg {
    font-family: var(--ui-font-mono);
    font-size: 0.86em;
    color: var(--color-text-2);
    word-break: break-all;
    white-space: pre-wrap;
  }

  .error-hint {
    margin-top: 6px;
    padding: 6px 8px;
    background: var(--ui-bg-subtle);
    border-radius: var(--ui-radius-sm);
    font-size: 0.86em;
    color: var(--color-text-3);
  }
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
    font-size: 0.89em;
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
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0 8px;
}

.merge-label {
  font-size: 0.86em;
  color: var(--color-text-2);
  font-weight: 500;
}

.merge-tip {
  font-size: 0.82em;
}

.frame-list-wrap {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.frame-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 4px 6px;
  font-size: 0.86em;
  font-weight: 600;
  color: var(--color-text-2);
}

.frame-empty {
  padding: 24px 0;
  text-align: center;
  font-size: 0.86em;
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
  font-size: 0.86em;
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
    font-size: 0.82em;
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
    font-size: 0.86em;

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
      font-size: 0.75em;
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
  font-size: 0.86em;
  animation: blink 1s infinite;
}

.frame-time {
  font-family: var(--ui-font-mono);
  font-size: 0.79em;
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
