<template>
  <div class="llm-playground">
    <!-- 左：Provider 列表 -->
    <div class="panel provider-panel">
      <div class="panel-header">
        <span>Providers</span>
        <el-button size="small" type="primary" plain :icon="Plus" @click="openAdd">添加</el-button>
      </div>
      <div class="provider-list">
        <div
          v-for="p in store.providers"
          :key="p.name"
          class="provider-item"
          :class="{ active: store.selectedProvider === p.name }"
          @click="store.selectedProvider = p.name"
        >
          <div class="provider-name">{{ p.name }} <el-tag size="small">{{ p.provider_type }}</el-tag></div>
          <div class="provider-model">{{ p.model }}</div>
          <div class="provider-key">{{ maskApiKey(p.api_key) }}</div>
          <div class="provider-actions">
            <el-button size="small" link @click.stop="openEdit(p)">编辑</el-button>
            <el-button size="small" link type="danger" @click.stop="onDelete(p.name)">删除</el-button>
          </div>
        </div>
        <el-empty v-if="!store.providers.length" description="暂无 Provider" :image-size="60" />
      </div>
    </div>

    <!-- 右：聊天面板 -->
    <div class="panel chat-panel">
      <div v-if="!store.selectedProvider" class="empty-tip">
        <el-empty description="选择左侧 Provider 开始对话" />
      </div>
      <template v-else>
        <div class="chat-toolbar">
          <el-input-number v-model="temperature" :min="0" :max="2" :step="0.1" size="small" />
          <el-checkbox v-model="useStream">流式</el-checkbox>
          <el-button type="primary" :loading="store.streaming" :disabled="!canSend" @click="onSend">发送</el-button>
          <el-button @click="store.clearMessages">清空</el-button>
        </div>
        <div class="messages">
          <div v-for="(m, i) in store.messages" :key="i" class="message" :class="m.role">
            <el-tag size="small" :type="roleTag(m.role)">{{ m.role }}</el-tag>
            <MonacoEditor :model-value="m.content" :language="'plaintext'" read-only height="auto" auto-scroll-to-end />
          </div>
        </div>
        <div v-if="store.streaming" class="streaming-tip">生成中... {{ store.streamingText.length }} 字</div>
        <div v-if="store.streamInterrupted" class="error-box">已中断：{{ store.error }}</div>
        <div v-if="store.lastUsage" class="usage-tip">{{ store.lastUsage }}</div>
      </template>
    </div>

    <!-- 添加/编辑 Provider -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑 Provider' : '添加 Provider'" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="name"><el-input v-model="form.name" :disabled="editing" /></el-form-item>
        <el-form-item label="base_url"><el-input v-model="form.base_url" placeholder="https://api.deepseek.com" /></el-form-item>
        <el-form-item label="api_key"><el-input v-model="form.api_key" show-password /></el-form-item>
        <el-form-item label="model"><el-input v-model="form.model" placeholder="deepseek-chat" /></el-form-item>
        <el-form-item label="provider_type">
          <el-select v-model="form.provider_type">
            <el-option label="openai (Compatible)" value="openai" />
            <el-option label="anthropic" value="anthropic" />
            <el-option label="custom" value="custom" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import { useLlmStore, maskApiKey, type LlmProvider } from '@/stores/llm'

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
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onDelete(name: string) {
  await ElMessageBox.confirm(`删除 Provider '${name}'？`, '确认', { type: 'warning' })
  await store.deleteProvider(name)
  ElMessage.success('已删除')
}

async function onSend() {
  // 编辑最后一条 user 消息内容
  const lastUser = [...store.messages].reverse().find((m) => m.role === 'user')
  if (!lastUser || !lastUser.content.trim()) return
  if (useStream.value) await store.chatStream(temperature.value)
  else await store.chatSync(temperature.value)
  // 新增一条空的 user 消息用于下次输入
  store.messages.push({ role: 'user', content: '' })
}

function roleTag(role: string) {
  return role === 'user' ? 'primary' : role === 'assistant' ? 'success' : 'info'
}
</script>

<style scoped>
.llm-playground { display: flex; height: 100%; gap: 1px; background: var(--el-border-color); }
.panel { background: #fff; overflow: auto; display: flex; flex-direction: column; }
.provider-panel { width: 280px; flex-shrink: 0; }
.chat-panel { flex: 1; min-width: 0; padding: 8px; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--el-border-color); font-weight: 600; }
.provider-list { flex: 1; overflow-y: auto; }
.provider-item { padding: 10px 12px; border-bottom: 1px solid var(--el-border-color-lighter); cursor: pointer; }
.provider-item.active { background: var(--el-color-primary-light-9); }
.provider-item:hover { background: var(--el-fill-color-light); }
.provider-name { font-weight: 600; display: flex; align-items: center; gap: 6px; }
.provider-model, .provider-key { font-size: 12px; color: var(--el-text-color-secondary); }
.chat-toolbar { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--el-border-color); }
.messages { flex: 1; overflow-y: auto; padding: 8px 0; }
.message { padding: 8px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.streaming-tip, .usage-tip { padding: 4px 0; color: var(--el-text-color-secondary); font-size: 12px; }
.error-box { color: var(--el-color-danger); padding: 8px; background: var(--el-color-danger-light-9); border-radius: 4px; margin: 8px 0; }
.empty-tip { display: flex; align-items: center; justify-content: center; height: 100%; }
</style>
