<template>
  <div ref="containerRef" class="monaco-container" :class="{ 'is-fill': fill }"
    :style="fill ? undefined : { height }"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'

import { useSettingsStore } from '@/stores/settings'
import { PLACEHOLDER_SOURCE } from '@/utils/env'
import { varHoverMarkdown } from '@/utils/varInfo'
import type { VarResolver } from '@/utils/varInfo'

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
    /** 传入后高亮 {{var}} 占位符，并在悬停时显示变量值 / 内置占位符说明 */
    varResolver?: VarResolver
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
    scheduleVarDecorations()
    if (props.autoScrollToEnd && editor) {
      const model = editor.getModel()
      if (model) {
        const lastLine = model.getLineCount()
        editor.revealLineInCenter(lastLine)
      }
    }
  })
  refreshVarDecorations()
})

// ---- 占位符高亮 + 悬停说明 ----
const MAX_VAR_DECORATIONS = 2000
let varDecorations: monaco.editor.IEditorDecorationsCollection | null = null
let varTimer: number | null = null

function scheduleVarDecorations() {
  if (!props.varResolver) return
  if (varTimer) clearTimeout(varTimer)
  varTimer = window.setTimeout(() => {
    varTimer = null
    refreshVarDecorations()
  }, 60)
}

function refreshVarDecorations() {
  const model = editor?.getModel()
  if (!editor || !model) return
  const resolver = props.varResolver
  if (!resolver) {
    varDecorations?.clear()
    return
  }
  const text = model.getValue()
  const list: monaco.editor.IModelDeltaDecoration[] = []
  for (const m of text.matchAll(new RegExp(PLACEHOLDER_SOURCE, 'g'))) {
    if (list.length >= MAX_VAR_DECORATIONS) break
    const idx = m.index ?? 0
    const start = model.getPositionAt(idx)
    const end = model.getPositionAt(idx + m[0].length)
    const info = resolver(m[1])
    const cls = !info.source
      ? 'monaco-var monaco-var-missing'
      : info.source === 'Built-in'
        ? 'monaco-var monaco-var-builtin'
        : 'monaco-var'
    list.push({
      range: new monaco.Range(start.lineNumber, start.column, end.lineNumber, end.column),
      options: {
        inlineClassName: cls,
        hoverMessage: { value: varHoverMarkdown(info) },
        stickiness: monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges,
      },
    })
  }
  if (varDecorations) varDecorations.set(list)
  else varDecorations = editor.createDecorationsCollection(list)
}

// 变量表（环境切换、占位符修改）变化时刷新高亮与提示
watch(
  () => props.varResolver,
  () => refreshVarDecorations(),
)

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
  if (varTimer) clearTimeout(varTimer)
  varDecorations?.clear()
  varDecorations = null
  editor?.dispose()
  editor = null
})
</script>

<!-- 占位符高亮作用于 Monaco 内部 DOM，必须用全局样式；配色与 URL 输入框保持一致 -->
<style lang="less">
.monaco-editor .monaco-var {
  background: rgba(255, 176, 32, 0.22);
  color: #d48806 !important;
  border-radius: 3px;
  cursor: help;

  &.monaco-var-builtin {
    background: rgba(22, 93, 255, 0.14);
    color: rgb(var(--primary-6)) !important;
  }

  &.monaco-var-missing {
    background: rgba(245, 63, 63, 0.18);
    color: #f53f3f !important;
  }
}
</style>

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
