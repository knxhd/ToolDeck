<template>
  <div class="single-data-view">
    <div class="body-toolbar">
      <a-select v-model="formatType" size="mini" style="width: 110px">
        <a-option value="text">Text</a-option>
        <a-option value="json">JSON</a-option>
        <a-option value="html">HTML</a-option>
      </a-select>
      <span class="toolbar-spacer" />
      <a-tooltip content="复制响应体" position="top">
        <a-button size="mini" type="text" @click="copyBody">
          <template #icon><icon-copy /></template>
        </a-button>
      </a-tooltip>
      <a-tooltip content="在响应中查找" position="top">
        <a-button size="mini" type="text" @click="openFind">
          <template #icon><icon-search /></template>
        </a-button>
      </a-tooltip>
    </div>
    <div class="body-view">
      <MonacoEditor
        ref="monacoRef"
        v-if="formatType !== 'html'"
        :model-value="rendered(data)"
        :language="formatType === 'json' ? 'json' : 'plaintext'"
        read-only
        fill
      />
      <iframe v-else class="html-frame" :srcdoc="data" sandbox=""></iframe>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { toast } from '@/utils/feedback'
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
const monacoRef = ref<InstanceType<typeof MonacoEditor> | null>(null)

const rendered = (raw: string) => {
  if (formatType.value !== 'json' || !raw) return raw || ''
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}

async function copyBody() {
  const text = props.data || ''
  try {
    await navigator.clipboard.writeText(text)
    toast.success('已复制')
  } catch {
    toast.error('复制失败')
  }
}

function openFind() {
  const ed = monacoRef.value?.editor?.()
  ed?.focus()
  ed?.trigger('keyboard', 'actions.find', undefined)
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
  gap: 4px;
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

.toolbar-spacer {
  flex: 1;
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
