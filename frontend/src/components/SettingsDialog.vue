<template>
  <a-modal :visible="modelValue" title="系统设置" width="480px" :mask-closable="false"
    @update:visible="(v: boolean) => emit('update:modelValue', v)">
    <div class="settings-form">
      <div class="form-row">
        <span class="form-label">字体</span>
        <a-select v-model="settings.fontFamily" style="width: 100%">
          <a-option v-for="o in FONT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</a-option>
        </a-select>
      </div>
      <div class="form-row">
        <span class="form-label">字号</span>
        <a-select v-model="settings.fontSize" style="width: 100%">
          <a-option v-for="s in FONT_SIZE_OPTIONS" :key="s" :value="s">{{ s }} px</a-option>
        </a-select>
      </div>
      <div class="form-row">
        <span class="form-label">主题</span>
        <a-radio-group v-model="settings.dark" type="button">
          <a-radio :value="false">浅色</a-radio>
          <a-radio :value="true">深色</a-radio>
        </a-radio-group>
      </div>
      <div class="form-row">
        <span class="form-label">预览</span>
        <div class="preview">The quick brown fox 敏捷的棕色狐狸 123</div>
      </div>
    </div>
    <template #footer>
      <a-button @click="onReset">恢复默认</a-button>
      <a-button type="primary" @click="emit('update:modelValue', false)">完成</a-button>
    </template>
  </a-modal>
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
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 14px;

  .form-row {
    display: flex;
    align-items: center;
    gap: 12px;

    .form-label {
      width: 60px;
      flex-shrink: 0;
      color: var(--el-text-color-primary);
      font-size: 13px;
    }
  }
}
.preview {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  font-family: var(--app-font-family);
  font-size: var(--app-font-size);
}
</style>
