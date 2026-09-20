<template>
  <el-container class="main-layout">
    <el-header class="header">
      <div class="logo">API Tool</div>
      <el-menu :default-active="activeIndex" mode="horizontal" :ellipsis="false" router>
        <el-menu-item index="/http">
          <el-icon><Link /></el-icon>
          <span>HTTP</span>
        </el-menu-item>
        <el-menu-item index="/mcp">
          <el-icon><Connection /></el-icon>
          <span>MCP</span>
        </el-menu-item>
        <el-menu-item index="/llm">
          <el-icon><ChatDotRound /></el-icon>
          <span>LLM</span>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><Clock /></el-icon>
          <span>历史</span>
        </el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="main-content">
      <RouterView />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterView } from 'vue-router'
import { ChatDotRound, Clock, Connection, Link } from '@element-plus/icons-vue'

const route = useRoute()
const activeIndex = computed(() => route.path)
</script>

<style scoped>
.main-layout {
  height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  padding: 0;
  background: #fff;
  border-bottom: 1px solid var(--el-border-color);
  height: 56px;
}
.logo {
  font-weight: 700;
  font-size: 18px;
  padding: 0 20px;
  color: var(--el-color-primary);
  white-space: nowrap;
}
.header :deep(.el-menu) {
  border-bottom: none;
  flex: 1;
}
.main-content {
  padding: 0;
  overflow: hidden;
}
</style>
