<template>
  <div class="user-overlay">
    <div class="user-card">
      <div class="user-logo">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
          <path d="M4 7h16M4 12h16M4 17h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
      <h2 class="user-title">API Tool</h2>
      <p class="user-sub">输入你的名字，开始调试</p>

      <a-input
        v-model="name"
        size="large"
        placeholder="你的用户名"
        :max-length="32"
        allow-clear
        :disabled="loading"
        @press-enter="onSubmit"
      />
      <div v-if="errorMsg" class="user-error">{{ errorMsg }}</div>

      <a-button
        type="primary"
        long
        size="large"
        :loading="loading"
        @click="onSubmit"
      >进入</a-button>

      <p class="user-tip">用户名仅保存在本机浏览器，用于隔离你自己的接口集合和历史</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Modal } from '@arco-design/web-vue'

import { useUserStore } from '@/stores/user'

const emit = defineEmits<{ (e: 'done'): void }>()

const user = useUserStore()
const name = ref(user.name || '')
const loading = ref(false)
const errorMsg = ref('')

async function onSubmit() {
  errorMsg.value = ''
  const n = name.value.trim()
  if (!n) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (!/^[A-Za-z0-9_.-]{1,32}$/.test(n)) {
    errorMsg.value = '用户名只能包含字母数字下划线短横点，长度 1-32'
    return
  }
  loading.value = true
  try {
    const exists = await user.checkExists(n)
    if (exists) {
      Modal.warning({
        title: `用户名「${n}」已被使用`,
        content: '继续将看到该用户已有的集合和历史记录，确认使用这个名字吗？',
        okText: '继续使用',
        cancelText: '换一个',
        onOk: () => {
          user.setName(n)
          emit('done')
        },
      })
    } else {
      user.setName(n)
      emit('done')
    }
  } catch (err: any) {
    errorMsg.value = err.message || String(err)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.user-overlay {
  position: fixed;
  inset: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-fill-2, rgba(0, 0, 0, 0.6));
  backdrop-filter: blur(4px);
}
.user-card {
  width: 360px;
  padding: 36px 32px 24px;
  background: var(--color-bg-2, #1f1f1f);
  border: 1px solid var(--color-border-2, #333);
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
  text-align: center;
}
.user-logo {
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
.user-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-1);
}
.user-sub {
  margin: 6px 0 24px;
  font-size: 13px;
  color: var(--color-text-3);
}
.user-card :deep(.arco-input-wrapper) {
  margin-bottom: 8px;
}
.user-error {
  color: rgb(var(--danger-6));
  font-size: 12px;
  text-align: left;
  margin-bottom: 8px;
  min-height: 16px;
}
.user-card :deep(.arco-btn) {
  margin-top: 8px;
}
.user-tip {
  margin: 16px 0 0;
  font-size: 12px;
  color: var(--color-text-3);
  line-height: 1.5;
}
</style>
