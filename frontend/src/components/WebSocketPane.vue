<template>
  <div class="ws-pane">
    <div class="ws-bar">
      <el-input v-model="tab.ws_url" placeholder="wss://echo.websocket.events" style="flex: 1" />
      <el-button v-if="!ws" type="primary" @click="connect">连接</el-button>
      <el-button v-else type="danger" plain @click="disconnect">断开</el-button>
    </div>
    <div class="ws-log" ref="logEl">
      <div v-for="(m, i) in messages" :key="i" class="ws-msg" :class="m.dir">
        <span class="ws-time">{{ m.time }}</span>
        <span class="ws-text">{{ m.data }}</span>
      </div>
      <el-empty v-if="!messages.length" description="连接后在此收发消息" :image-size="50" />
    </div>
    <div class="ws-input">
      <el-input v-model="draft" type="textarea" :rows="3" placeholder="输入要发送的消息，Ctrl+Enter 发送"
        @keydown.ctrl.enter="send" />
      <el-button type="primary" :disabled="!ws" @click="send">发送</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
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
    ElMessage.error((e as Error).message)
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
.ws-pane { display: flex; flex-direction: column; height: 100%; padding: 8px; gap: 8px; }
.ws-bar { display: flex; gap: 8px; }
.ws-log { flex: 1; overflow-y: auto; border: 1px solid var(--el-border-color); border-radius: 4px; padding: 8px; font-family: monospace; font-size: 12px; }
.ws-msg { display: flex; gap: 8px; padding: 2px 0; }
.ws-time { color: var(--el-text-color-placeholder); }
.ws-msg.in .ws-text { color: var(--el-color-success); }
.ws-msg.out .ws-text { color: var(--el-color-primary); }
.ws-msg.sys .ws-text { color: var(--el-text-color-secondary); }
.ws-input { display: flex; gap: 8px; align-items: flex-end; }
.ws-input .el-textarea { flex: 1; }
</style>
