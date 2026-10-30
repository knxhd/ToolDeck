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

        <!-- Key + 类型（Text / File） -->
        <span class="fd-col-key">
          <a-input :model-value="item.key" placeholder="Key" size="small" class="fd-key-input"
            @input="update(i, { key: $event })" />
          <a-select :model-value="item.type" size="small" class="fd-type" :bordered="false"
            :trigger-props="{ autoFitPopupMinWidth: true }" @change="onType(i, $event)">
            <a-option value="text">Text</a-option>
            <a-option value="file">File</a-option>
          </a-select>
        </span>

        <!-- Value：文本 或 文件路径 -->
        <span class="fd-col-value">
          <template v-if="item.type === 'file'">
            <a-input :model-value="item.value" size="small" class="fd-path-input" allow-clear
              placeholder="文件路径，如 D:\data\avatar.png" :title="item.value"
              @input="update(i, { value: $event })" @clear="update(i, { value: '' })">
              <template #prefix><icon-file /></template>
            </a-input>
            <a-button size="small" :loading="pickingIdx === i" @click="pickFile(i)">选择文件</a-button>
          </template>
          <a-input v-else :model-value="item.value" placeholder="Value" size="small"
            @input="update(i, { value: $event })" />
        </span>

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

/** 空行：无 key、无 value 且为 Text 类型（File 类型的空行视为用户正在编辑的数据行）。 */
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

function onType(i: number, v: unknown) {
  const type = v === 'file' ? 'file' : 'text'
  if (type === rows.value[i].type) return
  // 切换类型时清空 value：文本值与文件路径语义不同
  update(i, { type, value: '' })
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
    if (res.path) update(i, { value: res.path })
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
    update(idx, { value: data.path })
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
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}

.fd-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-bottom: 1px solid var(--el-border-color);

  &:last-child {
    border-bottom: none;
  }

  &.fd-head {
    font-size: 13px;
    font-weight: 600;
    color: var(--el-text-color-secondary);
    padding-top: 6px;
    padding-bottom: 6px;
  }
}

.fd-col-check {
  width: 20px;
  flex-shrink: 0;
}

.fd-col-key {
  width: 36%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 4px;

  .fd-key-input {
    flex: 1;
    min-width: 0;
  }

  .fd-type {
    width: 76px;
    flex-shrink: 0;
  }
}

.fd-col-value {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;

  .fd-path-input {
    flex: 1;
    min-width: 0;
  }
}

.fd-col-op {
  width: 32px;
  flex-shrink: 0;
  text-align: center;
}

.fd-hidden-input {
  display: none;
}
</style>
