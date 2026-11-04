<template>
  <div class="request-bar">
    <!-- 方法 + URL 合并为一个输入组，聚焦时整组高亮 -->
    <div class="url-group">
      <a-dropdown trigger="click" @select="onMethodSelect">
        <button type="button" class="method-trigger" :class="'m-' + tab.request.method.toLowerCase()">
          <span class="method-text">{{ tab.request.method }}</span>
          <icon-down class="caret" />
        </button>
        <template #content>
          <a-doption v-for="m in methods" :key="m" :value="m">
            <span class="method-pill" :class="'m-' + m.toLowerCase()">{{ m }}</span>
          </a-doption>
        </template>
      </a-dropdown>
      <span class="url-divider"></span>
      <UrlInput
        v-model="tab.request.url"
        :request="tab.request"
        @blur="syncQueryToParams"
        @enter="onSend"
        @curl="applyCurl"
      />
    </div>
    <a-button v-if="!tab.streaming" type="primary" class="send-btn" @click="onSend">发送</a-button>
    <a-button v-else status="danger" type="secondary" class="send-btn" @click="$emit('cancel')">停止</a-button>
  </div>
</template>

<script setup lang="ts">
import UrlInput from '@/components/UrlInput.vue'
import { parseUrlQuery } from '@/utils/parseCurl'
import type { ParsedCurl } from '@/utils/parseCurl'
import { toast } from '@/utils/feedback'
import type { HttpMethod, OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()
const emit = defineEmits<{ send: []; cancel: []; save: [] }>()

const methods: HttpMethod[] = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

/** 方法下拉选择：只改方法，不动其它字段。 */
function onMethodSelect(v: string | number | Record<string, unknown> | undefined) {
  props.tab.request.method = String(v) as HttpMethod
}

function onSend() {
  syncQueryToParams()
  emit('send')
}

/** URL 失焦/发送时：自动把 URL 中 ?query 解析到 Params；URL 输入框保留完整 URL（Postman 式双向同步）。 */
function syncQueryToParams() {
  const r = props.tab.request
  if (!r.url || !r.url.includes('?')) return
  const { params } = parseUrlQuery(r.url)
  if (!params.length) return
  // 若 Params 表已与 URL query 一致则跳过（避免重复解析/重复提示）
  const current = (r.params || []).filter((p) => p.enabled && p.key)
  const same =
    current.length === params.length &&
    current.every((p, i) => p.key === params[i].key && p.value === params[i].value)
  if (same) return
  r.params = [...params, { key: '', value: '', enabled: true }]
  emit('save')
  toast.success(`已解析 ${params.length} 个 URL 参数到 Params`)
}

/** UrlInput 粘贴 curl 后回调：把解析结果写回请求。 */
function applyCurl(parsed: ParsedCurl) {
  const r = props.tab.request
  r.method = parsed.method as HttpMethod
  // URL 已由 UrlInput 通过 v-model 写回，这里同步 headers/params/body
  r.headers = parsed.headers.length ? parsed.headers : [{ key: '', value: '', enabled: true }]
  r.params = parsed.params.length ? parsed.params : [{ key: '', value: '', enabled: true }]
  r.body_type = parsed.bodyType
  r.body = parsed.body
  emit('save')
}
</script>

<style lang="less" scoped>
.request-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  height: 48px;
  padding: 0 10px;
  background: var(--ui-bg-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
}

/* 输入组：方法 + URL 共用一层边框 */
.url-group {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  height: 32px;
  padding-right: 2px;
  background: var(--ui-bg-subtle);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;

  &:focus-within {
    background: var(--ui-bg-panel);
    border-color: rgb(var(--primary-6));
    box-shadow: 0 0 0 3px rgba(var(--primary-6), 0.12);
  }
}

.method-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  height: 100%;
  padding: 0 8px 0 10px;
  border: none;
  background: transparent;
  border-radius: var(--ui-radius-sm);
  cursor: pointer;
  font-family: var(--ui-font-mono);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--color-text-1);

  &:hover {
    background: var(--ui-bg-hover);
  }

  .caret {
    font-size: 10px;
    color: var(--color-text-3);
  }

  // 彩色请求方法
  &.m-get {
    color: var(--ui-method-get);
  }
  &.m-post {
    color: var(--ui-method-post);
  }
  &.m-put {
    color: var(--ui-method-put);
  }
  &.m-patch {
    color: var(--ui-method-patch);
  }
  &.m-delete {
    color: var(--ui-method-delete);
  }
  &.m-head {
    color: var(--ui-method-head);
  }
  &.m-options {
    color: var(--ui-method-options);
  }
}

.url-divider {
  flex-shrink: 0;
  width: 1px;
  height: 16px;
  margin-right: 2px;
  background: var(--ui-border);
}

.send-btn {
  height: 32px;
  min-width: 84px;
  border-radius: var(--ui-radius-md);
  font-weight: 600;
}
</style>
