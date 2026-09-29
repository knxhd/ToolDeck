<template>
  <a-layout class="main-layout">
    <a-layout-content class="main-content">
      <RouterView />
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<style lang="less" scoped>
.main-layout {
  height: 100vh;
  .main-content {
    padding: 0;
    overflow: hidden;
  }
}
</style>
