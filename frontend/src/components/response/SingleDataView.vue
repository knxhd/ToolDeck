<template>
  <div class="single-data-view">
    <div class="body-toolbar">
      <a-select v-model="formatType" size="mini" style="width: 110px">
        <a-option value="text">Text</a-option>
        <a-option value="json">JSON</a-option>
        <a-option value="html">HTML</a-option>
      </a-select>
    </div>
    <div class="body-view">
      <MonacoEditor v-if="formatType !== 'html'" :model-value="rendered(data)"
        :language="formatType === 'json' ? 'json' : 'plaintext'" read-only fill />
      <iframe v-else class="html-frame" :srcdoc="data" sandbox=""></iframe>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MonacoEditor from '@/components/MonacoEditor.vue'

const props = defineProps({
  data: {
    type: String,
    required: true
  },
  defaultFormat: {
    type: String,
    default: 'json'
  },
})

const formatType = ref(props.defaultFormat)

const rendered = (raw: string) => {
  if (formatType.value !== 'json' || !raw) return raw || ''
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}
</script>

<style scoped lang="less">
.single-data-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.body-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  height: 30px;
  padding: 0 0 6px;

  :deep(.arco-select-view) {
    height: 24px;
    border-radius: var(--ui-radius-sm);
    background: var(--ui-bg-subtle);
    font-family: var(--ui-font-mono);
    font-size: 11.5px;
  }
}

.body-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: auto;
  border-radius: var(--ui-radius-md);

  .html-frame {
    width: 100%;
    height: 100%;
    border: 1px solid var(--ui-border);
    border-radius: var(--ui-radius-md);
    background: #fff;
  }
}
</style>
