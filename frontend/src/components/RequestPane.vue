<template>
  <div class="request-pane">
    <div class="url-bar">
      <a-select v-model="tab.request.method" style="width: 110px">
        <a-option v-for="m in methods" :key="m" :value="m">{{ m }}</a-option>
      </a-select>
      <a-input
        v-model="tab.request.url"
        placeholder="https://api.example.com/path"
        allow-clear
        @press-enter="onSend"
      />
      <a-button @click="curlDialogVisible = true">导入 curl</a-button>
      <a-button v-if="!tab.streaming" type="primary" @click="onSend">发送</a-button>
      <a-button v-else status="danger" type="secondary" @click="$emit('cancel')">停止</a-button>
    </div>
    <a-tabs v-model:active-key="activeKey" class="req-tabs">
      <a-tab-pane key="params" title="Params">
        <KeyValueEditor v-model="tab.request.params" />
      </a-tab-pane>
      <a-tab-pane key="headers" title="Headers">
        <KeyValueEditor v-model="tab.request.headers" />
      </a-tab-pane>
      <a-tab-pane key="body" title="Body">
        <a-radio-group v-model="tab.request.body_type" type="button" style="margin-bottom: 8px">
          <a-radio value="none">none</a-radio>
          <a-radio value="json">JSON</a-radio>
          <a-radio value="raw">raw</a-radio>
          <a-radio value="form-data">form-data</a-radio>
        </a-radio-group>
        <MonacoEditor
          v-if="tab.request.body_type !== 'none' && tab.request.body_type !== 'form-data'"
          v-model="tab.request.body"
          :language="tab.request.body_type === 'json' ? 'json' : 'plaintext'"
          height="220px"
        />
        <KeyValueEditor
          v-else-if="tab.request.body_type === 'form-data'"
          :model-value="formPairs"
          @update:model-value="onFormChange"
        />
        <a-empty v-else description="无 Body" style="padding: 12px 0" />
      </a-tab-pane>
    </a-tabs>

    <!-- 从 curl 导入 -->
    <a-modal v-model:visible="curlDialogVisible" title="从 curl 导入" width="640px">
      <a-textarea
        v-model="curlText"
        :auto-size="{ minRows: 10, maxRows: 18 }"
        placeholder="粘贴 curl 命令，例如：&#10;curl -X POST 'https://api.example.com/v1/chat' \&#10;  -H 'Content-Type: application/json' \&#10;  -d '{&quot;model&quot;:&quot;gpt&quot;}'"
      />
      <template #footer>
        <a-button @click="curlDialogVisible = false">取消</a-button>
        <a-button type="primary" @click="applyCurl">解析导入</a-button>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import KeyValueEditor from '@/components/KeyValueEditor.vue'
import { parseCurl } from '@/utils/parseCurl'
import { toast } from '@/utils/feedback'
import type { HttpMethod, KeyValue, OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()
const emit = defineEmits<{ send: []; cancel: []; save: [] }>()

const methods: HttpMethod[] = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

const curlDialogVisible = ref(false)
const curlText = ref('')

/** 是否已有实际 body 内容（用于决定默认打开的 tab）。 */
const hasBody = computed(() => {
  const r = props.tab.request
  if (r.body_type === 'none') return false
  if (r.body_type === 'form-data') {
    try {
      const arr = JSON.parse(r.body || '[]')
      return arr.some((i: { key?: string; value?: string }) => i && (i.key || i.value))
    } catch {
      return false
    }
  }
  return !!r.body?.trim()
})

/** 打开请求时按实际情况选默认 tab：有 body 进 Body，否则进 Params。 */
const activeKey = ref(hasBody.value ? 'body' : 'params')

const formPairs = computed<KeyValue[]>(() => {
  try {
    const arr = JSON.parse(props.tab.request.body || '[]')
    return arr.map((i: { key: string; value: string }) => ({ key: i.key, value: i.value, enabled: true }))
  } catch {
    return []
  }
})

function onFormChange(pairs: KeyValue[]) {
  props.tab.request.body = JSON.stringify(pairs.map((p) => ({ key: p.key, value: p.value })))
}

function onSend() {
  emit('send')
}

function applyCurl() {
  try {
    const parsed = parseCurl(curlText.value)
    if (!parsed.url) {
      toast.warning('未识别到 URL，请检查 curl 命令')
      return
    }
    const r = props.tab.request
    r.method = parsed.method as HttpMethod
    r.url = parsed.url
    r.headers = parsed.headers.length ? parsed.headers : [{ key: '', value: '', enabled: true }]
    r.params = parsed.params.length ? parsed.params : [{ key: '', value: '', enabled: true }]
    r.body_type = parsed.bodyType
    r.body = parsed.body
    // 导入后按实际情况切 tab：有 body 进 Body，否则回 Params
    activeKey.value = parsed.bodyType !== 'none' ? 'body' : 'params'
    curlDialogVisible.value = false
    curlText.value = ''
    emit('save')
    toast.success('已从 curl 导入')
  } catch (e) {
    toast.error('解析失败：' + (e as Error).message)
  }
}
</script>

<style lang="less" scoped>
.request-pane {
  display: flex; flex-direction: column; height: 100%;
  .url-bar { display: flex; gap: 8px; padding: 8px; border-bottom: 1px solid var(--el-border-color); }
  .req-tabs { flex: 1; overflow: auto; padding: 0 8px; }
}
</style>
