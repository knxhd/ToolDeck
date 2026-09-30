<template>
  <div ref="containerRef" class="monaco-container" :class="{ 'is-fill': fill }"
    :style="fill ? undefined : { height }"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'

import { useSettingsStore } from '@/stores/settings'

const props = withDefaults(
  defineProps<{
    modelValue: string
    language?: string
    theme?: 'vs' | 'vs-dark'
    readOnly?: boolean
    height?: string
    fill?: boolean
    autoScrollToEnd?: boolean
    fontSize?: number
  }>(),
  {
    language: 'json',
    readOnly: false,
    height: '100%',
    fill: false,
    autoScrollToEnd: false,
  },
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const settings = useSettingsStore()
const containerRef = ref<HTMLDivElement | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null

function resolvedTheme(): 'vs' | 'vs-dark' {
  if (props.theme) return props.theme
  return settings.settings.dark ? 'vs-dark' : 'vs'
}

onMounted(() => {
  if (!containerRef.value) return
  editor = monaco.editor.create(containerRef.value, {
    value: props.modelValue,
    language: props.language,
    theme: resolvedTheme(),
    readOnly: props.readOnly,
    automaticLayout: true,
    minimap: { enabled: false },
    stickyScroll: { enabled: false },
    scrollBeyondLastLine: false,
    fontSize: props.fontSize || settings.settings.fontSize || 14,
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

watch(
  () => settings.settings.dark,
  (dark) => {
    monaco.editor.setTheme(props.theme ? props.theme : dark ? 'vs-dark' : 'vs')
  },
)

watch(
  () => [props.fontSize, settings.settings.fontSize],
  ([fs]) => {
    editor?.updateOptions({ fontSize: fs || settings.settings.fontSize || 14 })
  },
)

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

<style lang="less" scoped>
.monaco-container {
  width: 100%; min-height: 200px;
  border: 1px solid var(--el-border-color); border-radius: 4px;

  &.is-fill {
    flex: 1;
    min-height: 0;
    height: auto;
  }
}
</style>
