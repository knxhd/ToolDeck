/**
 * 占位符信息解析：给编辑器高亮 / 悬停提示用。
 * 优先级与发送时一致：请求占位符 > 集合占位符 > 环境变量 > 内置占位符。
 */
import type { KeyValue } from '@/api/types'
import { useEnvironmentsStore } from '@/stores/environments'
import { parseBuiltin } from '@/utils/env'

export type VarSource = 'Placeholder' | 'Collection' | 'Environment' | 'Built-in'

export interface VarInfo {
  /** 占位符 token（不含花括号），如 `base_url`、`$randomString(8)` */
  name: string
  /** 来源；null 表示未定义 */
  source: VarSource | null
  /** 用户变量的原始值 / 内置占位符的示例值 */
  value?: string
  /** 内置占位符说明 */
  desc?: string
  /** 内置占位符参数用法 */
  usage?: string
}

export type VarResolver = (name: string) => VarInfo

const SOURCE_LABEL: Record<VarSource, string> = {
  Placeholder: '请求占位符',
  Collection: '集合占位符',
  Environment: '环境变量',
  'Built-in': '内置占位符',
}

function enabledMap(list: KeyValue[] | undefined): Record<string, string> {
  const out: Record<string, string> = {}
  for (const p of list || []) {
    const key = (p.key || '').trim()
    if (p.enabled && key) out[key] = p.value ?? ''
  }
  return out
}

/**
 * 基于当前集合作用域（环境变量 + 集合占位符）和请求级占位符构造解析函数。
 * collectionPlaceholders 传入时代替 store 中的集合占位符（如集合占位符对话框中未保存的编辑副本）。
 * 请在 computed 中调用，依赖变化时会得到新的函数实例，编辑器据此刷新高亮。
 */
export function buildVarResolver(
  requestPlaceholders?: KeyValue[],
  collectionPlaceholders?: KeyValue[],
): VarResolver {
  const env = useEnvironmentsStore()
  const reqVars = enabledMap(requestPlaceholders)
  const colVars = collectionPlaceholders ? enabledMap(collectionPlaceholders) : { ...env.collectionPlaceholderVars }
  const envVars = { ...env.vars }
  return (name: string): VarInfo => {
    if (name in reqVars) return { name, source: 'Placeholder', value: reqVars[name] }
    if (name in colVars) return { name, source: 'Collection', value: colVars[name] }
    if (name in envVars) return { name, source: 'Environment', value: envVars[name] }
    const b = parseBuiltin(name)
    if (b) {
      return { name, source: 'Built-in', value: b.def.gen(b.arg), desc: b.def.desc, usage: b.def.usage }
    }
    return { name, source: null }
  }
}

/** 选一个不会与内容冲突的代码围栏。 */
function fence(text: string): string {
  let f = '```'
  while (text.includes(f)) f += '`'
  return f
}

const MAX_PREVIEW = 800

/** 生成悬停提示的 Markdown 文本。 */
export function varHoverMarkdown(info: VarInfo): string {
  const title = `**\`{{${info.name}}}\`**`
  if (!info.source) {
    return `${title} · 未定义\n\n未在环境变量 / 占位符中定义，发送时将原样保留。`
  }
  if (info.source === 'Built-in') {
    const lines = [`${title} · ${SOURCE_LABEL['Built-in']}`, '', info.desc || '']
    if (info.usage) lines.push('', `参数：${info.usage}`)
    const sample = info.value ?? ''
    const f = fence(sample)
    lines.push('', '示例值（每次发送重新生成）：', '', `${f}text\n${sample}\n${f}`)
    return lines.join('\n')
  }
  const raw = info.value ?? ''
  const shown = raw.length > MAX_PREVIEW ? `${raw.slice(0, MAX_PREVIEW)}\n…（共 ${raw.length} 字符）` : raw
  const f = fence(shown)
  return `${title} · ${SOURCE_LABEL[info.source]}\n\n${shown === '' ? '(空字符串)' : `${f}text\n${shown}\n${f}`}`
}
