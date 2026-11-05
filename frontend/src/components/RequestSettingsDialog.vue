<template>
  <a-modal :visible="modelValue" title="请求设置" width="420px" :mask-closable="false"
    @update:visible="(v: boolean) => emit('update:modelValue', v)">
    <div class="req-settings-form">
      <div class="form-row">
        <span class="form-label">超时（秒）</span>
        <a-input-number v-model="request.timeout" :min="1" :max="600" :precision="0"
          mode="button" style="width: 132px" />
        <span class="form-tip">请求等待响应的最大时间</span>
      </div>
      <div class="form-row">
        <span class="form-label">跟随重定向</span>
        <a-switch v-model="request.follow_redirects" />
      </div>
      <div class="form-row">
        <span class="form-label">校验 SSL 证书</span>
        <a-switch v-model="request.verify_ssl" />
      </div>
    </div>
    <template #footer>
      <a-button type="primary" @click="emit('update:modelValue', false)">完成</a-button>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import type { HttpRequestData } from '@/api/types'

defineProps<{ modelValue: boolean; request: HttpRequestData }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()
</script>

<style lang="less" scoped>
.req-settings-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 0;

  .form-row {
    display: flex;
    align-items: center;
    gap: 12px;

    .form-label {
      width: 96px;
      flex-shrink: 0;
      color: var(--color-text-2);
      font-size: 12.5px;
      font-weight: 500;
    }

    .form-tip {
      flex: 1;
      min-width: 0;
      color: var(--color-text-3);
      font-size: 0.86em;
      line-height: 1.5;
    }
  }
}
</style>
