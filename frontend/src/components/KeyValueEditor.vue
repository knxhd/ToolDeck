<template>
  <div class="kv-editor">
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
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { KeyValue } from '@/api/types'

const props = defineProps<{ modelValue: KeyValue[] }>()
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

watch(
  () => props.modelValue,
  (val) => {
    rows.value = ensureTail(clone(val))
  },
)

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
}
</style>
