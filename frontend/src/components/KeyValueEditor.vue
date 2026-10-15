<template>
  <div class="kv-editor" :class="{ 'is-bulk-capable': bulk }">
    <!-- 文本批量编辑模式：每行一条 key:value，// 开头表示禁用 -->
    <template v-if="bulk && bulkMode">
      <MonacoEditor class="kv-bulk-editor" :model-value="bulkText" language="plaintext" fill
        @update:model-value="onBulkInput" />
    </template>

    <!-- 表格模式 -->
    <div v-else class="kv-rows">
      <div v-for="(item, i) in rows" :key="i" class="kv-row">
        <a-checkbox
          :model-value="item.enabled"
          :disabled="!item.key && !item.value"
          @change="onToggle(i, $event)"
        />
        <a-input :model-value="item.key" placeholder="key" size="small" @input="onKey(i, $event)" />
        <span class="kv-sep">:</span>
        <a-input :model-value="item.value" placeholder="value" size="small" @input="onValue(i, $event)" />
        <a-button
          v-if="item.key || item.value"
          size="small"
          status="danger"
          type="secondary"
          shape="circle"
          @click="remove(i)"
        >
          <template #icon><icon-delete /></template>
        </a-button>
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

/** bulk：是否提供「Bulk Edit」文本批量编辑切换（默认关闭）。 */
const props = defineProps<{ modelValue: KeyValue[]; bulk?: boolean }>()
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

  .kv-row {
    display: flex;
    align-items: center;
    gap: 8px;

    :deep(.arco-input) {
      flex: 1;
    }
  }

  .kv-sep {
    color: var(--el-text-color-secondary);
    flex-shrink: 0;
  }

  .kv-footer {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
  }

  .kv-bulk-hint {
    margin-right: auto;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}
</style>
