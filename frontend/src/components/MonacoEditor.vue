<template>
  <div ref="containerRef" class="monaco-container" :style="{ height: height }"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'

const props = withDefaults(
  defineProps<{
    modelValue: string
    language?: string
    theme?: 'vs' | 'vs-dark'
    readOnly?: boolean
    height?: string
    autoScrollToEnd?: boolean
  }>(),
  {
    language: 'json',
    theme: 'vs',
    readOnly: false,
    height: '100%',
    autoScrollToEnd: false,
  },
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const containerRef = ref<HTMLDivElement | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null

onMounted(() => {
  if (!containerRef.value) return
  editor = monaco.editor.create(containerRef.value, {
    value: props.modelValue,
    language: props.language,
    theme: props.theme,
    readOnly: props.readOnly,
    automaticLayout: true,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    fontSize: 13,
    tabSize: 2,
    wordWrap: 'on',
  })
  editor.onDidChangeModelContent(() => {
    emit('update:modelValue', editor!.getValue())
    if (props.autoScrollToEnd && editor) {
      const model = editor.getModel()
      if (model) {
        const lastLine = model.getLineCount()
        editor.revealLineInCenter(lastLine)
      }
    }
  })
})

watch(
  () => props.modelValue,
  (val) => {
    if (editor && val !== editor.getValue()) {
      editor.setValue(val)
    }
  },
)

watch(
  () => props.language,
  (lang) => {
    if (editor) monaco.editor.setModelLanguage(editor.getModel()!, lang)
  },
)

/** 增量追加文本到末尾。 */
function appendText(text: string) {
  if (!editor) return
  const model = editor.getModel()
  if (!model) return
  const lines = model.getLineCount()
  const lastCol = model.getLineMaxColumn(lines)
  model.applyEdits([
    {
      range: new monaco.Range(lines, lastCol, lines, lastCol),
      text,
    },
  ])
  if (props.autoScrollToEnd) {
    editor.revealLineInCenter(model.getLineCount())
  }
}

defineExpose({ appendText, editor: () => editor })

onBeforeUnmount(() => {
  editor?.dispose()
  editor = null
})
</script>

<style scoped>
.monaco-container {
  width: 100%;
  min-height: 200px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}
</style>
