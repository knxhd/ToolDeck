<template>
  <div class="request-pane">
    <a-tabs v-model:active-key="activeKey" class="req-tabs">
      <a-tab-pane key="params" title="Params">
        <KeyValueEditor v-model="tab.request.params" bulk />
      </a-tab-pane>
      <a-tab-pane key="headers" title="Headers">
        <KeyValueEditor v-model="tab.request.headers" bulk />
      </a-tab-pane>
      <a-tab-pane key="body" title="Body">
        <div class="body-toolbar">
          <a-dropdown @select="onBodyTypeChange">
            <a-button size="small" type="text" class="body-type-btn">
              {{ bodyTypeLabel }} <icon-down />
            </a-button>
            <template #content>
              <a-doption v-for="opt in bodyOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
                <span class="selected-opt-span" v-if="opt.value === tab.request.body_type">✓ </span>
              </a-doption>
            </template>
          </a-dropdown>
          <a-button size="small" @click="prettify" type="text"
            :disabled="tab.request.body_type === 'none' || tab.request.body_type === 'form-data'">
            Prettify
          </a-button>
        </div>
        <MonacoEditor v-if="tab.request.body_type !== 'none' && tab.request.body_type !== 'form-data'"
          v-model="tab.request.body" :language="tab.request.body_type === 'json' ? 'json' : 'plaintext'" fill />
        <KeyValueEditor v-else-if="tab.request.body_type === 'form-data'" :model-value="formPairs"
          @update:model-value="onFormChange" />
        <a-empty v-else description="无 Body" style="padding: 12px 0" />
      </a-tab-pane>
      <a-tab-pane key="placeholders">
        <template #title>
          占位符<span v-if="placeholderCount" class="tab-count">{{ placeholderCount }}</span>
        </template>
        <PlaceholderEditor v-model="placeholders" title="请求占位符" />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { jsonrepair } from 'jsonrepair'
import MonacoEditor from '@/components/MonacoEditor.vue'
import KeyValueEditor from '@/components/KeyValueEditor.vue'
import PlaceholderEditor from '@/components/PlaceholderEditor.vue'
import { buildQueryString, parseUrlQuery } from '@/utils/parseCurl'
import { toast } from '@/utils/feedback'
import type { BodyType, KeyValue, OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()

const bodyOptions: Array<{ value: BodyType; label: string }> = [
  { value: 'none', label: 'None' },
  { value: 'json', label: 'JSON' },
  { value: 'raw', label: 'Raw' },
  { value: 'form-data', label: 'Form Data' },
]

const bodyTypeLabel = computed(
  () => bodyOptions.find((o) => o.value === props.tab.request.body_type)?.label || 'No Body',
)

/** 请求级占位符（旧数据可能没有该字段）。 */
const placeholders = computed<KeyValue[]>({
  get: () => props.tab.request.placeholders ?? [],
  set: (v) => {
    props.tab.request.placeholders = v
  },
})

const placeholderCount = computed(() => placeholders.value.filter((p) => p.enabled && p.key).length)

function onBodyTypeChange(v: string | number | Record<string, unknown> | undefined) {
  props.tab.request.body_type = String(v) as BodyType
}

function prettify() {
  const r = props.tab.request
  if (r.body_type === 'json') {
    try {
      const fixedJsonStr = jsonrepair(r.body)
      const obj = JSON.parse(fixedJsonStr)
      r.body = JSON.stringify(obj, null, 2)
      toast.success('已格式化 JSON')
    } catch {
      toast.error('JSON 语法错误，无法格式化')
    }
  } else if (r.body_type === 'raw') {
    try {
      r.body = JSON.stringify(JSON.parse(r.body || ''), null, 2)
      r.body_type = 'json'
      toast.success('已按 JSON 格式化')
    } catch {
      toast.info('Raw 文本暂不支持格式化')
    }
  }
}

/** 是否已有实际 body 内容（用于决定默认打开的 tab）。 */
const hasBody = computed(() => {
  const r = props.tab.request
  if (r.body_type === 'none') return false
  if (r.body_type === 'form-data') {
    try {
      const arr = JSON.parse(r.body || '[]')
      return arr.some((i: { key?: string; value?: string }) => i && (i.key || i.value))
    } catch {
      return false
    }
  }
  return !!r.body?.trim()
})

/** 打开请求时按实际情况选默认 tab：有 body 进 Body，否则进 Params。 */
const activeKey = ref(hasBody.value ? 'body' : 'params')

const formPairs = computed<KeyValue[]>(() => {
  try {
    const arr = JSON.parse(props.tab.request.body || '[]')
    return arr.map((i: { key: string; value: string }) => ({ key: i.key, value: i.value, enabled: true }))
  } catch {
    return []
  }
})

function onFormChange(pairs: KeyValue[]) {
  props.tab.request.body = JSON.stringify(pairs.map((p) => ({ key: p.key, value: p.value })))
}

/** Params 表编辑 → 反向同步 URL 的 query 部分（Postman 式；URL 程序性更新不会触发输入框 blur，无循环）。 */
watch(
  () => props.tab.request.params,
  (pairs) => {
    const r = props.tab.request
    const { baseUrl } = parseUrlQuery(r.url)
    const query = buildQueryString(pairs || [])
    const next = query ? `${baseUrl}?${query}` : baseUrl
    if (next !== r.url) r.url = next
  },
  { deep: true },
)
</script>

<style lang="less" scoped>
.request-pane {
  display: flex;
  flex-direction: column;
  height: 100%;

  .body-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 0 8px;
  }

  .body-type-btn {
    font-weight: 600;
  }

  .req-tabs {
    flex: 1;
    min-height: 0;
    padding: 0 8px;
    display: flex;
    flex-direction: column;

    :deep(.arco-tabs-nav) {
      flex-shrink: 0;
    }

    :deep(.arco-tabs-content) {
      flex: 1;
      min-height: 0;
      overflow: hidden;
    }

    :deep(.arco-tabs-content-list) {
      height: 100%;
    }

    :deep(.arco-tabs-content-item) {
      height: 100%;
      overflow: auto;
    }

    :deep(.arco-tabs-content-item-active) {
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    :deep(.arco-tabs-content-item-active .arco-tabs-pane) {
      flex: 1;
      min-height: 0;
      display: flex;
      flex-direction: column;
      overflow: auto;
      /* 参数/请求头列表超高时在此滚动；Monaco fill 模式占满高度不触发 */
    }
  }
}

.selected-opt-span {
  margin-left: 16px;
}

.tab-count {
  margin-left: 4px;
  padding: 0 5px;
  font-size: 11px;
  line-height: 16px;
  border-radius: 8px;
  background: rgba(255, 176, 32, 0.22);
  color: #d48806;
}
</style>
