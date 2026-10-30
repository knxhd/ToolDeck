<template>
  <div class="auth-overlay">
    <div class="auth-card">
      <div class="auth-logo">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
          <path d="M4 7h16M4 12h16M4 17h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
      <h2 class="auth-title">API Tool</h2>
      <p class="auth-sub">{{ mode === 'login' ? '登录你的账号' : '创建新账号' }}</p>

      <div class="field">
        <a-input v-if="mode === 'register'" v-model="displayName" size="large" placeholder="昵称（可选）" :max-length="20" />
      </div>
      <div class="field">
        <a-input v-model="username" size="large" placeholder="用户名" :max-length="32" allow-clear />
      </div>
      <div class="field">
        <a-input-password
          v-model="password"
          size="large"
          :placeholder="mode === 'register' ? '密码（至少10位，含字母数字特殊字符）' : '密码'"
          :max-length="64"
          @press-enter="onSubmit"
        />
      </div>

      <div v-if="errorMsg" class="auth-error">{{ errorMsg }}</div>

      <a-button type="primary" long size="large" :loading="loading" class="submit-btn" @click="onSubmit">
        {{ mode === 'login' ? '登录' : '注册并进入' }}
      </a-button>

      <div class="auth-switch">
        <span v-if="mode === 'login'">还没有账号？</span>
        <span v-else>已经有账号了？</span>
        <a-link @click="toggleMode">
          {{ mode === 'login' ? '注册' : '去登录' }}
        </a-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { useUserStore } from '@/stores/user'

const emit = defineEmits<{ (e: 'done'): void }>()

const user = useUserStore()
const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const displayName = ref('')
const loading = ref(false)
const errorMsg = ref('')

function toggleMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  errorMsg.value = ''
}

async function onSubmit() {
  errorMsg.value = ''
  const u = username.value.trim()
  const p = password.value
  if (!u) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (!p) {
    errorMsg.value = '请输入密码'
    return
  }
  if (mode.value === 'register') {
    if (p.length < 10) {
      errorMsg.value = '密码至少 10 位'
      return
    }
    if (!/^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{10,}$/.test(p)) {
      errorMsg.value = '密码必须同时包含字母、数字和特殊字符'
      return
    }
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      await user.login(u, p)
    } else {
      await user.register(u, p, displayName.value.trim())
    }
    emit('done')
  } catch (err: any) {
    errorMsg.value = err.message || String(err)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-overlay {
  position: fixed;
  inset: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-fill-2, rgba(0, 0, 0, 0.6));
  backdrop-filter: blur(4px);
}
.auth-card {
  width: 380px;
  padding: 36px 32px 24px;
  background: var(--color-bg-2, #1f1f1f);
  border: 1px solid var(--color-border-2, #333);
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
  text-align: center;
}
.auth-logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: var(--color-primary-light-1, #165dff);
  color: #fff;
}
.auth-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-1);
}
.auth-sub {
  margin: 6px 0 20px;
  font-size: 13px;
  color: var(--color-text-3);
}
.auth-card :deep(.arco-form-item) {
  margin-bottom: 12px;
}
.field {
  margin-bottom: 12px;
}
.auth-error {
  color: rgb(var(--danger-6));
  font-size: 12px;
  text-align: left;
  margin-bottom: 8px;
  min-height: 16px;
}
.submit-btn {
  margin-top: 4px;
}
.auth-switch {
  margin-top: 16px;
  font-size: 13px;
  color: var(--color-text-3);
}
</style>
