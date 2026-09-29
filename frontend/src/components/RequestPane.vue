<template>
  <div class="request-pane">
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
          fill
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
import { computed, ref } from 'vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import KeyValueEditor from '@/components/KeyValueEditor.vue'
import type { KeyValue, OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()

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
</script>

<style lang="less" scoped>
.request-pane {
  display: flex;
  flex-direction: column;
  height: 100%;

  .req-tabs {
    flex: 1;
    min-height: 0;
    padding: 0 8px;
    display: flex;
    flex-direction: column;

    :deep(.arco-tabs-nav) {
      flex-shrink: 0;
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
    }
  }
}
</style>
