<template>
  <el-dialog :model-value="modelValue" title="系统设置" width="480px" :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)">
    <el-form label-width="80px">
      <el-form-item label="字体">
        <el-select v-model="settings.fontFamily" style="width: 100%">
          <el-option v-for="o in FONT_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="字号">
        <el-select v-model="settings.fontSize" style="width: 100%">
          <el-option v-for="s in FONT_SIZE_OPTIONS" :key="s" :label="s + ' px'" :value="s" />
        </el-select>
      </el-form-item>
      <el-form-item label="主题">
        <el-radio-group v-model="settings.dark">
          <el-radio-button :value="false">浅色</el-radio-button>
          <el-radio-button :value="true">深色</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="预览">
        <div class="preview">The quick brown fox 敏捷的棕色狐狸 123</div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="onReset">恢复默认</el-button>
      <el-button type="primary" @click="emit('update:modelValue', false)">完成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { useSettingsStore, FONT_OPTIONS, FONT_SIZE_OPTIONS } from '@/stores/settings'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean] }>()

const store = useSettingsStore()
const settings = store.settings

function onReset() {
  store.reset()
}
</script>

<style lang="less" scoped>
.preview {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  font-family: var(--app-font-family);
  font-size: var(--app-font-size);
}
</style>
