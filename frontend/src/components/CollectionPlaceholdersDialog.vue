<template>
  <a-modal :visible="visible" width="1100px" :footer="false" :mask-closable="false" unmount-on-close
    @cancel="onClose">
    <template #title>
      <span>集合占位符</span>
      <span v-if="collection" class="collection-tag">{{ collection.name }}</span>
    </template>

    <a-empty v-if="!collection" description="请先从某个集合打开请求" />

    <template v-else>
      <div class="ph-dialog-hint">
        集合内所有请求均可用 <code v-pre>{{名称}}</code> 引用；同名时请求自身的占位符优先。
      </div>
      <div class="ph-dialog-body">
        <PlaceholderEditor v-model="localList" title="集合占位符" />
      </div>
      <div class="dialog-footer">
        <a-button @click="onReset">重置</a-button>
        <a-button type="primary" @click="onSave">保存</a-button>
      </div>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import PlaceholderEditor from '@/components/PlaceholderEditor.vue'
import { useEnvironmentsStore } from '@/stores/environments'
import { VAR_NAME_RE } from '@/utils/env'
import { toast } from '@/utils/feedback'
import type { KeyValue } from '@/api/types'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [v: boolean] }>()

const envStore = useEnvironmentsStore()

const collection = computed(() => envStore.collection)

/** 编辑副本：保存时才回写集合并持久化。 */
const localList = ref<KeyValue[]>([])

watch(
  () => props.visible,
  (v) => {
    if (v) loadFromStore()
  },
  { immediate: true },
)

function loadFromStore() {
  localList.value = JSON.parse(JSON.stringify(envStore.collectionPlaceholders))
}

async function onSave() {
  const list = localList.value
  const enabledKeys = list.filter((p) => p.enabled).map((p) => (p.key || '').trim())
  if (list.some((p) => !VAR_NAME_RE.test((p.key || '').trim()))) {
    toast.warning('存在名称为空或不合法的占位符')
    return
  }
  if (new Set(enabledKeys).size !== enabledKeys.length) {
    toast.warning('存在重名的占位符')
    return
  }
  await envStore.replacePlaceholders(JSON.parse(JSON.stringify(list)))
  toast.success('集合占位符已保存')
  emit('update:visible', false)
}

function onReset() {
  loadFromStore()
}

function onClose() {
  emit('update:visible', false)
}
</script>

<style lang="less" scoped>
.collection-tag {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.ph-dialog-hint {
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);

  code {
    background: var(--el-fill-color);
    padding: 1px 4px;
    border-radius: 3px;
  }
}

.ph-dialog-body {
  height: 60vh;
  min-height: 360px;
  display: flex;
  flex-direction: column;
}

.dialog-footer {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
