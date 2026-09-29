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
  gap: 12px;
  padding: 2px 0 6px;
  flex-shrink: 0;
}

.body-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: auto;

  .html-frame {
    width: 100%;
    height: 100%;
    border: 1px solid var(--el-border-color);
    border-radius: 4px;
    background: #fff;
  }
}
</style>
