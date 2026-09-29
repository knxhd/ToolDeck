<template>
  <div class="request-bar">
    <a-select v-model="tab.request.method" style="width: 110px">
      <a-option v-for="m in methods" :key="m" :value="m">{{ m }}</a-option>
    </a-select>
    <a-input
      v-model="tab.request.url"
      placeholder="https://api.example.com/path"
      allow-clear
      @press-enter="onSend"
    />
    <a-button @click="curlDialogVisible = true">导入 curl</a-button>
    <a-button v-if="!tab.streaming" type="primary" @click="onSend">发送</a-button>
    <a-button v-else status="danger" type="secondary" @click="$emit('cancel')">停止</a-button>

    <!-- 从 curl 导入 -->
    <a-modal v-model:visible="curlDialogVisible" title="从 curl 导入" width="640px">
      <a-textarea
        v-model="curlText"
        :auto-size="{ minRows: 10, maxRows: 18 }"
        placeholder="粘贴 curl 命令，例如：&#10;curl -X POST 'https://api.example.com/v1/chat' \&#10;  -H 'Content-Type: application/json' \&#10;  -d '{&quot;model&quot;:&quot;gpt&quot;}'"
      />
      <template #footer>
        <a-button @click="curlDialogVisible = false">取消</a-button>
        <a-button type="primary" @click="applyCurl">解析导入</a-button>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { parseCurl } from '@/utils/parseCurl'
import { toast } from '@/utils/feedback'
import type { HttpMethod, OpenTab } from '@/api/types'

const props = defineProps<{ tab: OpenTab }>()
const emit = defineEmits<{ send: []; cancel: []; save: [] }>()

const methods: HttpMethod[] = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

const curlDialogVisible = ref(false)
const curlText = ref('')

function onSend() {
  emit('send')
}

function applyCurl() {
  try {
    const parsed = parseCurl(curlText.value)
    if (!parsed.url) {
      toast.warning('未识别到 URL，请检查 curl 命令')
      return
    }
    const r = props.tab.request
    r.method = parsed.method as HttpMethod
    r.url = parsed.url
    r.headers = parsed.headers.length ? parsed.headers : [{ key: '', value: '', enabled: true }]
    r.params = parsed.params.length ? parsed.params : [{ key: '', value: '', enabled: true }]
    r.body_type = parsed.bodyType
    r.body = parsed.body
    curlDialogVisible.value = false
    curlText.value = ''
    emit('save')
    toast.success('已从 curl 导入')
  } catch (e) {
    toast.error('解析失败：' + (e as Error).message)
  }
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

  :deep(.arco-input-wrapper) {
    flex: 1;
  }
}
</style>
