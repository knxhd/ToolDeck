<template>
  <a-modal :visible="modelValue" title="修改密码" width="420px" :mask-closable="false"
    @update:visible="(v: boolean) => emit('update:modelValue', v)">
    <div class="password-form">
      <div class="form-row">
        <span class="form-label">当前密码</span>
        <a-input-password v-model="form.oldPassword" placeholder="请输入当前密码" allow-clear />
      </div>
      <div class="form-row">
        <span class="form-label">新密码</span>
        <a-input-password v-model="form.newPassword" placeholder="至少 10 位，含字母、数字和特殊字符" allow-clear />
      </div>
      <div class="form-row">
        <span class="form-label">确认密码</span>
        <a-input-password v-model="form.confirmPassword" placeholder="再次输入新密码" allow-clear />
      </div>
      <p class="form-tip">
        密码需至少 10 位，且同时包含字母、数字和特殊字符（如 !@#$%）。
      </p>
    </div>

    <template #footer>
      <a-button @click="emit('update:modelValue', false)">取消</a-button>
      <a-button type="primary" :loading="saving" @click="onSubmit">确认修改</a-button>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { useUserStore } from '@/stores/user'
import { toast } from '@/utils/feedback'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()

const user = useUserStore()
const saving = ref(false)
const form = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })

/** 与后端 auth.validate_password 保持一致。 */
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{10,}$/

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    form.oldPassword = ''
    form.newPassword = ''
    form.confirmPassword = ''
  },
)

async function onSubmit() {
  if (!form.oldPassword) {
    toast.warning('请输入当前密码')
    return
  }
  if (!PASSWORD_RE.test(form.newPassword)) {
    toast.warning('新密码至少 10 位，且需包含字母、数字和特殊字符')
    return
  }
  if (form.newPassword === form.oldPassword) {
    toast.warning('新密码不能与当前密码相同')
    return
  }
  if (form.newPassword !== form.confirmPassword) {
    toast.warning('两次输入的新密码不一致')
    return
  }
  saving.value = true
  try {
    await user.changePassword(form.oldPassword, form.newPassword)
    toast.success('密码已修改，下次登录请使用新密码')
    emit('update:modelValue', false)
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '修改失败')
  } finally {
    saving.value = false
  }
}
</script>

<style lang="less" scoped>
.password-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;

  .form-label {
    width: 66px;
    flex-shrink: 0;
    color: var(--color-text-2);
    font-size: 12.5px;
    font-weight: 500;
  }
}

.form-tip {
  margin: 0 0 0 78px;
  color: var(--color-text-3);
  font-size: 11.5px;
  line-height: 1.6;
}
</style>
