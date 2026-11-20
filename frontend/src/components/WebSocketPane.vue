<template>
  <div class="ws-pane">
    <!-- 顶部请求条：与 HTTP 请求条同一套尺寸与配色 -->
    <div class="ws-bar">
      <div class="url-group">
        <span class="kind-badge">WS</span>
        <span class="url-divider"></span>
        <a-input :border="false" v-model="tab.ws_url" class="url-input" allow-clear
          placeholder="wss://echo.websocket.events" @press-enter="connect" />
      </div>
      <a-button v-if="!ws" type="primary" class="send-btn" @click="connect">连接</a-button>
      <a-button v-else status="danger" type="secondary" class="send-btn" @click="disconnect">断开</a-button>
    </div>

    <div class="ws-card">
      <div class="col-head">
        <span>消息记录</span>
        <span v-if="ws" class="state-pill">已连接</span>
      </div>
      <div class="ws-log" ref="logEl">
        <div v-for="(m, i) in messages" :key="i" class="ws-msg" :class="m.dir">
          <span class="ws-time">{{ m.time }}</span>
          <span class="ws-text">{{ m.data }}</span>
        </div>
        <a-empty v-if="!messages.length" description="连接后在此收发消息" style="padding: 16px 0" />
      </div>
    </div>

    <div class="ws-input" :class="{ 'is-focused': draftFocused }">
      <a-textarea :border="false" v-model="draft" class="draft-input" :auto-size="{ minRows: 3, maxRows: 8 }"
        placeholder="输入要发送的消息，Ctrl+Enter 发送" @focus="draftFocused = true" @blur="draftFocused = false"
        @keydown.ctrl.enter="send" />
      <a-button type="primary" class="send-btn" :disabled="!ws || !draft" @click="send">发送</a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { toast } from '@/utils/feedback'
import type { OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()
const emit = defineEmits<{ save: [] }>()

const ws = ref<WebSocket | null>(null)
const draft = ref('')
const draftFocused = ref(false)
const logEl = ref<HTMLElement>()

// 地址改动后自动保存（防抖，避免边输边写集合树）
let saveTimer: number | undefined
watch(() => props.tab.ws_url, () => {
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => emit('save'), 400)
})

interface Msg { dir: 'in' | 'out' | 'sys'; data: string; time: string }
const messages = ref<Msg[]>([])

function push(dir: Msg['dir'], data: string) {
  messages.value.push({ dir, data, time: new Date().toLocaleTimeString() })
  nextTick(() => {
    if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
  })
}

function connect() {
  if (!props.tab.ws_url) return
  try {
    const sock = new WebSocket(props.tab.ws_url)
    ws.value = sock
    sock.onopen = () => push('sys', '已连接')
    sock.onmessage = (ev) => push('in', String(ev.data))
    sock.onerror = () => push('sys', '连接出错')
    sock.onclose = () => {
      push('sys', '连接已关闭')
      ws.value = null
    }
  } catch (e) {
    toast.error((e as Error).message)
  }
}

function disconnect() {
  ws.value?.close()
}

function send() {
  if (!ws.value || !draft.value) return
  push('out', draft.value)
  ws.value.send(draft.value)
  draft.value = ''
}

onBeforeUnmount(() => {
  window.clearTimeout(saveTimer)
  ws.value?.close()
})
</script>

<style lang="less" scoped>
.ws-pane {
  display: flex;
  flex-direction: column;
  gap: 6px;
  height: 100%;
  min-height: 0;
}

/* 顶部请求条：尺寸与 RequestBar 一致 */
.ws-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  height: 48px;
  padding: 0 10px;
  background: var(--ui-bg-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
}

.url-group {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  height: 32px;
  padding-right: 2px;
  background: var(--ui-bg-subtle);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;

  &:focus-within {
    background: var(--ui-bg-panel);
    border-color: rgb(var(--primary-6));
    box-shadow: 0 0 0 3px rgba(var(--primary-6), 0.12);
  }

  :deep(.arco-input-wrapper) {
    height: 100%;
    padding: 0 8px 0 4px;
    background: transparent;
    border: none;
  }
}

.kind-badge {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  height: 100%;
  padding: 0 10px;
  border-radius: var(--ui-radius-sm);
  color: var(--ui-method-ws);
  font-family: var(--ui-font-mono);
  font-size: 0.86em;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.url-divider {
  flex-shrink: 0;
  width: 1px;
  height: 16px;
  margin-right: 2px;
  background: var(--ui-border);
}

.url-input {
  flex: 1;
  min-width: 0;
  height: 100%;

  :deep(.arco-input-wrapper) {
    height: 100%;
    padding: 0 8px 0 4px;
    background: transparent;
    border: none;
  }

  :deep(.arco-input) {
    font-family: var(--ui-font-mono);
    font-size: 12px;
  }
}

.send-btn.arco-btn {
  flex-shrink: 0;
  min-width: 84px;
  height: 32px;
  border-radius: var(--ui-radius-md);
  font-weight: 600;
}

.ws-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--ui-bg-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
  overflow: hidden;
}

.col-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  height: 38px;
  padding: 0 12px;
  border-bottom: 1px solid var(--ui-border-soft);
  color: var(--color-text-2);
  font-size: 0.89em;
  font-weight: 600;
}

.state-pill {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 7px;
  border-radius: 9px;
  background: var(--ui-status-2xx-bg);
  color: var(--ui-status-2xx);
  font-family: var(--ui-font-mono);
  font-size: 0.71em;
  font-weight: 700;
}

.ws-log {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 12px;
  font-family: var(--ui-font-mono);
  font-size: 12px;
  line-height: 1.7;
}

.ws-msg {
  display: flex;
  gap: 8px;
  padding: 2px 0;
}

.ws-time {
  flex-shrink: 0;
  color: var(--color-text-4);
  font-variant-numeric: tabular-nums;
}

.ws-text {
  min-width: 0;
  word-break: break-word;
}

.ws-msg.in .ws-text {
  color: var(--ui-status-2xx);
}

.ws-msg.out .ws-text {
  color: rgb(var(--primary-6));
}

.ws-msg.sys .ws-text {
  color: var(--color-text-3);
}

/* 发送区：与 HTTP 输入组同款边框 + 聚焦高亮 */
.ws-input {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  flex-shrink: 0;
  padding: 6px 8px 6px 10px;
  background: var(--ui-bg-panel);
  border-color: var(--ui-border);
  border-radius: var(--ui-radius-md);

  &.is-focused {
    background: var(--ui-bg-panel);
    border-color: rgb(var(--primary-6));
    box-shadow: 0 0 0 1px rgba(var(--primary-6), 1);
  }

  :deep(.arco-textarea-wrapper) {
    background: transparent;
    border: none;
  }
}

.draft-input {
  flex: 1;
  min-width: 0;

  :deep(.arco-input-wrapper) {
    background: transparent;
  }

  :deep(.arco-textarea) {
    font-family: var(--ui-font-mono);
    font-size: 12px;
    line-height: 1.7;
  }
}
</style>
