<template>
  <div class="doc-editor">
    <!-- 编辑区：Monaco Markdown 编辑器 -->
    <div v-show="mode !== 'preview'" class="doc-pane doc-edit">
      <MonacoEditor :model-value="modelValue" language="markdown" fill
        @update:model-value="emit('update:modelValue', $event)" />
    </div>
    <!-- 预览区：实时渲染 Markdown -->
    <div v-show="mode !== 'edit'" class="doc-pane doc-preview">
      <v-md-preview v-if="modelValue.trim()" :text="modelValue" />
      <div v-else class="doc-empty">暂无文档，切换到「编辑」或「分屏」使用 Markdown 编写此接口的说明</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import MonacoEditor from '@/components/MonacoEditor.vue'
import type { DocMode } from '@/api/types'

withDefaults(defineProps<{ modelValue: string; mode?: DocMode }>(), { mode: 'split' })
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<style lang="less" scoped>
.doc-editor {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 8px;
  padding-bottom: 4px;
}

.doc-pane {
  flex: 1 1 0;
  min-width: 0;
  min-height: 0;
}

.doc-edit {
  display: flex;
  flex-direction: column;
}

.doc-preview {
  overflow-y: auto;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;

  :deep(.github-markdown-body) {
    padding: 12px 16px;
    background: transparent;
  }
}

.doc-empty {
  padding: 16px;
  font-size: 13px;
  color: var(--el-text-color-placeholder);
}
</style>
