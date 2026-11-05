<template>
  <div class="masked-input">
    <!-- 空值时：直接用普通输入框，不触发密码解锁 -->
    <a-input
      v-if="!modelValue"
      :model-value="modelValue"
      :placeholder="placeholder"
      allow-clear
      @update:model-value="emit('update:modelValue', $event)"
    />
    <!-- 有值且未解锁：显示掩码，点眼睛需密码 -->
    <template v-else>
      <a-input
        v-if="unlocked"
        :model-value="modelValue"
        :type="password ? 'password' : 'text'"
        :placeholder="placeholder"
        allow-clear
        @update:model-value="emit('update:modelValue', $event)"
      >
        <template #suffix>
          <icon-eye-invisible class="eye" @click="unlocked = false" />
        </template>
      </a-input>
      <a-input
        v-else
        model-value="••••••••••"
        disabled
        @click="askPassword"
      >
        <template #suffix>
          <icon-eye class="eye" @click.stop="askPassword" />
        </template>
      </a-input>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import { toast } from '@/utils/feedback'

withDefaults(
  defineProps<{
    modelValue: string
    password?: boolean
    placeholder?: string
  }>(),
  { password: false, placeholder: '' },
)
const emit = defineEmits<{ 'update:modelValue': [v: string] }>()

const unlocked = ref(false)

function askPassword() {
  const pwd = window.prompt('请输入登录密码以查看敏感字段：')
  if (pwd === null) return
  api.post('/api/auth/verify-password', { password: pwd })
    .then(() => {
      unlocked.value = true
      toast.success('已解锁')
    })
    .catch((err) => {
      toast.error(err.message || '密码错误')
    })
}
</script>

<style scoped>
.masked-input {
  width: 100%;
}
.eye {
  cursor: pointer;
  color: var(--color-text-3);
}
.eye:hover {
  color: rgb(var(--primary-6));
}
</style>
