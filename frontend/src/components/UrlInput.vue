<template>
  <div class="url-input-wrap" ref="wrapRef">
    <!-- 高亮渲染层：显示带颜色的占位符；真实输入框透明在下层 -->
    <div class="highlight-layer" ref="layerRef" @mouseover="onHover" @mouseleave="onLeave"
      @mousedown.prevent>
      <span class="hl-text" v-html="rendered"></span>
      <span v-if="!modelValue" class="hl-placeholder">https://api.example.com/path</span>
    </div>
    <input
      ref="inputRef"
      class="real-input"
      :value="modelValue"
      @input="onInput"
      @scroll="syncScroll"
      @keydown.enter="$emit('enter')"
      @blur="$emit('blur')"
      spellcheck="false"
      autocomplete="off"
    />
    <span v-if="modelValue" class="clear-btn" title="清空" @click="onClear">×</span>

    <!-- 悬停浮层：显示变量当前值 -->
    <div v-if="tip.visible" class="var-tip" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">
      <div class="var-tip-head">
        <span class="var-tip-name">{{ tip.name }}</span>
        <span class="var-tip-badge">Environment</span>
      </div>
      <div class="var-tip-value">
        {{ tip.value === '' ? '(空字符串)' : tip.value }}
        <span class="var-tip-copy" title="复制值" @click="copyValue">⧉</span>
      </div>
      <div v-if="tip.missing" class="var-tip-missing">当前环境未定义该变量</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'

import { useEnvironmentsStore } from '@/stores/environments'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [v: string]; enter: []; blur: [] }>()

const env = useEnvironmentsStore()

const wrapRef = ref<HTMLElement | null>(null)
const layerRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

const PLACEHOLDER_RE = /\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}/g

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

/** 把文本按占位符切分，占位符包成 <span class="env-var">。 */
const rendered = computed(() => {
  const text = props.modelValue || ''
  let out = ''
  let last = 0
  for (const m of text.matchAll(new RegExp(PLACEHOLDER_RE.source, 'g'))) {
    const idx = m.index ?? 0
    out += escapeHtml(text.slice(last, idx))
    const name = m[1]
    const missing = !(name in env.vars)
    out += `<span class="env-var${missing ? ' missing' : ''}" data-var="${escapeHtml(name)}">${escapeHtml(m[0])}</span>`
    last = idx + m[0].length
  }
  out += escapeHtml(text.slice(last))
  return out
})

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
  nextTick(syncScroll)
}

function syncScroll() {
  if (inputRef.value && layerRef.value) {
    layerRef.value.scrollLeft = inputRef.value.scrollLeft
  }
}

function onClear() {
  emit('update:modelValue', '')
  inputRef.value?.focus()
}

// ---- 悬停 tooltip ----
const tip = ref({ visible: false, x: 0, y: 0, name: '', value: '', missing: false })

function onHover(e: MouseEvent) {
  const target = (e.target as HTMLElement).closest('.env-var') as HTMLElement | null
  if (!target || !wrapRef.value) {
    tip.value.visible = false
    return
  }
  const name = target.dataset.var || ''
  const rect = target.getBoundingClientRect()
  const wrapRect = wrapRef.value.getBoundingClientRect()
  const val = env.vars[name] ?? ''
  tip.value = {
    visible: true,
    x: rect.left - wrapRect.left,
    y: rect.bottom - wrapRect.top + 8,
    name,
    value: val,
    missing: !(name in env.vars),
  }
}

function onLeave() {
  tip.value.visible = false
}

async function copyValue() {
  try {
    await navigator.clipboard.writeText(tip.value.value)
  } catch {
    /* 忽略剪贴板权限错误 */
  }
}
</script>

<style lang="less" scoped>
.url-input-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  border: 1px solid var(--arco-color-border-2, #e5e6eb);
  border-radius: 2px;
  background: var(--arco-color-bg-2, #fff);
  transition: border-color 0.1s;
  height: 32px;

  &:focus-within {
    border-color: rgb(var(--primary-6, 22, 93, 255));
    box-shadow: 0 0 0 2px rgb(var(--primary-1, 234, 244, 255));
  }
}

/* 高亮层与输入框共用同样的字体/内边距/换行，保证文字对齐 */
.highlight-layer,
.real-input {
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  padding: 4px 32px 4px 11px;
  white-space: nowrap;
  letter-spacing: normal;
  word-spacing: normal;
  text-indent: 0;
}

.highlight-layer {
  position: absolute;
  inset: 0;
  overflow-x: auto;
  overflow-y: hidden;
  pointer-events: none;
  color: var(--arco-color-text-1, #1d2129);
  scrollbar-width: none;
  z-index: 1;

  &::-webkit-scrollbar { display: none; }
}

.hl-text { display: inline; }

.hl-placeholder {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--arco-color-text-4, #c9cdd4);
  pointer-events: none;
}

.real-input {
  position: absolute;
  inset: 0;
  width: 100%;
  background: transparent;
  border: none;
  outline: none;
  color: transparent;
  caret-color: var(--arco-color-text-1, #1d2129);
  overflow-x: auto;
  overflow-y: hidden;
  margin: 0;
  z-index: 0;
}

/* 占位符高亮色：琥珀色 pill，和普通 URL 文字区分 */
.hl-text :deep(.env-var) {
  background: rgba(255, 176, 32, 0.22);
  color: #d48806;
  border-radius: 3px;
  padding: 0 2px;
  margin: 0 -2px;
  pointer-events: auto;
  cursor: default;

  &.missing {
    background: rgba(245, 63, 63, 0.18);
    color: #f53f3f;
  }
}

.clear-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  color: var(--arco-color-text-3, #86909c);
  font-size: 14px;
  padding: 0 4px;
  z-index: 2;

  &:hover { color: var(--arco-color-text-1, #1d2129); }
}

.var-tip {
  position: absolute;
  z-index: 1000;
  background: rgba(30, 30, 32, 0.96);
  color: #fff;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 12px;
  min-width: 180px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  pointer-events: auto;
}

.var-tip-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.var-tip-name {
  font-weight: 600;
  font-family: ui-monospace, 'JetBrains Mono', Menlo, monospace;
}

.var-tip-badge {
  font-size: 11px;
  color: #4080ff;
  border: 1px solid #4080ff;
  border-radius: 3px;
  padding: 0 4px;
}

.var-tip-value {
  font-family: ui-monospace, 'JetBrains Mono', Menlo, monospace;
  word-break: break-all;
  display: flex;
  align-items: center;
  gap: 6px;
}

.var-tip-copy {
  cursor: pointer;
  opacity: 0.7;
  &:hover { opacity: 1; }
}

.var-tip-missing {
  margin-top: 4px;
  color: #f53f3f;
  font-size: 11px;
}
</style>
