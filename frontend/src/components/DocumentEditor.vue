<template>
  <!-- 全屏时传送到 body，避免受祖先元素 overflow / transform 影响；组件实例与编辑器状态保持不变 -->
  <Teleport to="body" :disabled="!fullscreen">
  <div class="doc-editor" :class="{ 'is-fullscreen': fullscreen }">
    <div v-if="fullscreen" class="doc-fs-header">
      <span class="doc-fs-title">{{ title || '接口文档' }}</span>
      <a-radio-group :model-value="mode" type="button" size="small"
        @change="emit('update:mode', $event as DocMode)">
        <a-radio value="edit">编辑</a-radio>
        <a-radio value="split">分屏</a-radio>
        <a-radio value="preview">预览</a-radio>
      </a-radio-group>
      <a-button size="small" type="text" title="退出全屏 (Esc)" @click="emit('update:fullscreen', false)">
        <template #icon><icon-fullscreen-exit /></template>
        退出全屏
      </a-button>
    </div>
    <div class="doc-body">
    <!-- 编辑区：Markdown 工具栏 + Monaco 编辑器 -->
    <div v-show="mode !== 'preview'" class="doc-pane doc-edit">
      <div class="md-toolbar">
        <template v-for="(group, gi) in toolbarGroups" :key="gi">
          <span v-if="gi" class="md-divider"></span>
          <template v-for="btn in group" :key="btn.key">
            <!-- 表格：点击弹出网格选择行列数 -->
            <a-popover v-if="btn.key === 'table'" v-model:popup-visible="tablePickerOpen" trigger="click"
              position="bl">
              <button type="button" class="md-btn" :title="btn.title" @mousedown.prevent>
                <svg class="md-svg" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="4">
                  <rect x="6" y="8" width="36" height="32" rx="2" />
                  <path d="M6 18h36M6 29h36M18 18v22M30 18v22" />
                </svg>
              </button>
              <template #content>
                <div class="tbl-picker" @mouseleave="resetHover">
                  <div v-for="r in PICKER_ROWS" :key="r" class="tbl-row">
                    <span v-for="c in PICKER_COLS" :key="c" class="tbl-cell"
                      :class="{ active: r <= hoverRows && c <= hoverCols }"
                      @mouseenter="setHover(r, c)" @mousedown.prevent @click="insertTable(r, c)"></span>
                  </div>
                  <div class="tbl-label">
                    {{ hoverCols ? `${hoverCols} 列 × ${hoverRows} 行（另含表头）` : '选择表格大小' }}
                  </div>
                </div>
              </template>
            </a-popover>
            <button v-else type="button" class="md-btn" :title="btn.title" @mousedown.prevent @click="btn.action()">
              <component :is="btn.icon" />
            </button>
          </template>
        </template>
      </div>
      <MonacoEditor ref="editorRef" :model-value="modelValue" language="markdown" fill
        @update:model-value="emit('update:modelValue', $event)" />
    </div>
    <!-- 预览区：实时渲染 Markdown -->
    <div v-show="mode !== 'edit'" class="doc-pane doc-preview">
      <v-md-preview v-if="modelValue.trim()" :text="modelValue" />
      <div v-else class="doc-empty">暂无文档，切换到「编辑」或「分屏」使用 Markdown 编写此接口的说明</div>
    </div>
    </div>
  </div>
  </Teleport>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'

import MonacoEditor from '@/components/MonacoEditor.vue'
import type { DocMode } from '@/api/types'

const props = withDefaults(
  defineProps<{ modelValue: string; mode?: DocMode; fullscreen?: boolean; title?: string }>(),
  { mode: 'split', fullscreen: false, title: '' },
)
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:mode': [value: DocMode]
  'update:fullscreen': [value: boolean]
}>()

// ---- 全屏：Esc 退出（编辑器已处理的 Esc，如关闭补全弹窗，会 preventDefault，此时不退出）----
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && !e.defaultPrevented) emit('update:fullscreen', false)
}

watch(
  () => props.fullscreen,
  (on) => {
    if (on) window.addEventListener('keydown', onKeydown)
    else window.removeEventListener('keydown', onKeydown)
    // 切换后把焦点还给编辑器，便于继续输入
    setTimeout(() => editorRef.value?.editor()?.focus(), 0)
  },
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

const editorRef = ref<InstanceType<typeof MonacoEditor> | null>(null)

interface Ctx {
  ed: monaco.editor.IStandaloneCodeEditor
  model: monaco.editor.ITextModel
  sel: monaco.Selection
}

function ctx(): Ctx | null {
  const ed = editorRef.value?.editor() ?? null
  const model = ed?.getModel()
  const sel = ed?.getSelection()
  if (!ed || !model || !sel) return null
  return { ed, model, sel }
}

/** 从 (line, col) 开始写入文本 s 后的结束位置。 */
function advance(line: number, col: number, s: string): { line: number; col: number } {
  const parts = s.split('\n')
  if (parts.length === 1) return { line, col: col + s.length }
  return { line: line + parts.length - 1, col: parts[parts.length - 1].length + 1 }
}

/** 执行编辑（单独一个撤销步），可选设置编辑后的选区。 */
function apply(c: Ctx, edits: Array<{ range: monaco.IRange; text: string }>, selection?: monaco.Selection) {
  c.ed.pushUndoStop()
  c.ed.executeEdits(
    'md-toolbar',
    edits.map((e) => ({ ...e, forceMoveMarkers: true })),
    selection ? [selection] : undefined,
  )
  c.ed.pushUndoStop()
  c.ed.focus()
}

/** 在选区内插入 before + inner + after，并选中 inner 中 [selStart, selEnd) 的部分。 */
function replaceSelection(text: string, selStart = text.length, selEnd = selStart) {
  const c = ctx()
  if (!c) return
  const { startLineNumber: l, startColumn: col } = c.sel
  const a = advance(l, col, text.slice(0, selStart))
  const b = advance(l, col, text.slice(0, selEnd))
  apply(c, [{ range: c.sel, text }], new monaco.Selection(a.line, a.col, b.line, b.col))
}

/** 行内包裹：**粗体**、*斜体*、~~删除线~~、`代码`；已包裹时再次点击取消。 */
function wrap(marker: string, placeholder: string) {
  const c = ctx()
  if (!c) return
  const text = c.model.getValueInRange(c.sel)
  const m = marker.length
  if (text.length >= m * 2 && text.startsWith(marker) && text.endsWith(marker)) {
    const inner = text.slice(m, text.length - m)
    replaceSelection(inner, 0, inner.length)
    return
  }
  const inner = text || placeholder
  replaceSelection(`${marker}${inner}${marker}`, m, m + inner.length)
}

/** 选中行逐行加 / 去前缀：标题、引用、列表。 */
function linePrefix(kind: 'heading' | 'quote' | 'ul' | 'ol' | 'task', level = 1) {
  const c = ctx()
  if (!c) return
  let { startLineNumber: start, endLineNumber: end } = c.sel
  if (end > start && c.sel.endColumn === 1) end -= 1
  const patterns: Record<typeof kind, RegExp> = {
    heading: /^#{1,6}\s+/,
    quote: /^>\s?/,
    ul: /^[-*+]\s+(?!\[[ xX]\])/,
    ol: /^\d+\.\s+/,
    task: /^[-*+]\s+\[[ xX]\]\s+/,
  }
  const re = patterns[kind]
  const lines: string[] = []
  for (let i = start; i <= end; i++) lines.push(c.model.getLineContent(i))
  const prefixOf = (idx: number) =>
    kind === 'heading' ? `${'#'.repeat(level)} `
      : kind === 'quote' ? '> '
        : kind === 'ul' ? '- '
          : kind === 'ol' ? `${idx + 1}. `
            : '- [ ] '
  // 所有行都已是该格式（标题需同级）时整体取消，否则统一加上
  const allHave = lines.every((t, idx) => (kind === 'heading' ? t.startsWith(prefixOf(idx)) : re.test(t)))
  const edits = lines.map((t, idx) => {
    const stripped = t.replace(re, '')
    return {
      range: new monaco.Range(start + idx, 1, start + idx, t.length + 1),
      text: allHave ? stripped : prefixOf(idx) + stripped,
    }
  })
  apply(c, edits)
}

/** 在当前行之后插入独立的块（表格、代码块、分隔线），与上下文之间保留空行；选中块内 [selStart, selEnd)。 */
function insertBlock(block: string, selStart = block.length, selEnd = selStart) {
  const c = ctx()
  if (!c) return
  const lineNo = c.sel.endLineNumber
  const line = c.model.getLineContent(lineNo)
  const col = line.length + 1
  const lead = line.trim() ? '\n\n' : ''
  // 插入点在行尾，原有换行仍在其后，再补一个换行即可与后文空一行
  const text = lead + block + '\n'
  const base = advance(lineNo, col, lead)
  const a = advance(base.line, base.col, block.slice(0, selStart))
  const b = advance(base.line, base.col, block.slice(0, selEnd))
  apply(c, [{ range: new monaco.Range(lineNo, col, lineNo, col), text }], new monaco.Selection(a.line, a.col, b.line, b.col))
}

function insertLink(image = false) {
  const c = ctx()
  if (!c) return
  const sel = c.model.getValueInRange(c.sel)
  const bang = image ? '!' : ''
  if (sel) {
    const text = `${bang}[${sel}](https://)`
    const urlStart = bang.length + sel.length + 3
    replaceSelection(text, urlStart, urlStart + 'https://'.length)
  } else {
    const label = image ? '图片描述' : '链接文字'
    replaceSelection(`${bang}[${label}](https://)`, bang.length + 1, bang.length + 1 + label.length)
  }
}

function insertCodeBlock() {
  const c = ctx()
  if (!c) return
  const sel = c.model.getValueInRange(c.sel)
  if (sel) {
    replaceSelection('```json\n' + sel + '\n```', 3, 7)
  } else {
    insertBlock('```json\n\n```', 3, 7)
  }
}

function insertHr() {
  insertBlock('---')
}

function insertDateTime() {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  replaceSelection(`${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`)
}

function trigger(cmd: 'undo' | 'redo') {
  const ed = editorRef.value?.editor()
  if (!ed) return
  ed.focus()
  ed.trigger('md-toolbar', cmd, null)
}

// ---- 表格 ----
const PICKER_ROWS = 8
const PICKER_COLS = 8
const tablePickerOpen = ref(false)
const hoverRows = ref(0)
const hoverCols = ref(0)

function setHover(r: number, c: number) {
  hoverRows.value = r
  hoverCols.value = c
}

function resetHover() {
  hoverRows.value = 0
  hoverCols.value = 0
}

/** 生成 rows 行（不含表头）× cols 列的 Markdown 表格，并选中第一个表头单元格。 */
function insertTable(rows: number, cols: number) {
  const headers = Array.from({ length: cols }, (_, i) => `列${i + 1}`)
  const header = `| ${headers.join(' | ')} |`
  const sep = `| ${headers.map(() => '---').join(' | ')} |`
  const body = Array.from({ length: rows }, () => `| ${headers.map(() => '   ').join(' | ')} |`)
  const block = [header, sep, ...body].join('\n')
  insertBlock(block, 2, 2 + headers[0].length)
  tablePickerOpen.value = false
  resetHover()
}

interface ToolbarBtn {
  key: string
  title: string
  icon?: string
  action: () => void
}

const toolbarGroups: ToolbarBtn[][] = [
  [
    { key: 'undo', title: '撤销 (Ctrl+Z)', icon: 'icon-undo', action: () => trigger('undo') },
    { key: 'redo', title: '重做 (Ctrl+Y)', icon: 'icon-redo', action: () => trigger('redo') },
  ],
  [
    { key: 'bold', title: '粗体', icon: 'icon-bold', action: () => wrap('**', '粗体文字') },
    { key: 'strike', title: '删除线', icon: 'icon-strikethrough', action: () => wrap('~~', '删除文字') },
    { key: 'italic', title: '斜体', icon: 'icon-italic', action: () => wrap('*', '斜体文字') },
    { key: 'quote', title: '引用', icon: 'icon-quote', action: () => linePrefix('quote') },
    { key: 'code', title: '行内代码', icon: 'icon-code', action: () => wrap('`', 'code') },
  ],
  [1, 2, 3, 4, 5, 6].map((lv) => ({
    key: `h${lv}`,
    title: `标题 ${lv}`,
    icon: `icon-h${lv}`,
    action: () => linePrefix('heading', lv),
  })),
  [
    { key: 'ul', title: '无序列表', icon: 'icon-unordered-list', action: () => linePrefix('ul') },
    { key: 'ol', title: '有序列表', icon: 'icon-ordered-list', action: () => linePrefix('ol') },
    { key: 'task', title: '任务列表', icon: 'icon-check-square', action: () => linePrefix('task') },
    { key: 'hr', title: '分隔线', icon: 'icon-minus', action: insertHr },
  ],
  [
    { key: 'link', title: '链接', icon: 'icon-link', action: () => insertLink(false) },
    { key: 'image', title: '图片', icon: 'icon-image', action: () => insertLink(true) },
    { key: 'codeblock', title: '代码块', icon: 'icon-code-block', action: insertCodeBlock },
    { key: 'table', title: '插入表格', action: () => { tablePickerOpen.value = true } },
    { key: 'datetime', title: '插入当前时间', icon: 'icon-calendar-clock', action: insertDateTime },
  ],
]
</script>

<style lang="less" scoped>
.doc-editor {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding-bottom: 4px;

  /* 全屏：铺满视口（z-index 低于 Arco 弹层，表格选择等浮层可正常显示） */
  &.is-fullscreen {
    position: fixed;
    inset: 0;
    z-index: 1000;
    padding: 0 14px 14px;
    background: var(--ui-bg-canvas);
  }
}

.doc-fs-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  height: 48px;
  margin-bottom: 10px;
  padding: 0 4px;
  border-bottom: 1px solid var(--ui-border);

  .doc-fs-title {
    flex: 1;
    min-width: 0;
    font-size: 13.5px;
    font-weight: 600;
    color: var(--color-text-1);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.doc-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 8px;
}

.doc-pane {
  flex: 1 1 0;
  min-width: 0;
  min-height: 0;
}

.doc-edit {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-panel);
  overflow: hidden;

  /* 外层已带边框，编辑器自身边框去掉 */
  :deep(.monaco-container) {
    border: none;
    border-radius: 0;
  }
}

.md-toolbar {
  flex-shrink: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1px;
  padding: 5px 8px;
  border-bottom: 1px solid var(--ui-border-soft);
  background: var(--ui-bg-subtle);
}

.md-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: none;
  border-radius: var(--ui-radius-sm);
  background: transparent;
  color: var(--color-text-2);
  font-size: 15px;
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease;

  &:hover {
    background: var(--ui-bg-panel);
    color: rgb(var(--primary-6));
    box-shadow: var(--ui-shadow-1);
  }

  &:active {
    background: var(--ui-bg-active);
  }
}

.md-svg {
  width: 1em;
  height: 1em;
}

.md-divider {
  width: 1px;
  height: 15px;
  margin: 0 5px;
  background: var(--ui-border);
}

.doc-preview {
  overflow-y: auto;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-panel);

  :deep(.github-markdown-body) {
    padding: 4px 18px 18px;
    background: transparent;
    font-size: 13.5px;
    line-height: 1.75;
  }
}

.doc-empty {
  padding: 28px 16px;
  color: var(--color-text-4);
  font-size: 12.5px;
  text-align: center;
}

.tbl-picker {
  user-select: none;

  .tbl-row {
    display: flex;
    gap: 3px;
    margin-bottom: 3px;
  }

  .tbl-cell {
    width: 16px;
    height: 16px;
    border: 1px solid var(--ui-border-strong);
    border-radius: 3px;
    cursor: pointer;
    transition: background-color 0.1s ease, border-color 0.1s ease;

    &.active {
      border-color: rgb(var(--primary-6));
      background: rgba(var(--primary-6), 0.22);
    }
  }

  .tbl-label {
    margin-top: 6px;
    color: var(--color-text-3);
    font-size: 11.5px;
    text-align: center;
  }
}
</style>
