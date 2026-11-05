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
        <span>{{ c }}</span>
        <span v-if="builtinDesc(c)" class="ac-desc">{{ builtinDesc(c) }}</span>
      </div>
    </div>

    <!-- 悬停浮层：显示变量当前值 -->
    <div v-if="tip.visible" class="var-tip" :style="{ left: tip.x + 'px', top: tip.y + 'px' }" @mouseenter="cancelHide"
      @mouseleave="hideTip">
      <div class="var-tip-head">
        <span class="var-tip-name">{{ tip.name }}</span>
        <span class="var-tip-badge">{{ tip.source }}</span>
      </div>
      <div class="var-tip-value">
        <span class="var-tip-value-text">{{ tip.value === '' ? '(空字符串)' : tip.value }}</span>
        <button class="var-tip-copy" title="复制值" @click="copyValue">
          <icon-copy />
        </button>
      </div>
      <div v-if="tip.desc" class="var-tip-desc">{{ tip.desc }}</div>
      <div v-if="tip.missing" class="var-tip-missing">未定义该变量（环境变量 / 占位符）</div>
    </div>

    <!-- 生成调用代码弹框 -->
    <GenerateCodeDialog v-model:visible="codeVisible" :request="codeRequest" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'

import GenerateCodeDialog from '@/components/GenerateCodeDialog.vue'
import { useEnvironmentsStore } from '@/stores/environments'
import { BUILTIN_VARS, PLACEHOLDER_SOURCE, isKnownVar, lookupVar, parseBuiltin } from '@/utils/env'
import { parseCurl } from '@/utils/parseCurl'
import type { ParsedCurl } from '@/utils/parseCurl'
import { toast } from '@/utils/feedback'
import type { HttpRequestData } from '@/api/types'
import { copyText } from '@/utils/commonUtil'

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

const PLACEHOLDER_RE = new RegExp(PLACEHOLDER_SOURCE, 'g')

/** 内置占位符说明（非内置返回空）。 */
function builtinDesc(name: string): string {
  return parseBuiltin(name)?.def.desc ?? ''
}

/** 请求级占位符（启用且有名称）。 */
const placeholderVars = computed<Record<string, string>>(() => {
  const out: Record<string, string> = {}
  for (const p of props.request?.placeholders || []) {
    const key = (p.key || '').trim()
    if (p.enabled && key) out[key] = p.value ?? ''
  }
  return out
})

/** 可用变量（优先级：请求占位符 > 集合占位符 > 环境变量）。 */
const knownVars = computed<Record<string, string>>(() => ({ ...env.scopeVars, ...placeholderVars.value }))

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
    const missing = !isKnownVar(name, knownVars.value)
    const builtin = !missing && !(name in knownVars.value)
    const cls = missing ? ' missing' : builtin ? ' builtin' : ''
    out += `<span class="env-var${cls}" data-var="${escapeHtml(name)}">${escapeHtml(m[0])}</span>`
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
  // 可用变量 = 用户变量 + 内置占位符（内置排在后面）
  const userKeys = Object.keys(knownVars.value)
  const keys = [...userKeys, ...BUILTIN_VARS.map((b) => b.name).filter((n) => !userKeys.includes(n))]
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
  // 只允许变量名字符（含内置占位符的 $ 前缀），否则关闭（避免在中文/空格等场景误弹）
  if (/[^\w.$-]/.test(partial)) {
    closePopup()
    return
  }
  const q = partial.toLowerCase()
  const candidates = q ? keys.filter((k) => k.toLowerCase().includes(q)) : [...keys]
  if (!candidates.length) {
    closePopup()
    return
  }
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
const tip = ref({
  visible: false, x: 0, y: 0, name: '', value: '', missing: false, source: 'Environment', desc: '',
})
let hideTimer: number | null = null

function scheduleHide() {
  cancelHide()
  hideTimer = window.setTimeout(() => {
    tip.value.visible = false
    hideTimer = null
  }, 120)
}
function cancelHide() {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
}
function hideTip() {
  tip.value.visible = false
}

function onHover(e: MouseEvent) {
  const target = (e.target as HTMLElement).closest('.env-var') as HTMLElement | null
  if (!target || !wrapRef.value) {
    scheduleHide()
    return
  }
  cancelHide()
  const name = target.dataset.var || ''
  const rect = target.getBoundingClientRect()
  const wrapRect = wrapRef.value.getBoundingClientRect()
  const isUser = name in knownVars.value
  const builtin = isUser ? null : parseBuiltin(name)
  const source = name in placeholderVars.value
    ? 'Placeholder'
    : name in env.collectionPlaceholderVars
      ? 'Collection'
      : builtin
        ? 'Built-in'
        : 'Environment'
  // 内置占位符展示一次示例值（发送时会重新生成）
  const val = lookupVar(name, knownVars.value) ?? ''
  tip.value = {
    visible: true,
    x: rect.left - wrapRect.left,
    y: rect.bottom - wrapRect.top + 8,
    name,
    value: val,
    missing: !isUser && !builtin,
    source,
    desc: builtin
      ? `${builtin.def.desc}${builtin.def.usage ? `；${builtin.def.usage}` : ''}（示例值，每次发送重新生成）`
      : '',
  }
}

function onLeave() {
  scheduleHide()
}

async function copyValue() {
  try {
    await copyText(tip.value.value)
    toast.success('复制成功')
  } catch (err:any) {
    console.error(err)
    toast.error('复制失败')
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
  height: 100%;
  background: transparent;
}

/* 高亮层与输入框共用同样的字体/内边距/换行，保证文字对齐 */
.highlight-layer,
.real-input {
  font-family: var(--ui-font-mono);
  font-size: 12.5px;
  line-height: 1.5;
  padding: 4px 30px 4px 2px;
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
  color: var(--color-text-1);
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
  left: 2px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-4);
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
  caret-color: rgb(var(--primary-6));
  overflow-x: auto;
  overflow-y: hidden;
  margin: 0;
  z-index: 0;
}

/* 占位符高亮色：琥珀色 pill，和普通 URL 文字区分 */
.hl-text :deep(.env-var) {
  background: rgba(212, 136, 6, 0.16);
  color: var(--ui-accent-warm);
  border-radius: 3px;
  padding: 0 2px;
  margin: 0 -2px;
  pointer-events: auto;
  cursor: default;

  &.missing {
    background: rgba(220, 70, 64, 0.16);
    color: var(--ui-accent-danger);
  }

  &.builtin {
    background: rgba(var(--primary-6), 0.16);
    color: rgb(var(--primary-6));
  }
}

.clear-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  color: var(--color-text-3);
  font-size: 1em;
  padding: 0 4px;
  z-index: 2;

  &:hover {
    color: var(--color-text-1);
  }
}

.var-tip {
  position: absolute;
  z-index: 1000;
  background: var(--ui-bg-panel);
  color: var(--color-text-1);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  padding: 8px 10px;
  font-size: 0.86em;
  min-width: 220px;
  box-shadow: var(--ui-shadow-pop);
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
  font-family: var(--ui-font-mono);
  color: var(--ui-accent-warm);
}

.var-tip-badge {
  font-size: 0.79em;
  color: rgb(var(--primary-6));
  background: rgba(var(--primary-6), 0.14);
  border-radius: 3px;
  padding: 1px 6px;
}

.var-tip-value {
  font-family: var(--ui-font-mono);
  word-break: break-all;
  white-space: pre-wrap;
  max-width: 480px;
  max-height: 200px;
  overflow: auto;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  background: var(--ui-bg-subtle);
  padding: 4px 6px;
  border-radius: var(--ui-radius-sm);
}

.var-tip-value-text {
  flex: 1;
  min-width: 0;
}

.var-tip-copy {
  flex-shrink: 0;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--color-text-3);
  padding: 0;
  font-size: 0.93em;

  &:hover {
    color: rgb(var(--primary-6));
  }
}

.var-tip-missing {
  margin-top: 6px;
  color: var(--ui-accent-danger);
  font-size: 0.79em;
}

.var-tip-desc {
  margin-top: 6px;
  color: var(--color-text-3);
  font-size: 0.79em;
}

.ac-popup {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  min-width: 220px;
  max-height: 240px;
  overflow-y: auto;
  background: var(--ui-bg-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  box-shadow: var(--ui-shadow-pop);
  z-index: 1100;
  padding: 4px;
  font-size: 0.93em;
}

.ac-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 6px 8px;
  border-radius: var(--ui-radius-sm);
  cursor: pointer;
  font-family: var(--ui-font-mono);

  .ac-desc {
    font-family: var(--app-font-family);
    font-size: 0.86em;
    color: var(--color-text-3);
    white-space: nowrap;
  }

  &:hover,
  &.active {
    background: var(--ui-bg-active);
  }
}
</style>
