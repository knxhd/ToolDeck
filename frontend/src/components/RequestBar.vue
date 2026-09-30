<template>
  <div class="request-bar">
    <a-select v-model="tab.request.method" style="width: 110px">
      <a-option v-for="m in methods" :key="m" :value="m">{{ m }}</a-option>
    </a-select>
    <UrlInput
      v-model="tab.request.url"
      @blur="syncQueryToParams"
      @enter="onSend"
      @curl="applyCurl"
    />
    <a-button v-if="!tab.streaming" type="primary" @click="onSend">发送</a-button>
    <a-button v-else status="danger" type="secondary" @click="$emit('cancel')">停止</a-button>
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
  padding: 8px;
  border-bottom: 1px solid var(--el-border-color);
  flex-shrink: 0;
}
</style>
