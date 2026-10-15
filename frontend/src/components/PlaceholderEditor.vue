<template>
  <div class="ph-editor">
    <!-- 左侧：占位符列表 -->
    <div class="ph-list">
      <div class="ph-list-head">
        <span class="ph-list-title">{{ title || '占位符' }}</span>
        <a-button size="mini" type="text" @click="add">
          <template #icon><icon-plus /></template>
          新增
        </a-button>
      </div>
      <div class="ph-items">
        <div v-for="(p, i) in modelValue" :key="i" class="ph-item"
          :class="{ active: i === activeIdx, disabled: !p.enabled }" @click="activeIdx = i">
          <a-checkbox :model-value="p.enabled" @click.stop @change="onToggle(i, $event)" />
          <span class="ph-name" :class="{ invalid: !!nameError(i) }" :title="p.key">{{ p.key || '(未命名)' }}</span>
          <span class="ph-len" title="字符数">{{ (p.value || '').length }}</span>
          <icon-delete class="ph-del" title="删除" @click.stop="remove(i)" />
        </div>
        <div v-if="!modelValue.length" class="ph-empty">
          暂无占位符<br />点击「新增」创建
        </div>
      </div>
    </div>

    <!-- 右侧：名称 + 文本编辑 -->
    <div v-if="current" class="ph-detail">
      <div class="ph-detail-head">
        <a-input :model-value="current.key" size="small" class="ph-key-input" placeholder="名称，如 system_prompt"
          :error="!!currentError" @input="onRename" />
        <a-tooltip content="点击复制引用">
          <span class="ph-ref" @click="copyRef">{{ refText }}</span>
        </a-tooltip>
        <span v-if="currentError" class="ph-error">{{ currentError }}</span>
        <a-tooltip :content="HELP_TEXT" position="bl">
          <icon-question-circle class="ph-help" />
        </a-tooltip>
      </div>
      <MonacoEditor :key="activeIdx" :model-value="current.value" language="markdown" fill
        @update:model-value="onValue" />
    </div>
    <div v-else class="ph-detail ph-detail-empty">
      <a-empty description="选择或新增一个占位符进行编辑" />
      <div class="ph-help-text">{{ HELP_TEXT }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import { VAR_NAME_RE } from '@/utils/env'
import { toast } from '@/utils/feedback'
import type { KeyValue } from '@/api/types'

/** title：列表标题（如「请求占位符」/「集合占位符」）。 */
const props = defineProps<{ modelValue: KeyValue[]; title?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: KeyValue[]] }>()

const HELP_TEXT =
  '在 URL / Params / Headers / Body 中用 {{名称}} 引用占位符。' +
  'JSON Body 的字符串内引用时，换行、制表符、引号等会自动转义；' +
  '同名优先级：请求占位符 > 集合占位符 > 环境变量；占位符文本中也可引用其它变量。'

const activeIdx = ref(props.modelValue.length ? 0 : -1)

// 列表变化（切换请求、删除）时保证选中项合法
watch(
  () => props.modelValue.length,
  (len) => {
    if (activeIdx.value >= len) activeIdx.value = len - 1
    if (activeIdx.value < 0 && len) activeIdx.value = 0
  },
)

const current = computed<KeyValue | null>(() => props.modelValue[activeIdx.value] ?? null)

const refText = computed(() => `{{${current.value?.key || '名称'}}}`)

/** 名称校验：非空、字符合法、不与其它启用项重名。 */
function nameError(i: number): string {
  const p = props.modelValue[i]
  if (!p) return ''
  const key = (p.key || '').trim()
  if (!key) return '名称不能为空'
  if (!VAR_NAME_RE.test(key)) return '仅支持字母、数字、下划线、点、短横线'
  if (p.enabled && props.modelValue.some((o, j) => j !== i && o.enabled && (o.key || '').trim() === key)) {
    return '名称重复'
  }
  return ''
}

const currentError = computed(() => (current.value ? nameError(activeIdx.value) : ''))

function commit(next: KeyValue[]) {
  emit('update:modelValue', next)
}

function update(i: number, patch: Partial<KeyValue>) {
  commit(props.modelValue.map((p, idx) => (idx === i ? { ...p, ...patch } : p)))
}

function add() {
  const used = new Set(props.modelValue.map((p) => p.key))
  let n = props.modelValue.length + 1
  while (used.has(`prompt_${n}`)) n += 1
  commit([...props.modelValue, { key: `prompt_${n}`, value: '', enabled: true }])
  activeIdx.value = props.modelValue.length
}

function remove(i: number) {
  const nextLen = props.modelValue.length - 1
  commit(props.modelValue.filter((_, idx) => idx !== i))
  if (nextLen <= 0) activeIdx.value = -1
  else if (activeIdx.value > i) activeIdx.value -= 1
  else if (activeIdx.value >= nextLen) activeIdx.value = nextLen - 1
}

function onToggle(i: number, checked: boolean | (string | number | boolean)[]) {
  update(i, { enabled: !!checked })
}

function onRename(value: string) {
  update(activeIdx.value, { key: value.trim() })
}

function onValue(value: string) {
  if (!current.value || value === current.value.value) return
  update(activeIdx.value, { value })
}

async function copyRef() {
  if (!current.value?.key) return
  try {
    await navigator.clipboard.writeText(refText.value)
    toast.success(`已复制 ${refText.value}`)
  } catch {
    toast.error('复制失败')
  }
}
</script>

<style lang="less" scoped>
.ph-editor {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 8px;
  padding-bottom: 8px;
}

.ph-list {
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  min-height: 0;

  .ph-list-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 4px 4px 10px;
    border-bottom: 1px solid var(--el-border-color);
  }

  .ph-list-title {
    font-weight: 600;
    font-size: 13px;
  }

  .ph-items {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 4px;
  }

  .ph-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 6px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;

    &:hover {
      background: var(--color-fill-2);

      .ph-del {
        visibility: visible;
      }
    }

    &.active {
      background: rgb(var(--primary-1));
      color: rgb(var(--primary-6));
    }

    &.disabled .ph-name {
      opacity: 0.5;
      text-decoration: line-through;
    }
  }

  .ph-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: ui-monospace, 'JetBrains Mono', Menlo, monospace;

    &.invalid {
      color: rgb(var(--danger-6));
    }
  }

  .ph-len {
    font-size: 11px;
    color: var(--color-text-3);
  }

  .ph-del {
    visibility: hidden;
    color: var(--color-text-3);

    &:hover {
      color: rgb(var(--danger-6));
    }
  }

  .ph-empty {
    padding: 24px 8px;
    text-align: center;
    color: var(--color-text-3);
    font-size: 12px;
    line-height: 1.8;
  }
}

.ph-detail {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;

  .ph-detail-head {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .ph-key-input {
    width: 240px;
  }

  .ph-ref {
    font-family: ui-monospace, 'JetBrains Mono', Menlo, monospace;
    font-size: 12px;
    padding: 1px 6px;
    border-radius: 3px;
    background: rgba(255, 176, 32, 0.22);
    color: #d48806;
    cursor: pointer;
  }

  .ph-error {
    color: rgb(var(--danger-6));
    font-size: 12px;
  }

  .ph-help {
    margin-left: auto;
    color: var(--color-text-3);
    cursor: help;
  }
}

.ph-detail-empty {
  align-items: center;
  justify-content: center;

  .ph-help-text {
    max-width: 420px;
    color: var(--color-text-3);
    font-size: 12px;
    line-height: 1.8;
    text-align: center;
  }
}
</style>
