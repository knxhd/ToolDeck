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
.llm-playground {
  display: flex;
  gap: 6px;
  height: 100%;
  padding: 6px;
  background: var(--ui-bg-canvas);
}

.panel {
  display: flex;
  flex-direction: column;
  overflow: auto;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
  background: var(--ui-bg-panel);
}

.provider-panel {
  width: 292px;
  flex-shrink: 0;
}

.chat-panel {
  flex: 1;
  min-width: 0;
  padding: 0 12px 10px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  height: 44px;
  padding: 0 12px;
  border-bottom: 1px solid var(--ui-border-soft);
  color: var(--color-text-2);
  font-size: 12.5px;
  font-weight: 600;

  :deep(.arco-btn) {
    height: 26px;
    padding: 0 10px;
    border-radius: var(--ui-radius-sm);
    font-size: 12px;
  }
}

.provider-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px;
}

.provider-item {
  margin-bottom: 2px;
  padding: 8px 9px;
  border-radius: var(--ui-radius-md);
  cursor: pointer;
  transition: background-color 0.12s ease, box-shadow 0.12s ease;

  &:hover {
    background: var(--ui-bg-hover);
  }

  &.active {
    background: var(--ui-bg-active);
    box-shadow: inset 3px 0 0 rgb(var(--primary-6));

    .provider-name {
      color: rgb(var(--primary-6));
    }
  }
}

.provider-name {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-1);
  font-size: 12.5px;
  font-weight: 600;
}

.provider-model,
.provider-key {
  margin-top: 2px;
  color: var(--color-text-4);
  font-family: var(--ui-font-mono);
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.provider-actions {
  display: flex;
  gap: 2px;
  margin-top: 4px;

  :deep(.arco-btn) {
    height: 22px;
    padding: 0 6px;
    border-radius: var(--ui-radius-sm);
    font-size: 11.5px;
  }
}

.chat-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  height: 46px;
  border-bottom: 1px solid var(--ui-border-soft);

  :deep(.arco-btn) {
    height: 26px;
    padding: 0 12px;
    border-radius: var(--ui-radius-sm);
    font-size: 12px;
  }
}

.messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px 0;
}

.message {
  padding: 8px 10px;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);

  &.user {
    border-left: 3px solid rgb(var(--primary-6));
  }

  &.assistant {
    border-left: 3px solid var(--ui-accent-ok);
  }

  &:deep(.arco-tag) {
    margin-bottom: 6px;
  }
}

.streaming-tip,
.usage-tip {
  padding: 4px 0;
  color: var(--color-text-4);
  font-family: var(--ui-font-mono);
  font-size: 11.5px;
}

.error-box {
  margin: 8px 0;
  padding: 8px 10px;
  border: 1px solid rgba(220, 70, 64, 0.28);
  border-left: 3px solid var(--ui-accent-danger);
  border-radius: var(--ui-radius-md);
  background: var(--ui-accent-danger-bg);
  color: var(--ui-accent-danger);
  font-size: 12px;
}

.empty-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 14px;

  .form-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;

    .form-label {
      width: 96px;
      flex-shrink: 0;
      padding-top: 5px;
      color: var(--color-text-2);
      font-family: var(--ui-font-mono);
      font-size: 12px;
    }
  }
}
</style>
