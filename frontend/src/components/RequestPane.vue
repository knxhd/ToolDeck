<template>
  <div class="request-pane">
    <div class="url-bar">
      <el-select v-model="tab.request.method" style="width: 110px">
        <el-option v-for="m in methods" :key="m" :label="m" :value="m" />
      </el-select>
      <el-input
        v-model="tab.request.url"
        placeholder="https://api.example.com/path"
        @keyup.enter="onSend"
      />
      <el-button v-if="!tab.streaming" type="primary" @click="onSend">发送</el-button>
      <el-button v-else type="danger" plain @click="$emit('cancel')">停止</el-button>
    </div>
    <el-tabs class="req-tabs">
      <el-tab-pane label="Params">
        <KeyValueEditor v-model="tab.request.params" />
      </el-tab-pane>
      <el-tab-pane label="Headers">
        <KeyValueEditor v-model="tab.request.headers" />
      </el-tab-pane>
      <el-tab-pane label="Body">
        <el-radio-group v-model="tab.request.body_type" style="margin-bottom: 8px">
          <el-radio-button value="none">none</el-radio-button>
          <el-radio-button value="json">JSON</el-radio-button>
          <el-radio-button value="raw">raw</el-radio-button>
          <el-radio-button value="form-data">form-data</el-radio-button>
        </el-radio-group>
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
        <el-empty v-else description="无 Body" :image-size="40" />
      </el-tab-pane>
    </el-tabs>
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
