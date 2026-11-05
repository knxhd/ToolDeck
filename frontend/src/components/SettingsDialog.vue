<template>
  <a-modal :visible="modelValue" title="系统设置" width="520px" :mask-closable="false"
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
        <a-select v-model="settings.theme" style="width: 100%">
          <a-optgroup label="浅色系">
            <a-option v-for="t in LIGHT_THEMES" :key="t.id" :value="t.id" :title="t.desc">
              <span class="ui-theme-opt">
                <span class="ui-theme-dot" :style="{ background: t.swatch }"></span>
                <span class="ui-theme-name">{{ t.name }}</span>
              </span>
            </a-option>
          </a-optgroup>
          <a-optgroup label="暗色系">
            <a-option v-for="t in DARK_THEMES" :key="t.id" :value="t.id" :title="t.desc">
              <span class="ui-theme-opt">
                <span class="ui-theme-dot" :style="{ background: t.swatch }"></span>
                <span class="ui-theme-name">{{ t.name }}</span>
              </span>
            </a-option>
          </a-optgroup>
        </a-select>
      </div>
      <div class="form-row form-row-top">
        <span class="form-label">配色</span>
        <div class="accent-list">
          <button v-for="p in ACCENT_PRESETS" :key="p.id" type="button" class="accent-item"
            :class="{ active: settings.accent === p.id }" :style="{ '--swatch': p.base }"
            :title="p.name" @click="settings.accent = p.id">
            <span class="swatch" :style="{ background: p.base }">
              <icon-check v-if="settings.accent === p.id" class="swatch-check" />
            </span>
            <span class="accent-name">{{ p.name }}</span>
          </button>
        </div>
      </div>
      <div class="form-row form-row-top">
        <span class="form-label">Tab数量</span>
        <a-input-number
          v-model="settings.maxTabs"
          :min="store.maxTabsMin"
          :max="store.maxTabsMax"
          :precision="0"
          mode="button"
          style="width: 132px"
        />
        <span class="form-tip">最多同时打开 {{ store.maxTabsMin }}~{{ store.maxTabsMax }} 个</span>
      </div>
      <div class="form-row">
        <span class="form-label">预览</span>
        <div class="preview">The quick brown fox 敏捷的棕色狐狸 123</div>
      </div>
      <div class="form-row form-row-top">
        <span class="form-label">快捷键</span>
        <div class="shortcut-list">
          <div class="shortcut-row"><span class="keys"><kbd>Ctrl</kbd>+<kbd>Enter</kbd></span><span class="desc">发送请求</span></div>
          <div class="shortcut-row"><span class="keys"><kbd>Ctrl</kbd>+<kbd>S</kbd></span><span class="desc">保存请求</span></div>
          <div class="shortcut-row"><span class="keys"><kbd>?</kbd></span><span class="desc">显示快捷键面板</span></div>
        </div>
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
import { ACCENT_PRESETS, DARK_THEMES, LIGHT_THEMES } from '@/utils/theme'

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
  gap: 16px;

  .form-row {
    display: flex;
    align-items: center;
    gap: 12px;

    .form-label {
      width: 58px;
      flex-shrink: 0;
      color: var(--color-text-2);
      font-size: 12.5px;
      font-weight: 500;
    }

    .form-tip {
      flex: 1;
      min-width: 0;
      color: var(--color-text-3);
      font-size: 12px;
      line-height: 1.5;
    }
  }

  .form-row-top {
    align-items: flex-start;

    .form-label {
      line-height: 30px;
    }
  }
}

// ---- 配色预设 ----
.accent-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  width: 100%;
}

.accent-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 8px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);
  color: var(--color-text-2);
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease, color 0.15s ease,
    box-shadow 0.15s ease;

  &:hover {
    background: var(--ui-bg-panel);
    border-color: var(--ui-border-strong);
    color: var(--color-text-1);
  }

  &.active {
    border-color: var(--swatch, rgb(var(--primary-6)));
    background: var(--ui-bg-panel);
    color: var(--color-text-1);
    font-weight: 600;
    box-shadow: 0 0 0 2px rgba(var(--primary-6), 0.14);
  }

  .swatch {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    border-radius: 50%;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.28);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 10px;
  }

  .swatch-check {
    font-size: 10px;
  }

  .accent-name {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
}

.preview {
  flex: 1;
  min-width: 0;
  padding: 9px 12px;
  border: 1px dashed var(--ui-border-strong);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);
  color: var(--color-text-1);
  font-family: var(--app-font-family);
  font-size: var(--app-font-size);
  line-height: 1.5;
}

.shortcut-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);
}
.shortcut-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12.5px;
  .keys {
    display: inline-flex;
    gap: 3px;
    kbd {
      padding: 2px 7px;
      border: 1px solid var(--ui-border);
      border-bottom-width: 2px;
      border-radius: 4px;
      background: var(--ui-bg-panel);
      font-family: var(--ui-font-mono);
      font-size: 11.5px;
      color: var(--color-text-1);
    }
  }
  .desc {
    color: var(--color-text-2);
  }
}
</style>
