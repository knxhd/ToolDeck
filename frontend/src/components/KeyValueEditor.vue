<template>
  <div class="kv-editor">
    <div v-for="(item, i) in local" :key="i" class="kv-row">
      <a-checkbox v-model="item.enabled" />
      <a-input v-model="item.key" placeholder="key" size="small" @change="emitChange" />
      <span class="kv-sep">:</span>
      <a-input v-model="item.value" placeholder="value" size="small" @change="emitChange" />
      <a-button size="small" status="danger" type="secondary" shape="circle" @click="remove(i)">
        <template #icon><icon-delete /></template>
      </a-button>
    </div>
    <a-button size="small" type="secondary" @click="add">
      <template #icon><icon-plus /></template>
      添加
    </a-button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { KeyValue } from '@/api/types'

const props = defineProps<{ modelValue: KeyValue[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: KeyValue[]] }>()

const local = ref<KeyValue[]>(JSON.parse(JSON.stringify(props.modelValue || [])))

watch(
  () => props.modelValue,
  (val) => {
    local.value = JSON.parse(JSON.stringify(val || []))
  },
)

function emitChange() {
  emit('update:modelValue', JSON.parse(JSON.stringify(local.value)))
}

function add() {
  local.value.push({ key: '', value: '', enabled: true })
  emitChange()
}

function remove(i: number) {
  local.value.splice(i, 1)
  emitChange()
}
</script>

<style lang="less" scoped>
.kv-editor {
  display: flex; flex-direction: column; gap: 6px;
  .kv-row { display: flex; align-items: center; gap: 8px; }
  .kv-sep { color: var(--el-text-color-secondary); }
}
</style>
