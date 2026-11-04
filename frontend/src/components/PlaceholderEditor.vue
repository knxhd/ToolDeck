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
          :class="{ active: !activeBuiltin && i === activeIdx, disabled: !p.enabled }" @click="selectItem(i)">
          <a-checkbox :model-value="p.enabled" @click.stop @change="onToggle(i, $event)" />
          <span class="ph-name" :class="{ invalid: !!nameError(i) }" :title="p.key">{{ p.key || '(未命名)' }}</span>
          <span class="ph-len" title="字符数">{{ (p.value || '').length }}</span>
          <icon-delete class="ph-del" title="删除" @click.stop="remove(i)" />
        </div>
        <div v-if="!modelValue.length" class="ph-empty">
          暂无占位符<br />点击「新增」创建
        </div>

        <!-- 内置占位符（只读） -->
        <div class="ph-group-title">内置占位符</div>
        <div v-for="b in BUILTIN_VARS" :key="b.name" class="ph-item ph-builtin"
          :class="{ active: activeBuiltin === b.name }" :title="b.desc" @click="activeBuiltin = b.name">
          <icon-thunderbolt class="ph-builtin-icon" />
          <span class="ph-name">{{ b.name }}</span>
        </div>
      </div>
    </div>

    <!-- 右侧：内置占位符说明 -->
    <div v-if="builtin" class="ph-detail ph-builtin-detail">
      <div class="ph-detail-head">
        <span class="ph-builtin-name">{{ builtin.name }}</span>
        <a-tag size="small" color="arcoblue">内置</a-tag>
        <a-tooltip content="点击复制引用">
          <span class="ph-ref" @click="copyText2(builtinRef)">{{ builtinRef }}</span>
        </a-tooltip>
      </div>
      <div class="ph-builtin-body">
        <div class="ph-builtin-row">
          <span class="ph-builtin-label">说明</span>
          <span>{{ builtin.desc }}</span>
        </div>
        <div v-if="builtin.usage" class="ph-builtin-row">
          <span class="ph-builtin-label">参数</span>
          <span>{{ builtin.usage }}</span>
        </div>
        <div class="ph-builtin-row">
          <span class="ph-builtin-label">示例</span>
          <code class="ph-builtin-sample">{{ sample }}</code>
          <a-button size="mini" type="text" title="重新生成" @click="refreshSample">
            <template #icon><icon-refresh /></template>
          </a-button>
        </div>
        <div class="ph-help-text">
          内置占位符无需定义，可直接在 URL / Params / Headers / Body / 其它占位符中引用；
          每次发送、每处引用都会重新生成。同名时自定义变量优先。
        </div>
      </div>
    </div>

    <!-- 右侧：名称 + 文本编辑 -->
    <div v-else-if="current" class="ph-detail">
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
        :var-resolver="varResolver" @update:model-value="onValue" />
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
import { BUILTIN_VARS, VAR_NAME_RE } from '@/utils/env'
import { toast } from '@/utils/feedback'
import type { KeyValue } from '@/api/types'
import type { VarResolver } from '@/utils/varInfo'
import { copyText } from '@/utils/commonUtil'

/** title：列表标题（如「请求占位符」/「集合占位符」）；varResolver：高亮文本中引用的其它变量。 */
const props = defineProps<{ modelValue: KeyValue[]; title?: string; varResolver?: VarResolver }>()
const emit = defineEmits<{ 'update:modelValue': [value: KeyValue[]] }>()

const HELP_TEXT =
  '在 URL / Params / Headers / Body 中用 {{名称}} 引用占位符。' +
  'JSON Body 的字符串内引用时，换行、制表符、引号等会自动转义；' +
  '同名优先级：请求占位符 > 集合占位符 > 环境变量；占位符文本中也可引用其它变量。' +
  '另有 {{$datetime}}、{{$randomString}} 等内置占位符可直接使用。'

const activeIdx = ref(props.modelValue.length ? 0 : -1)

/** 当前查看的内置占位符（与自定义占位符互斥）。 */
const activeBuiltin = ref<string | null>(null)
const builtin = computed(() => BUILTIN_VARS.find((b) => b.name === activeBuiltin.value) ?? null)
const builtinRef = computed(() => (builtin.value ? `{{${builtin.value.name}}}` : ''))
const sampleSeed = ref(0)
const sample = computed(() => {
  void sampleSeed.value
  return builtin.value ? builtin.value.gen() : ''
})

function refreshSample() {
  sampleSeed.value += 1
}

function selectItem(i: number) {
  activeBuiltin.value = null
  activeIdx.value = i
}

async function copyText2(text: string) {
  try {
    await copyText(text)
    toast.success(`已复制 ${text}`)
  } catch {
    toast.error('复制失败')
  }
}

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
  activeBuiltin.value = null
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
    await copyText(refText.value)
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
  width: 208px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-panel);
  overflow: hidden;

  .ph-list-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
    height: 32px;
    padding: 0 4px 0 10px;
    border-bottom: 1px solid var(--ui-border-soft);
    background: var(--ui-bg-subtle);

    :deep(.arco-btn) {
      height: 22px;
      padding: 0 6px;
      border-radius: var(--ui-radius-sm);
      color: var(--color-text-2);
      font-size: 11.5px;

      &:hover {
        background: var(--ui-bg-hover);
        color: rgb(var(--primary-6));
      }
    }
  }

  .ph-list-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-text-2);
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
    min-height: 26px;
    padding: 3px 6px;
    border-radius: var(--ui-radius-sm);
    cursor: pointer;
    font-size: 12px;
    color: var(--color-text-2);
    transition: background-color 0.12s ease, color 0.12s ease;

    &:hover {
      background: var(--ui-bg-hover);

      .ph-del {
        visibility: visible;
      }
    }

    &.active {
      background: var(--ui-bg-active);
      box-shadow: inset 3px 0 0 rgb(var(--primary-6));

      .ph-name {
        color: rgb(var(--primary-6));
        font-weight: 600;
      }
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
    font-family: var(--ui-font-mono);

    &.invalid {
      color: var(--ui-accent-danger);
    }
  }

  .ph-len {
    flex-shrink: 0;
    font-family: var(--ui-font-mono);
    font-size: 10.5px;
    color: var(--color-text-4);
    font-variant-numeric: tabular-nums;
  }

  .ph-del {
    visibility: hidden;
    flex-shrink: 0;
    color: var(--color-text-4);
    transition: color 0.12s ease;

    &:hover {
      color: var(--ui-accent-danger);
    }
  }

  .ph-empty {
    padding: 22px 8px;
    text-align: center;
    color: var(--color-text-4);
    font-size: 12px;
    line-height: 1.8;
  }

  .ph-group-title {
    margin: 8px 2px 4px;
    padding-top: 6px;
    border-top: 1px dashed var(--ui-border);
    font-family: var(--ui-font-mono);
    font-size: 10.5px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--color-text-4);
  }

  .ph-builtin-icon {
    flex-shrink: 0;
    font-size: 12px;
    color: var(--ui-accent-warm);
  }
}

.ph-builtin-detail {
  .ph-builtin-name {
    font-family: var(--ui-font-mono);
    font-size: 13.5px;
    font-weight: 600;
    color: var(--color-text-1);
  }

  .ph-builtin-body {
    flex: 1;
    min-height: 0;
    overflow: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px;
    border: 1px solid var(--ui-border);
    border-radius: var(--ui-radius-md);
    background: var(--ui-bg-panel);
    font-size: 12.5px;
    color: var(--color-text-2);
  }

  .ph-builtin-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .ph-builtin-label {
    width: 34px;
    flex-shrink: 0;
    font-size: 11.5px;
    color: var(--color-text-4);
  }

  .ph-builtin-sample {
    font-family: var(--ui-font-mono);
    font-size: 12px;
    padding: 3px 8px;
    border-radius: var(--ui-radius-sm);
    background: rgba(var(--primary-6), 0.1);
    color: rgb(var(--primary-6));
    word-break: break-all;
  }

  .ph-help-text {
    margin-top: 4px;
    padding-top: 10px;
    border-top: 1px dashed var(--ui-border);
    color: var(--color-text-3);
    font-size: 11.5px;
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

    :deep(.arco-btn) {
      height: 22px;
      padding: 0 6px;
      border-radius: var(--ui-radius-sm);
      color: var(--color-text-3);

      &:hover {
        background: var(--ui-bg-hover);
        color: rgb(var(--primary-6));
      }
    }
  }

  .ph-key-input {
    width: 240px;

    :deep(.arco-input-wrapper) {
      background: var(--ui-bg-subtle);
      font-family: var(--ui-font-mono);
      font-size: 12px;
    }
  }

  .ph-ref {
    font-family: var(--ui-font-mono);
    font-size: 11.5px;
    padding: 2px 7px;
    border: 1px solid rgba(212, 136, 6, 0.28);
    border-radius: var(--ui-radius-sm);
    background: var(--ui-accent-warm-bg);
    color: var(--ui-accent-warm);
    cursor: pointer;
    transition: filter 0.12s ease;

    &:hover {
      filter: brightness(1.08);
    }
  }

  .ph-error {
    color: var(--ui-accent-danger);
    font-size: 11.5px;
  }

  .ph-help {
    margin-left: auto;
    color: var(--color-text-4);
    cursor: help;
    transition: color 0.12s ease;

    &:hover {
      color: rgb(var(--primary-6));
    }
  }
}

.ph-detail-empty {
  align-items: center;
  justify-content: center;

  .ph-help-text {
    max-width: 420px;
    color: var(--color-text-4);
    font-size: 12px;
    line-height: 1.8;
    text-align: center;
  }
}
</style>
