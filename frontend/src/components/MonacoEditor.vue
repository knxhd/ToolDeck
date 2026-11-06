<template>
  <div ref="containerRef" class="monaco-container" :class="{ 'is-fill': fill }"
    :style="fill ? undefined : { height }"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'

import { useSettingsStore } from '@/stores/settings'
import { accentBase } from '@/utils/theme'
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

// ---- 编辑器主题：与设计令牌 / 当前配色保持一致 ----
const THEME_LIGHT_KEY = 'tooldeck-light'
const THEME_DARK_KEY = 'tooldeck-dark'

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const n = parseInt(full, 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

/** 把半透明前景色混合到背景上，得到 Monaco 能直接使用的实色。 */
function blend(fg: string, bg: string, alpha: number): string {
  const [r1, g1, b1] = hexToRgb(fg)
  const [r2, g2, b2] = hexToRgb(bg)
  const mix = (a: number, b: number) => Math.round(a * alpha + b * (1 - alpha))
  return `#${[mix(r1, r2), mix(g1, g2), mix(b1, b2)]
    .map((v) => v.toString(16).padStart(2, '0'))
    .join('')}`
}

/** 读取 body 上定义的颜色令牌；只接受 #hex，其他形式（rgb/rgba）回退到默认值。 */
function readColor(name: string, fallback: string): string {
  const v = getComputedStyle(document.body).getPropertyValue(name).trim()
  return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(v) ? v : fallback
}

function defineThemes() {
  const accent = accentBase(settings.settings.accent)
  const dark = settings.settings.dark
  // 背景取主题的卡片色，让编辑器跟着 10 套主题一起变
  const bg = readColor('--ui-bg-panel', dark ? '#161a22' : '#ffffff')
  const subtle = readColor('--ui-bg-subtle', dark ? '#1d222c' : '#f7f8fa')
  const mixBase = dark ? '#ffffff' : '#000000'
  const darkBg = bg
  monaco.editor.defineTheme(THEME_DARK_KEY, {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '6b7689', fontStyle: 'italic' },
      { token: 'string', foreground: '8fd18b' },
      { token: 'number', foreground: 'e0af68' },
      { token: 'keyword', foreground: '7aa2f7' },
      { token: 'type', foreground: 'bb9af7' },
      { token: 'delimiter', foreground: '8b96a8' },
      { token: 'tag', foreground: '7aa2f7' },
      { token: 'attribute.name', foreground: 'e0af68' },
    ],
    colors: {
      'editor.background': darkBg,
      'editor.foreground': '#c9d1e0',
      'editorCursor.foreground': accent,
      'editor.lineHighlightBackground': blend(mixBase, darkBg, 0.05),
      'editor.selectionBackground': blend(accent, darkBg, 0.34),
      'editor.inactiveSelectionBackground': blend(accent, darkBg, 0.18),
      'editorLineNumber.foreground': blend(mixBase, darkBg, 0.26),
      'editorLineNumber.activeForeground': blend(mixBase, darkBg, 0.5),
      'editorIndentGuide.background1': blend(mixBase, darkBg, 0.09),
      'editorIndentGuide.activeBackground1': blend(mixBase, darkBg, 0.18),
      'editorWidget.background': subtle,
      'editorWidget.border': blend(mixBase, subtle, 0.14),
      'editorSuggestWidget.background': subtle,
      'editorSuggestWidget.selectedBackground': blend(accent, darkBg, 0.34),
      'editorHoverWidget.background': subtle,
      'editorHoverWidget.border': blend(mixBase, subtle, 0.14),
      'scrollbarSlider.background': '#ffffff1f',
      'scrollbarSlider.hoverBackground': '#ffffff2e',
      'editorGutter.background': darkBg,
    },
  })

  const lightBg = bg
  monaco.editor.defineTheme(THEME_LIGHT_KEY, {
    base: 'vs',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '9aa3b2', fontStyle: 'italic' },
      { token: 'string', foreground: '1a9b64' },
      { token: 'number', foreground: 'b46b00' },
      { token: 'keyword', foreground: '2f6fd0' },
      { token: 'type', foreground: '7c4dd1' },
    ],
    colors: {
      'editor.background': lightBg,
      'editor.foreground': '#333a47',
      'editorCursor.foreground': accent,
      'editor.lineHighlightBackground': blend(mixBase, lightBg, 0.035),
      'editor.selectionBackground': blend(accent, lightBg, 0.18),
      'editor.inactiveSelectionBackground': blend(accent, lightBg, 0.1),
      'editorLineNumber.foreground': blend(mixBase, lightBg, 0.28),
      'editorLineNumber.activeForeground': blend(mixBase, lightBg, 0.55),
      'editorIndentGuide.background1': blend(mixBase, lightBg, 0.06),
      'editorIndentGuide.activeBackground1': blend(mixBase, lightBg, 0.14),
      'editorWidget.background': subtle,
      'editorWidget.border': blend(mixBase, subtle, 0.12),
      'editorSuggestWidget.selectedBackground': blend(accent, lightBg, 0.12),
      'editorHoverWidget.background': subtle,
      'editorHoverWidget.border': blend(mixBase, subtle, 0.12),
      'scrollbarSlider.background': '#0000001a',
      'scrollbarSlider.hoverBackground': '#00000029',
    },
  })
}

function resolvedTheme(): string {
  if (props.theme) return props.theme
  const dark = settings.settings.dark
  return dark ? THEME_DARK_KEY : THEME_LIGHT_KEY
}

onMounted(() => {
  if (!containerRef.value) return
  defineThemes()
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
    fontFamily: settings.settings.fontFamily,
    tabSize: 2,
    wordWrap: 'on',
    scrollbar: {
      verticalScrollbarSize: 10,
      horizontalScrollbarSize: 10,
      useShadows: false,
    },
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
  () => [settings.settings.theme, settings.settings.accent],
  () => {
    // 主题 / 配色变化：重算背景色、光标与选区
    defineThemes()
    if (!props.theme) monaco.editor.setTheme(resolvedTheme())
  },
)

watch(
  () => [props.fontSize, settings.settings.fontSize, settings.settings.fontFamily] as const,
  ([propSize, settingSize, fontFamily]) => {
    editor?.updateOptions({
      fontSize: propSize || settingSize || 14,
      fontFamily: fontFamily || undefined,
    })
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
  background: rgba(212, 136, 6, 0.16);
  color: #d48806 !important;
  border-radius: 3px;
  cursor: help;

  &.monaco-var-builtin {
    background: rgba(var(--primary-6), 0.16);
    color: rgb(var(--primary-6)) !important;
  }

  &.monaco-var-missing {
    background: rgba(220, 70, 64, 0.16);
    color: #dc4640 !important;
  }
}

body[arco-theme='dark'] .monaco-editor .monaco-var {
  background: rgba(232, 163, 61, 0.2);
  color: #e8a33d !important;

  &.monaco-var-builtin {
    background: rgba(var(--primary-6), 0.24);
    color: rgb(var(--primary-6)) !important;
  }

  &.monaco-var-missing {
    background: rgba(242, 117, 111, 0.22);
    color: #f2756f !important;
  }
}

/* 统一 Monaco 滚动条样式，与全局 10px 滚动条一致 */
.monaco-editor .monaco-scrollable-element > .scrollbar {
  width: 10px !important;
  height: 10px !important;
}
.monaco-editor .monaco-scrollable-element > .scrollbar > .slider {
  border-radius: 5px !important;
  border: 2px solid transparent !important;
  background-clip: content-box !important;
}
.monaco-editor .monaco-scrollable-element > .scrollbar > .slider:hover {
  background-clip: content-box !important;
}
</style>

<style lang="less" scoped>
.monaco-container {
  width: 100%;
  min-height: 200px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  /* overflow: hidden; */

  &.is-fill {
    flex: 1;
    min-height: 0;
    height: auto;
  }
}
</style>
