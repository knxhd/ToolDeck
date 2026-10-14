<template>
  <div class="url-input-wrap" ref="wrapRef">
    <!-- 高亮渲染层：显示带颜色的占位符；真实输入框透明在下层 -->
    <div class="highlight-layer" ref="layerRef" @mouseover="onHover" @mouseleave="onLeave" @mousedown.prevent>
      <span class="hl-text" v-html="rendered"></span>
      <span v-if="!modelValue" class="hl-placeholder">https://api.example.com/path</span>
    </div>
    <input ref="inputRef" class="real-input" :value="modelValue" @input="onInput" @scroll="syncScroll"
      @keydown="onKeydown" @click="detectTrigger" @keyup="detectTrigger" @blur="onBlur" @paste="onPaste"
      spellcheck="false" autocomplete="off" />
    <span v-if="modelValue" class="clear-btn" title="generate code" @click="generateCode"><icon-code /></span>

    <!-- 变量自动补全浮层 -->
    <div v-if="ac.visible && ac.candidates.length" class="ac-popup">
      <div v-for="(c, i) in ac.candidates" :key="c" class="ac-item" :class="{ active: i === ac.activeIdx }"
        @mousedown.prevent @click="pick(c)">
        {{ c }}
      </div>
    </div>

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

    <!-- 生成调用代码弹框 -->
    <GenerateCodeDialog v-model:visible="codeVisible" :request="codeRequest" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'

import GenerateCodeDialog from '@/components/GenerateCodeDialog.vue'
import { useEnvironmentsStore } from '@/stores/environments'
import { parseCurl } from '@/utils/parseCurl'
import type { ParsedCurl } from '@/utils/parseCurl'
import { toast } from '@/utils/feedback'
import type { HttpRequestData } from '@/api/types'

/** request：完整请求数据，用于生成调用代码；未传时仅按 URL 生成 GET 请求。 */
const props = defineProps<{ modelValue: string; request?: HttpRequestData }>()
const emit = defineEmits<{
  'update:modelValue': [v: string]
  enter: []
  blur: []
  curl: [parsed: ParsedCurl]
}>()

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
  nextTick(() => {
    syncScroll()
    detectTrigger()
  })
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

// ---- 生成调用代码 ----
const codeVisible = ref(false)

const codeRequest = computed<HttpRequestData>(
  () =>
    props.request ?? {
      method: 'GET',
      url: props.modelValue,
      headers: [],
      params: [],
      body_type: 'none',
      body: '',
    },
)

/** 打开「Generate Code」弹框：按当前请求生成 curl / Java / Python 调用代码。 */
function generateCode() {
  closePopup()
  tip.value.visible = false
  codeVisible.value = true
}

// ---- 变量自动补全 ----
const ac = ref({ visible: false, candidates: [] as string[], activeIdx: 0 })

function closePopup() {
  ac.value.visible = false
}

/** 根据光标位置判断是否处于 `{{partial` 状态，并刷新候选。 */
function detectTrigger() {
  const input = inputRef.value
  if (!input) return
  // 没有可用变量时完全不弹
  const keys = Object.keys(env.vars)
  if (!keys.length) {
    closePopup()
    return
  }
  const value = input.value
  const caret = input.selectionStart ?? value.length
  const before = value.slice(0, caret)
  const openIdx = before.lastIndexOf('{{')
  if (openIdx < 0) {
    closePopup()
    return
  }
  const partial = before.slice(openIdx + 2)
  // 已经出现 }} 视为占位符已闭合，不弹
  if (partial.includes('}}')) {
    closePopup()
    return
  }
  // 只允许变量名字符，否则关闭（避免在中文/空格等场景误弹）
  if (/[^\w.-]/.test(partial)) {
    closePopup()
    return
  }
  const q = partial.toLowerCase()
  const candidates = q ? keys.filter((k) => k.toLowerCase().includes(q)) : [...keys]
  ac.value = { visible: true, candidates, activeIdx: 0 }
}

function onKeydown(e: KeyboardEvent) {
  const popupOpen = ac.value.visible && ac.value.candidates.length > 0
  if (popupOpen) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      ac.value.activeIdx = (ac.value.activeIdx + 1) % ac.value.candidates.length
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      const n = ac.value.candidates.length
      ac.value.activeIdx = (ac.value.activeIdx - 1 + n) % n
      return
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      closePopup()
      return
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      pick(ac.value.candidates[ac.value.activeIdx])
      return
    }
  }
  if (e.key === 'Enter') {
    emit('enter')
  }
}

function pick(name: string) {
  const input = inputRef.value
  if (!input) return
  const value = input.value
  const caret = input.selectionStart ?? value.length
  const openIdx = value.slice(0, caret).lastIndexOf('{{')
  if (openIdx < 0) {
    closePopup()
    return
  }
  const before = value.slice(0, openIdx)
  const after = value.slice(caret)
  const next = before + '{{' + name + '}}' + after
  emit('update:modelValue', next)
  closePopup()
  nextTick(() => {
    input.focus()
    const pos = before.length + name.length + 4 // 插到 {{name}} 之后
    input.setSelectionRange(pos, pos)
  })
}

function onBlur() {
  closePopup()
  emit('blur')
}

/** 粘贴时若内容是 curl 命令，拦截默认粘贴并自动解析。 */
function onPaste(e: ClipboardEvent) {
  const text = e.clipboardData?.getData('text') || ''
  if (!text) return
  // 粗判：以 curl 开头，或包含典型 curl 参数
  const looksLikeCurl = /^\s*curl(\s|$)/i.test(text) || /(--url|--request|--header|-X\s)/.test(text)
  if (!looksLikeCurl) return
  e.preventDefault()
  try {
    const parsed = parseCurl(text)
    if (!parsed.url) {
      toast.warning('粘贴的 curl 未识别到 URL')
      return
    }
    emit('update:modelValue', parsed.url)
    emit('curl', parsed)
    toast.success('已从 curl 导入请求')
    closePopup()
    nextTick(() => {
      const input = inputRef.value
      if (input) {
        input.focus()
        input.setSelectionRange(parsed.url.length, parsed.url.length)
      }
    })
  } catch (err) {
    toast.error('curl 解析失败：' + (err as Error).message)
  }
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
  border: 1px solid var(--el-border-color);
  border-radius: 2px;
  background: var(--el-bg-color);
  transition: border-color 0.1s;
  height: 32px;

  &:focus-within {
    border-color: rgb(var(--primary-6));
    box-shadow: 0 0 0 2px rgb(var(--primary-1));
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
  color: var(--el-text-color-primary);
  scrollbar-width: none;
  z-index: 1;

  &::-webkit-scrollbar {
    display: none;
  }
}

.hl-text {
  display: inline;
}

.hl-placeholder {
  position: absolute;
  left: 11px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--el-text-color-placeholder);
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
  caret-color: var(--el-text-color-primary);
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
  color: var(--el-text-color-secondary);
  font-size: 14px;
  padding: 0 4px;
  z-index: 2;

  &:hover {
    color: var(--el-text-color-primary);
  }
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

  &:hover {
    opacity: 1;
  }
}

.var-tip-missing {
  margin-top: 4px;
  color: #f53f3f;
  font-size: 11px;
}

.ac-popup {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  min-width: 220px;
  max-height: 240px;
  overflow-y: auto;
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  z-index: 1100;
  font-size: 13px;
}

.ac-item {
  padding: 6px 10px;
  cursor: pointer;
  font-family: ui-monospace, 'JetBrains Mono', Menlo, monospace;

  &:hover,
  &.active {
    background: var(--el-color-primary-light-9);
  }
}
</style>
