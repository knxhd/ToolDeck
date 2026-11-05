<template>
  <div class="request-pane">
    <a-tabs v-model:active-key="tabKey" class="req-tabs" :lazy-load="true" :destroy-on-hide="true">
      <!-- Body 工具栏：仅在 Body tab 下显示在标签栏右侧；Prettify 仅 JSON 时显示 -->
      <template #extra>
        <div class="req-extra">
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
              格式化
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
      <a-tab-pane key="auth" title="Auth">
        <div class="auth-pane">
          <a-select v-model="auth.type" size="small" style="width: 200px">
            <a-option value="none">无</a-option>
            <a-option value="bearer">Bearer Token</a-option>
            <a-option value="basic">Basic Auth</a-option>
            <a-option value="apikey">API Key</a-option>
          </a-select>

          <div v-if="auth.type === 'bearer'" class="auth-form">
            <div class="auth-row">
              <label>Token</label>
              <MaskedInput :model-value="auth.token || ''" @update:model-value="auth.token = $event" placeholder="输入 Token，自动加 Authorization: Bearer <token>" />
            </div>
          </div>

          <div v-else-if="auth.type === 'basic'" class="auth-form">
            <div class="auth-row">
              <label>用户名</label>
              <a-input v-model="auth.username" placeholder="用户名" />
            </div>
            <div class="auth-row">
              <label>密码</label>
              <MaskedInput :model-value="auth.password || ''" @update:model-value="auth.password = $event" password placeholder="密码" />
            </div>
          </div>

          <div v-else-if="auth.type === 'apikey'" class="auth-form">
            <div class="auth-row">
              <label>Header 名</label>
              <a-input v-model="auth.key" placeholder="X-API-Key" />
            </div>
            <div class="auth-row">
              <label>值</label>
              <MaskedInput :model-value="auth.value || ''" @update:model-value="auth.value = $event" placeholder="API Key" />
            </div>
            <div class="auth-row">
              <label>位置</label>
              <a-radio-group v-model="auth.addTo" type="button" size="small">
                <a-radio value="header">Header</a-radio>
                <a-radio value="query">Query</a-radio>
              </a-radio-group>
            </div>
          </div>

          <p v-if="auth.type === 'none'" class="auth-hint muted">不使用鉴权。如需在 Header 手动填写，请到 Headers 页签。</p>
          <p v-else class="auth-hint muted">发送请求时自动注入对应 Header，可用 <span v-pre>{{变量}}</span> 引用环境变量。</p>
        </div>
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
      <!-- 批量测试：放在标签栏左侧末尾，点击只打开抽屉，不切换当前标签 -->
      <a-tab-pane :key="BENCH_KEY" title="批量测试" />
    </a-tabs>
    <BenchDrawer v-model:visible="benchOpen" :request="tab.request" />
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
import MaskedInput from '@/components/MaskedInput.vue'
import BenchDrawer from '@/components/BenchDrawer.vue'
import { buildQueryString, parseUrlQuery } from '@/utils/parseCurl'
import { toast } from '@/utils/feedback'
import type { AuthConfig, BodyType, DocMode, FormDataItem, KeyValue, OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()

const benchOpen = ref(false)

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

/** 鉴权配置；旧数据没有该字段，getter 首次访问时补上，保证 v-model 改 .type 时命中响应式对象。 */
const auth = computed<AuthConfig>({
  get: () => {
    if (!props.tab.request.auth) {
      props.tab.request.auth = { type: 'none', addTo: 'header' }
    }
    return props.tab.request.auth
  },
  set: (v) => {
    props.tab.request.auth = v
  },
})

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

/** 「批量测试」伪标签：点击时仅打开抽屉，保持当前标签不变。 */
const BENCH_KEY = '__bench'
const tabKey = computed<string>({
  get: () => activeKey.value,
  set: (k) => {
    if (k === BENCH_KEY) {
      benchOpen.value = true
      return
    }
    activeKey.value = k
  },
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
    font-size: 0.86em;
    font-weight: 600;

    &:hover {
      background: var(--ui-bg-hover);
    }
  }

  .req-tabs {
    flex: 1;
    min-width: 0;
    min-height: 0;
    width: 100%;
    display: flex;
    flex-direction: column;

    // 标签栏左右内边距与内容区一致（12px），使标签底色块与内容左边缘对齐
    :deep(.arco-tabs-nav) {
      flex-shrink: 0;
      height: 38px;
      padding: 0 12px;
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
      font-size: 0.89em;
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
      min-width: 0;
      min-height: 0;
      width: 100%;
      overflow: hidden;
    }

    :deep(.arco-tabs-content-list) {
      height: 100%;
      min-width: 0;
    }

    :deep(.arco-tabs-content-item) {
      height: 100%;
      min-width: 0;
      overflow: hidden;
    }

    :deep(.arco-tabs-content-item-active) {
      display: flex;
      flex-direction: column;
      min-width: 0;
      overflow: hidden;
    }

    /* Params / Headers / Body / Auth / 占位符 / 文档 统一内边距，保证左右完全对称 */
    :deep(.arco-tabs-content-item-active .arco-tabs-pane) {
      flex: 1;
      box-sizing: border-box;
      width: 100%;
      min-width: 0;
      min-height: 0;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      padding: 0 12px 12px;
      /* 子组件自行处理滚动：KV 表格 .kv-rows overflow-y:auto，Monaco fill，DocEditor 内部滚动 */
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
  font-size: 0.71em;
  font-weight: 700;
  line-height: 1.07em;
  text-align: center;
  vertical-align: middle;
}

.req-extra {
  display: flex;
  align-items: center;
  gap: 8px;
}

.auth-pane {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 12px 4px;
}
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 480px;
}
.auth-row {
  display: flex;
  align-items: center;
  gap: 10px;
  label {
    width: 70px;
    flex-shrink: 0;
    font-size: 0.86em;
    color: var(--color-text-2);
  }
}
.auth-hint {
  font-size: 0.86em;
  margin: 0;
}
</style>
