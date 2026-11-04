<template>
  <div class="fd-editor">
    <div class="fd-table">
      <div class="fd-row fd-head">
        <span class="fd-col-check"></span>
        <span class="fd-col-key">Key</span>
        <span class="fd-col-value">Value</span>
        <span class="fd-col-op"></span>
      </div>
      <div v-for="(item, i) in rows" :key="i" class="fd-row">
        <span class="fd-col-check">
          <a-checkbox :model-value="item.enabled" :disabled="isBlank(item)" @change="onToggle(i, $event)" />
        </span>

        <!-- Key -->
        <span class="fd-col-key">
          <a-input :model-value="item.key" placeholder="Key" size="small"
            @input="update(i, { key: $event })" />
        </span>

        <!-- Value：文本输入（内置上传图标） 或 已选文件 chip -->
        <span class="fd-col-value">
          <span v-if="item.type === 'file'" class="fd-file-chip" :title="item.value">
            <icon-file class="fd-file-icon" />
            <span class="fd-file-name">{{ item.value.split(/[\\/]/).pop() || item.value }}</span>
            <icon-close class="fd-file-clear" @click="clearFile(i)" />
          </span>
          <a-input v-else :model-value="item.value" placeholder="Value" size="small"
            @input="update(i, { value: $event })">
            <template #suffix>
              <a-tooltip content="选择文件">
                <icon-upload class="fd-suffix-icon" :class="{ loading: pickingIdx === i }"
                  @click="pickFile(i)" />
              </a-tooltip>
            </template>
          </a-input>
        </span>

        <!-- 操作：删除 -->
        <span class="fd-col-op">
          <a-button v-if="!isBlank(item)" size="small" status="danger" type="text" @click="remove(i)">
            <template #icon><icon-delete /></template>
          </a-button>
        </span>
      </div>
    </div>

    <!-- 原生对话框不可用时的兜底：浏览器选择文件并上传副本 -->
    <input ref="fileInputRef" type="file" class="fd-hidden-input" @change="onBrowserFileChosen" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

import { api } from '@/api/client'
import { toast } from '@/utils/feedback'
import type { FormDataItem } from '@/api/types'

const props = defineProps<{ modelValue: FormDataItem[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: FormDataItem[]] }>()

const emptyRow = (): FormDataItem => ({ key: '', value: '', enabled: true, type: 'text' })

/** 空行：无 key、无 value 且为 Text 类型（File 行即使无 key 也视为已编辑数据）。 */
const isBlank = (r: FormDataItem) => !r.key && !r.value && r.type !== 'file'

const clone = (list: FormDataItem[]): FormDataItem[] => JSON.parse(JSON.stringify(list || []))

/** 保证末尾恒有一条空行，便于继续追加。 */
function withTail(list: FormDataItem[]): FormDataItem[] {
  const data = list.filter((r) => !isBlank(r))
  return [...data, emptyRow()]
}

const rows = ref<FormDataItem[]>(withTail(clone(props.modelValue)))

watch(
  () => props.modelValue,
  (val) => {
    rows.value = withTail(clone(val))
  },
)

function commit(next: FormDataItem[]) {
  rows.value = withTail(next)
  emit('update:modelValue', clone(rows.value.filter((r) => !isBlank(r))))
}

function update(i: number, patch: Partial<FormDataItem>) {
  commit(rows.value.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
}

function onToggle(i: number, checked: boolean | (string | number | boolean)[]) {
  update(i, { enabled: !!checked })
}

function clearFile(i: number) {
  update(i, { type: 'text', value: '' })
}

function remove(i: number) {
  commit(rows.value.filter((_, idx) => idx !== i))
}

// ---- 选择文件 ----
const pickingIdx = ref(-1)
const fileInputRef = ref<HTMLInputElement | null>(null)
let pendingIdx = -1

/**
 * 优先调用后端弹出本机原生对话框，拿到文件真实路径；
 * 不可用（Docker / 非本机访问）时退回浏览器选择 + 上传副本，路径为副本在数据目录中的位置。
 */
async function pickFile(i: number) {
  pickingIdx.value = i
  try {
    const res = await api.post<{ path: string | null }>('/api/files/pick')
    if (res.path) update(i, { type: 'file', value: res.path })
  } catch {
    pendingIdx = i
    fileInputRef.value?.click()
  } finally {
    pickingIdx.value = -1
  }
}

async function onBrowserFileChosen(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  const idx = pendingIdx
  pendingIdx = -1
  if (!file || idx < 0) return
  pickingIdx.value = idx
  try {
    const res = await fetch(`/api/files/upload?filename=${encodeURIComponent(file.name)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/octet-stream' },
      body: file,
    })
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    const data = (await res.json()) as { path: string }
    update(idx, { type: 'file', value: data.path })
    toast.info('已将文件副本保存到数据目录')
  } catch (err) {
    toast.error('文件上传失败：' + (err as Error).message)
  } finally {
    pickingIdx.value = -1
  }
}
</script>

<style lang="less" scoped>
.fd-editor {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.fd-table {
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-panel);
  overflow: hidden;
}

.fd-row {
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

  &:not(.fd-head):hover {
    background: var(--ui-bg-hover);
  }

  &.fd-head {
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

.fd-col-check {
  width: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.fd-col-key {
  flex: 1 1 0;
  min-width: 0;
}

.fd-col-value {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  align-items: center;
}

.fd-col-key,
.fd-col-value {
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

.fd-file-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  height: 26px;
  padding: 0 8px;
  border: 1px solid rgba(var(--primary-6), 0.32);
  border-radius: var(--ui-radius-sm);
  background: rgba(var(--primary-6), 0.1);
  color: rgb(var(--primary-6));
  font-family: var(--ui-font-mono);
  font-size: 12px;

  .fd-file-icon {
    flex-shrink: 0;
  }

  .fd-file-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .fd-file-clear {
    flex-shrink: 0;
    cursor: pointer;
    color: var(--color-text-3);

    &:hover {
      color: var(--ui-accent-danger);
    }
  }
}

.fd-col-op {
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
    transition: opacity 0.12s ease;

    &:hover {
      opacity: 1;
    }
  }
}

.fd-hidden-input {
  display: none;
}

.fd-suffix-icon {
  cursor: pointer;
  color: var(--color-text-4);
  font-size: 13px;
  transition: color 0.12s ease;

  &:hover {
    color: rgb(var(--primary-6));
  }

  &.loading {
    opacity: 0.6;
    pointer-events: none;
  }
}
</style>
