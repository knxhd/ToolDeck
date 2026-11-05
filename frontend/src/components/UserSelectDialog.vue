<template>
  <div class="auth-overlay">
    <div class="auth-card">
      <div class="auth-logo">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
          <path d="M4 7h16M4 12h16M4 17h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
      <h2 class="auth-title">ToolDeck</h2>
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

      <div class="auth-foot">数据存储于本地，不出内网</div>
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
  overflow: hidden;
  background: var(--ui-bg-canvas);

  /* 主色束光：用当前主题色渲染氛围，不影响内容可读性 */
  &::before {
    content: '';
    position: absolute;
    width: 780px;
    height: 780px;
    top: -320px;
    left: 50%;
    transform: translateX(-50%);
    border-radius: 50%;
    background: radial-gradient(circle, rgba(var(--primary-6), 0.22) 0%, transparent 62%);
    pointer-events: none;
  }

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background-image: linear-gradient(var(--ui-border-soft) 1px, transparent 1px),
      linear-gradient(90deg, var(--ui-border-soft) 1px, transparent 1px);
    background-size: 44px 44px;
    mask-image: radial-gradient(circle at 50% 34%, #000 0%, transparent 72%);
    opacity: 0.5;
    pointer-events: none;
  }
}

.auth-card {
  position: relative;
  z-index: 1;
  width: 392px;
  padding: 40px 34px 22px;
  border: 1px solid var(--ui-border);
  border-radius: 14px;
  background: var(--ui-bg-panel);
  box-shadow: var(--ui-shadow-2), 0 0 0 1px rgba(255, 255, 255, 0.02) inset;
  text-align: center;
}

.auth-logo {
  width: 52px;
  height: 52px;
  margin: 0 auto 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: linear-gradient(140deg, rgb(var(--primary-5)), rgb(var(--primary-8)));
  color: #fff;
  box-shadow: 0 6px 18px rgba(var(--primary-6), 0.4);
}

.auth-title {
  margin: 0;
  font-size: 1.36em;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--color-text-1);
}

.auth-sub {
  margin: 6px 0 22px;
  font-size: 12.5px;
  color: var(--color-text-3);
}

.field {
  margin-bottom: 10px;

  :deep(.arco-input-wrapper) {
    height: 38px;
    border-radius: var(--ui-radius-md);
    background: var(--ui-bg-subtle);
    font-size: 0.93em;

    &:hover {
      background: var(--ui-bg-panel);
    }
  }
}

.auth-error {
  min-height: 16px;
  margin-bottom: 8px;
  padding: 6px 10px;
  border-radius: var(--ui-radius-sm);
  background: var(--ui-accent-danger-bg);
  color: var(--ui-accent-danger);
  font-size: 11.5px;
  line-height: 1.5;
  text-align: left;
}

.submit-btn {
  height: 38px;
  margin-top: 4px;
  border-radius: var(--ui-radius-md);
  font-size: 13.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.auth-switch {
  margin-top: 16px;
  font-size: 12.5px;
  color: var(--color-text-3);

  :deep(.arco-link) {
    font-size: 12.5px;
    font-weight: 500;
  }
}

.auth-foot {
  margin-top: 22px;
  padding-top: 14px;
  border-top: 1px solid var(--ui-border-soft);
  color: var(--color-text-4);
  font-size: 0.79em;
  letter-spacing: 0.02em;
}
</style>
