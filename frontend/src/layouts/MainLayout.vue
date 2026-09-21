<template>
  <el-container class="main-layout">
    <el-main class="main-content">
      <RouterView />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<style scoped>
.main-layout {
  height: 100vh;
}
.main-content {
  padding: 0;
  overflow: hidden;
}
</style>
