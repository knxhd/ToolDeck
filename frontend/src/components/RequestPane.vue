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
      <a-button v-if="!tab.streaming" type="primary" @click="onSend">发送</a-button>
      <a-button v-else status="danger" type="secondary" @click="$emit('cancel')">停止</a-button>
    </div>
    <a-tabs class="req-tabs" :default-active-key="'params'">
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
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import KeyValueEditor from '@/components/KeyValueEditor.vue'
import type { HttpMethod, KeyValue, OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()
const emit = defineEmits<{ send: []; cancel: [] }>()

const methods: HttpMethod[] = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

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
</script>

<style lang="less" scoped>
.request-pane {
  display: flex; flex-direction: column; height: 100%;
  .url-bar { display: flex; gap: 8px; padding: 8px; border-bottom: 1px solid var(--el-border-color); }
  .req-tabs { flex: 1; overflow: auto; padding: 0 8px; }
}
</style>
