<template>
  <div class="ws-pane">
    <div class="ws-bar">
      <a-input v-model="tab.ws_url" placeholder="wss://echo.websocket.events" allow-clear style="flex: 1" />
      <a-button v-if="!ws" type="primary" @click="connect">连接</a-button>
      <a-button v-else status="danger" type="secondary" @click="disconnect">断开</a-button>
    </div>
    <div class="ws-log" ref="logEl">
      <div v-for="(m, i) in messages" :key="i" class="ws-msg" :class="m.dir">
        <span class="ws-time">{{ m.time }}</span>
        <span class="ws-text">{{ m.data }}</span>
      </div>
      <a-empty v-if="!messages.length" description="连接后在此收发消息" style="padding: 16px 0" />
    </div>
    <div class="ws-input">
      <a-textarea v-model="draft" :auto-size="{ minRows: 3 }" placeholder="输入要发送的消息，Ctrl+Enter 发送"
        @keydown.ctrl.enter="send" style="flex: 1" />
      <a-button type="primary" :disabled="!ws" @click="send">发送</a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from 'vue'
import { toast } from '@/utils/feedback'
import type { OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()

const ws = ref<WebSocket | null>(null)
const draft = ref('')
const logEl = ref<HTMLElement>()

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

onBeforeUnmount(() => ws.value?.close())
</script>

<style lang="less" scoped>
.ws-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  gap: 8px;
  padding: 10px;
}

.ws-bar {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.ws-log {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px 10px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);
  font-family: var(--ui-font-mono);
  font-size: 11.5px;
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

.ws-msg.in .ws-text {
  color: var(--ui-accent-ok);
}

.ws-msg.out .ws-text {
  color: rgb(var(--primary-6));
}

.ws-msg.sys .ws-text {
  color: var(--color-text-3);
}

.ws-input {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  flex-shrink: 0;
}
</style>
