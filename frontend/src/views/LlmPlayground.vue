<template>
  <div class="llm-playground">
    <!-- 左：Provider 列表 -->
    <div class="panel provider-panel">
      <div class="panel-header">
        <span>Providers</span>
        <a-button size="small" type="secondary" @click="openAdd">
          <template #icon><icon-plus /></template>
          添加
        </a-button>
      </div>
      <div class="provider-list">
        <div
          v-for="p in store.providers"
          :key="p.name"
          class="provider-item"
          :class="{ active: store.selectedProvider === p.name }"
          @click="store.selectedProvider = p.name"
        >
          <div class="provider-name">{{ p.name }} <a-tag size="small">{{ p.provider_type }}</a-tag></div>
          <div class="provider-model">{{ p.model }}</div>
          <div class="provider-key">{{ maskApiKey(p.api_key) }}</div>
          <div class="provider-actions">
            <a-button size="mini" type="text" @click.stop="openEdit(p)">编辑</a-button>
            <a-button size="mini" type="text" status="danger" @click.stop="onDelete(p.name)">删除</a-button>
          </div>
        </div>
        <a-empty v-if="!store.providers.length" description="暂无 Provider" style="padding: 16px 0" />
      </div>
    </div>

    <!-- 右：聊天面板 -->
    <div class="panel chat-panel">
      <div v-if="!store.selectedProvider" class="empty-tip">
        <a-empty description="选择左侧 Provider 开始对话" />
      </div>
      <template v-else>
        <div class="chat-toolbar">
          <a-input-number v-model="temperature" :min="0" :max="2" :step="0.1" size="small" />
          <a-checkbox v-model="useStream">流式</a-checkbox>
          <a-button type="primary" :loading="store.streaming" :disabled="!canSend" @click="onSend">发送</a-button>
          <a-button @click="store.clearMessages">清空</a-button>
        </div>
        <div class="messages">
          <div v-for="(m, i) in store.messages" :key="i" class="message" :class="m.role">
            <a-tag size="small" :color="roleTag(m.role)">{{ m.role }}</a-tag>
            <MonacoEditor :model-value="m.content" language="plaintext" read-only height="auto" auto-scroll-to-end />
          </div>
        </div>
        <div v-if="store.streaming" class="streaming-tip">生成中... {{ store.streamingText.length }} 字</div>
        <div v-if="store.streamInterrupted" class="error-box">已中断：{{ store.error }}</div>
        <div v-if="store.lastUsage" class="usage-tip">{{ store.lastUsage }}</div>
      </template>
    </div>

    <!-- 添加/编辑 Provider -->
    <a-modal v-model:visible="dialogVisible" :title="editing ? '编辑 Provider' : '添加 Provider'" width="560px">
      <div class="dialog-form">
        <div class="form-row">
          <span class="form-label">name</span>
          <a-input v-model="form.name" :disabled="editing" />
        </div>
        <div class="form-row">
          <span class="form-label">base_url</span>
          <a-input v-model="form.base_url" placeholder="https://api.deepseek.com" />
        </div>
        <div class="form-row">
          <span class="form-label">api_key</span>
          <a-input-password v-model="form.api_key" />
        </div>
        <div class="form-row">
          <span class="form-label">model</span>
          <a-input v-model="form.model" placeholder="deepseek-chat" />
        </div>
        <div class="form-row">
          <span class="form-label">provider_type</span>
          <a-select v-model="form.provider_type" style="width: 100%">
            <a-option value="openai">openai (Compatible)</a-option>
            <a-option value="anthropic">anthropic</a-option>
            <a-option value="custom">custom</a-option>
          </a-select>
        </div>
      </div>
      <template #footer>
        <a-button @click="dialogVisible = false">取消</a-button>
        <a-button type="primary" @click="onSave">保存</a-button>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import { useLlmStore, maskApiKey, type LlmProvider } from '@/stores/llm'
import { confirmDialog, toast } from '@/utils/feedback'

const store = useLlmStore()
const temperature = ref(0.7)
const useStream = ref(true)

const dialogVisible = ref(false)
const editing = ref(false)
const form = ref<LlmProvider>({
  name: '', base_url: '', api_key: '', model: '', provider_type: 'openai', options: {},
})

const canSend = computed(() =>
  store.selectedProvider && store.messages.some((m) => m.role === 'user' && m.content.trim()),
)

onMounted(() => store.loadProviders())

function openAdd() {
  editing.value = false
  form.value = { name: '', base_url: '', api_key: '', model: '', provider_type: 'openai', options: {} }
  dialogVisible.value = true
}

function openEdit(p: LlmProvider) {
  editing.value = true
  form.value = { ...p }
  dialogVisible.value = true
}

async function onSave() {
  try {
    if (editing.value) await store.updateProvider(form.value.name, form.value)
    else await store.addProvider(form.value)
    dialogVisible.value = false
    toast.success('保存成功')
  } catch (e) {
    toast.error((e as Error).message)
  }
}

async function onDelete(name: string) {
  const ok = await confirmDialog('确认', `删除 Provider '${name}'？`)
  if (!ok) return
  await store.deleteProvider(name)
  toast.success('已删除')
}

async function onSend() {
  const lastUser = [...store.messages].reverse().find((m) => m.role === 'user')
  if (!lastUser || !lastUser.content.trim()) return
  if (useStream.value) await store.chatStream(temperature.value)
  else await store.chatSync(temperature.value)
  store.messages.push({ role: 'user', content: '' })
}

function roleTag(role: string) {
  return role === 'user' ? 'blue' : role === 'assistant' ? 'green' : 'gray'
}
</script>

<style lang="less" scoped>
.llm-playground { display: flex; height: 100%; gap: 1px; background: var(--el-border-color); }
.panel { background: var(--el-bg-color); overflow: auto; display: flex; flex-direction: column; }
.provider-panel { width: 280px; flex-shrink: 0; }
.chat-panel { flex: 1; min-width: 0; padding: 8px; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--el-border-color); font-weight: 600; }
.provider-list { flex: 1; overflow-y: auto; }
.provider-item { padding: 10px 12px; border-bottom: 1px solid var(--el-border-color-lighter); cursor: pointer;
  &.active { background: var(--el-color-primary-light-9); }
  &:hover { background: var(--el-fill-color-light); }
}
.provider-name { font-weight: 600; display: flex; align-items: center; gap: 6px; }
.provider-model, .provider-key { font-size: 12px; color: var(--el-text-color-secondary); }
.chat-toolbar { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--el-border-color); }
.messages { flex: 1; overflow-y: auto; padding: 8px 0; }
.message { padding: 8px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.streaming-tip, .usage-tip { padding: 4px 0; color: var(--el-text-color-secondary); font-size: 12px; }
.error-box { color: var(--el-color-danger); padding: 8px; background: var(--el-color-danger-light-9); border-radius: 4px; margin: 8px 0; }
.empty-tip { display: flex; align-items: center; justify-content: center; height: 100%; }

.dialog-form {
  display: flex; flex-direction: column; gap: 12px;
  .form-row { display: flex; align-items: flex-start; gap: 12px;
    .form-label { width: 100px; flex-shrink: 0; padding-top: 4px; color: var(--el-text-color-primary); font-size: 13px; }
  }
}
</style>
