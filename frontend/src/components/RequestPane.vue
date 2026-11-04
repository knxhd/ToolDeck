<template>
  <div class="request-pane">
    <a-tabs v-model:active-key="activeKey" class="req-tabs">
      <!-- Body 工具栏：仅在 Body tab 下显示在标签栏右侧；Prettify 仅 JSON 时显示 -->
      <template #extra>
        <div v-if="activeKey === 'body'" class="body-extra">
          <a-dropdown @select="onBodyTypeChange" position="br">
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
          <a-button v-if="tab.request.body_type === 'json'" size="small" type="text" @click="prettify">
            Prettify
          </a-button>
        </div>
        <!-- 文档工具栏：编辑 / 分屏 / 预览 切换 + 全屏 -->
        <div v-else-if="activeKey === 'docs'" class="body-extra">
          <a-radio-group v-model="docMode" type="button" size="small">
            <a-radio value="edit">编辑</a-radio>
            <a-radio value="split">分屏</a-radio>
            <a-radio value="preview">预览</a-radio>
          </a-radio-group>
          <a-button size="small" type="text" title="全屏编辑" @click="docFullscreen = true">
            <template #icon><icon-fullscreen /></template>
          </a-button>
        </div>
      </template>
      <a-tab-pane key="params" title="Params">
        <KeyValueEditor v-model="tab.request.params" bulk :var-resolver="varResolver" />
      </a-tab-pane>
      <a-tab-pane key="headers" title="Headers">
        <KeyValueEditor v-model="tab.request.headers" bulk :var-resolver="varResolver" />
      </a-tab-pane>
      <a-tab-pane key="body" title="Body">
        <MonacoEditor v-if="tab.request.body_type !== 'none' && tab.request.body_type !== 'form-data'"
          v-model="tab.request.body" :language="tab.request.body_type === 'json' ? 'json' : 'plaintext'" fill
          :var-resolver="varResolver" />
        <FormDataEditor v-else-if="tab.request.body_type === 'form-data'" :model-value="formItems"
          @update:model-value="onFormChange" />
        <a-empty v-else description="无 Body" style="padding: 12px 0" />
      </a-tab-pane>
      <a-tab-pane key="placeholders">
        <template #title>
          占位符<span v-if="placeholderCount" class="tab-count">{{ placeholderCount }}</span>
        </template>
        <PlaceholderEditor v-model="placeholders" title="请求占位符" :var-resolver="varResolver" />
      </a-tab-pane>
      <a-tab-pane key="docs">
        <template #title>
          文档<span v-if="docs.trim()" class="tab-dot"></span>
        </template>
        <DocumentEditor v-model="docs" v-model:mode="docMode" v-model:fullscreen="docFullscreen"
          :title="`${tab.title} · 接口文档`" />
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
import FormDataEditor from '@/components/FormDataEditor.vue'
import { buildVarResolver } from '@/utils/varInfo'
import DocumentEditor from '@/components/DocumentEditor.vue'
import { buildQueryString, parseUrlQuery } from '@/utils/parseCurl'
import { toast } from '@/utils/feedback'
import type { BodyType, DocMode, FormDataItem, KeyValue, OpenTab } from '@/api/types'

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

/** 编辑器占位符高亮 / 悬停说明所用的解析函数（环境、集合占位符、请求占位符变化时自动更新）。 */
const varResolver = computed(() => buildVarResolver(props.tab.request.placeholders))

/** 接口文档（Markdown）；旧数据没有该字段，内容未变时不写回，避免误标未保存。 */
const docs = computed<string>({
  get: () => props.tab.request.docs ?? '',
  set: (v) => {
    if (v === (props.tab.request.docs ?? '')) return
    props.tab.request.docs = v
  },
})

/** 文档显示模式：已有文档默认预览，否则默认分屏便于边写边看。 */
const docMode = ref<DocMode>(docs.value.trim() ? 'preview' : 'split')
/** 文档是否全屏编辑；离开文档标签页时自动恢复。 */
const docFullscreen = ref(false)

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
watch(activeKey, (k) => {
  if (k !== 'docs') docFullscreen.value = false
})

/** Form Data 字段：body 中的 JSON 数组（兼容旧数据：缺 type 视为 text，缺 enabled 视为启用）。 */
const formItems = computed<FormDataItem[]>(() => {
  try {
    const arr = JSON.parse(props.tab.request.body || '[]')
    if (!Array.isArray(arr)) return []
    return arr
      .filter((i) => i && typeof i === 'object')
      .map((i): FormDataItem => ({
        key: String(i.key ?? ''),
        value: String(i.value ?? ''),
        enabled: i.enabled !== false,
        type: i.type === 'file' ? 'file' : 'text',
      }))
  } catch {
    return []
  }
})

/** 写回 body：file 字段只保存文件路径。 */
function onFormChange(items: FormDataItem[]) {
  props.tab.request.body = JSON.stringify(
    items.map((p) => ({ key: p.key, value: p.value, type: p.type, enabled: p.enabled })),
  )
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

  .body-extra {
    display: flex;
    align-items: center;
    gap: 6px;
    padding-right: 2px;
  }

  .body-type-btn {
    height: 26px;
    padding: 0 8px;
    border-radius: var(--ui-radius-sm);
    color: var(--color-text-2);
    font-size: 12px;
    font-weight: 600;

    &:hover {
      background: var(--ui-bg-hover);
    }
  }

  .req-tabs {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;

    :deep(.arco-tabs-nav) {
      flex-shrink: 0;
      height: 38px;
      padding: 0 10px;
      border-bottom: 1px solid var(--ui-border-soft);

      &::before {
        display: none;
      }
    }

    :deep(.arco-tabs-nav-extra) {
      height: 38px;
    }

    :deep(.arco-tabs-tab) {
      height: 26px;
      margin: 0 2px 0 0;
      padding: 0 10px;
      border: none;
      border-radius: var(--ui-radius-sm);
      background: transparent;
      color: var(--color-text-3);
      font-size: 12.5px;
      transition: color 0.15s ease, background-color 0.15s ease;

      &:hover {
        color: var(--color-text-1);
        background: var(--ui-bg-hover);
      }
    }

    :deep(.arco-tabs-tab-active) {
      background: var(--ui-bg-active);
      color: rgb(var(--primary-6));
      font-weight: 600;
    }

    :deep(.arco-tabs-ink-bar) {
      display: none;
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
  float: right;
  margin-left: 16px;
  color: rgb(var(--primary-6));
}

.tab-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  margin-left: 5px;
  border-radius: 50%;
  background: rgb(var(--primary-6));
  vertical-align: middle;
}

.tab-count {
  display: inline-block;
  min-width: 15px;
  margin-left: 5px;
  padding: 0 4px;
  border-radius: 7px;
  background: var(--ui-accent-warm-bg, rgba(212, 136, 6, 0.16));
  color: var(--ui-accent-warm);
  font-family: var(--ui-font-mono);
  font-size: 10px;
  font-weight: 700;
  line-height: 15px;
  text-align: center;
  vertical-align: middle;
}
</style>
