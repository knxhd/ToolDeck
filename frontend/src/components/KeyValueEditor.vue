<template>
  <div class="kv-editor" :class="{ 'is-bulk-capable': bulk }">
    <!-- 文本批量编辑模式：每行一条 key:value，// 开头表示禁用 -->
    <template v-if="bulk && bulkMode">
      <MonacoEditor class="kv-bulk-editor" :model-value="bulkText" language="plaintext" fill
        :var-resolver="varResolver" @update:model-value="onBulkInput" />
    </template>

    <!-- 表格模式：与 Form Data 保持一致的表头 + 固定列宽，保证各行垂直对齐 -->
    <div v-else class="kv-rows">
      <div class="kv-table">
        <div class="kv-row kv-head">
          <span class="kv-col-check"></span>
          <span class="kv-col-key">Key</span>
          <span class="kv-col-value">Value</span>
          <span class="kv-col-op"></span>
        </div>
        <div v-for="(item, i) in rows" :key="i" class="kv-row">
          <span class="kv-col-check">
            <a-checkbox
              :model-value="item.enabled"
              :disabled="!item.key && !item.value"
              @change="onToggle(i, $event)"
            />
          </span>
          <span class="kv-col-key">
            <a-input :model-value="item.key" placeholder="Key" size="small" @input="onKey(i, $event)" />
          </span>
          <span class="kv-col-value">
            <a-input :model-value="item.value" placeholder="Value" size="small" @input="onValue(i, $event)" />
          </span>
          <!-- 操作列恒定占位，空尾行不显示按钮但保留宽度，避免列错位 -->
          <span class="kv-col-op">
            <a-button v-if="item.key || item.value" size="small" status="danger" type="text" @click="remove(i)">
              <template #icon><icon-delete /></template>
            </a-button>
          </span>
        </div>
      </div>
    </div>

    <div v-if="bulk" class="kv-footer">
      <span v-if="bulkMode" class="kv-bulk-hint">每行一条 key:value，以 // 开头表示禁用</span>
      <a-button size="mini" type="text" @click="toggleBulk">
        {{ bulkMode ? 'Key/Value Edit' : 'Bulk Edit' }}
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import type { KeyValue } from '@/api/types'
import type { VarResolver } from '@/utils/varInfo'

/** bulk：是否提供「Bulk Edit」文本批量编辑切换（默认关闭）；varResolver：批量编辑时高亮占位符。 */
const props = defineProps<{ modelValue: KeyValue[]; bulk?: boolean; varResolver?: VarResolver }>()
const emit = defineEmits<{ 'update:modelValue': [value: KeyValue[]] }>()

const clone = (list: KeyValue[]) => JSON.parse(JSON.stringify(list || []))

const emptyRow = (): KeyValue => ({ key: '', value: '', enabled: true })

/** 保证列表末尾是空行：末行已填值时补一个新空行；列表为空时补一条空行。 */
function ensureTail(list: KeyValue[]): KeyValue[] {
  const last = list[list.length - 1]
  if (!list.length || last.key || last.value) list.push(emptyRow())
  return list
}

/** 显示行 = 数据行 + 恒定空尾行（空行只存在于显示层；有值行才是数据）。 */
const rows = ref<KeyValue[]>(ensureTail(clone(props.modelValue)))

// ---- 文本批量编辑 ----
const bulkMode = ref(false)
const bulkText = ref('')
/** 最近一次由文本编辑提交的数据，用于识别「自己触发的回流」，避免重写文本导致光标跳动。 */
let lastBulkCommit = ''

const dataKey = (list: KeyValue[]) =>
  JSON.stringify((list || []).filter((r) => r.key || r.value).map((r) => [r.key, r.value, !!r.enabled]))

/** 列表 → 文本：每行 key:value，禁用项以 // 开头。 */
function toBulkText(list: KeyValue[]): string {
  return (list || [])
    .filter((r) => r.key || r.value)
    .map((r) => `${r.enabled ? '' : '//'}${r.key}:${r.value}`)
    .join('\n')
}

/** 文本 → 列表：按首个冒号拆分 key / value，空行忽略，// 开头为禁用项。 */
function parseBulkText(text: string): KeyValue[] {
  const out: KeyValue[] = []
  for (const raw of text.split(/\r?\n/)) {
    let line = raw.trim()
    if (!line) continue
    let enabled = true
    if (line.startsWith('//')) {
      enabled = false
      line = line.slice(2).trim()
      if (!line) continue
    }
    const idx = line.indexOf(':')
    const key = idx < 0 ? line : line.slice(0, idx).trim()
    const value = idx < 0 ? '' : line.slice(idx + 1).trim()
    if (key || value) out.push({ key, value, enabled })
  }
  return out
}

function onBulkInput(text: string) {
  bulkText.value = text
  const parsed = parseBulkText(text)
  lastBulkCommit = dataKey(parsed)
  const next = ensureTail(parsed.length ? parsed : [emptyRow()])
  rows.value = clone(next)
  emit('update:modelValue', clone(next))
}

function toggleBulk() {
  bulkMode.value = !bulkMode.value
  if (bulkMode.value) {
    bulkText.value = toBulkText(rows.value)
    lastBulkCommit = dataKey(rows.value)
  }
}

watch(
  () => props.modelValue,
  (val) => {
    rows.value = ensureTail(clone(val))
    // 外部改动（如 URL 同步到 Params）时刷新文本；自身文本编辑回流则保持原文本不动
    if (bulkMode.value && dataKey(val) !== lastBulkCommit) {
      bulkText.value = toBulkText(val)
      lastBulkCommit = dataKey(val)
    }
  },
)

// ---- 表格编辑 ----
/** 把显示层同步为数据层（仅有值行 + 恒定空尾行），并提交父级（数据层也带一条空行，后端会过滤空 key）。 */
function syncAndCommit() {
  const data = rows.value.filter((r) => r.key || r.value)
  const next = ensureTail(data.length ? clone(data) : [emptyRow()])
  rows.value = next
  emit('update:modelValue', clone(next))
}

function onKey(i: number, value: string) {
  rows.value[i].key = value
  syncAndCommit()
}

function onValue(i: number, value: string) {
  rows.value[i].value = value
  syncAndCommit()
}

function onToggle(i: number, checked: boolean | (string | number | boolean)[]) {
  rows.value[i].enabled = !!checked
  syncAndCommit()
}

/** 只允许删除有值行；空尾行不显示删除按钮。 */
function remove(i: number) {
  if (!rows.value[i] || (!rows.value[i].key && !rows.value[i].value)) return
  const data = rows.value.filter((_, idx) => idx !== i).filter((r) => r.key || r.value)
  const next = ensureTail(data.length ? clone(data) : [emptyRow()])
  rows.value = next
  emit('update:modelValue', clone(next))
}
</script>

<style lang="less" scoped>
.kv-editor {
  display: flex;
  flex-direction: column;
  gap: 6px;

  /* 开启 Bulk Edit 时占满所在面板：表格区滚动，底部按钮固定 */
  &.is-bulk-capable {
    flex: 1;
    min-height: 0;
    padding-bottom: 4px;
  }

  .kv-rows {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  &.is-bulk-capable .kv-rows {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  .kv-table {
    border: 1px solid var(--ui-border);
    border-radius: var(--ui-radius-md);
    background: var(--ui-bg-panel);
    overflow: auto;
  }

  .kv-row {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 34px;
    padding: 3px 8px;
    border-bottom: 1px solid var(--ui-border-soft);
    transition: background-color 0.12s ease;

    &:last-child {
      border-bottom: none;
    }

    &:not(.kv-head):hover {
      background: var(--ui-bg-hover);
    }

    &.kv-head {
      min-height: 28px;
      padding: 0 8px;
      border-bottom: 1px solid var(--ui-border);
      background: var(--ui-bg-subtle);
      font-family: var(--ui-font-mono);
      font-size: 10.5px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--color-text-3);
    }
  }

  .kv-col-check {
    width: 20px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
  }

  .kv-col-key,
  .kv-col-value {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    align-items: center;

    /* 行内输入框默认熔入表格，hover / 聚焦才显形，减少视觉噪音 */
    :deep(.arco-input-wrapper) {
      background: transparent;
      border-color: transparent;
      border-radius: var(--ui-radius-sm);
      font-family: var(--ui-font-mono);
      font-size: 12px;
      transition: background-color 0.12s ease, border-color 0.12s ease;

      &:hover {
        background: var(--ui-bg-panel);
        border-color: var(--ui-border);
      }
    }
  }

  .kv-col-op {
    width: 26px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;

    :deep(.arco-btn) {
      width: 22px;
      height: 22px;
      padding: 0;
      border-radius: var(--ui-radius-sm);
      font-size: 12px;
      opacity: 0.55;
      transition: opacity 0.12s ease, background-color 0.12s ease;

      &:hover {
        opacity: 1;
      }
    }
  }

  .kv-footer {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
    padding-top: 2px;

    :deep(.arco-btn) {
      height: 24px;
      padding: 0 8px;
      border-radius: var(--ui-radius-sm);
      color: var(--color-text-2);
      font-size: 12px;

      &:hover {
        background: var(--ui-bg-hover);
        color: rgb(var(--primary-6));
      }
    }
  }

  .kv-bulk-hint {
    margin-right: auto;
    color: var(--color-text-3);
    font-size: 11.5px;
  }
}
</style>
