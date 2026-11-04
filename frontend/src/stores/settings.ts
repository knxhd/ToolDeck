/** 全局设置：字体、字号、界面主题、主题配色、Tab数量，持久化到 localStorage。 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { ref, watch } from 'vue'

import { applyAccent, themeMode, themePreset } from '@/utils/theme'

const KEY = 'api-tool-settings'

export const FONT_OPTIONS = [
  { label: '系统默认', value: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif' },
  { label: '等宽', value: 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace' },
  { label: '微软雅黑', value: '"Microsoft YaHei", sans-serif' },
  { label: '宋体', value: 'SimSun, serif' },
]

export const FONT_SIZE_OPTIONS = [12, 13, 14, 15, 16, 18]

/** 标签页数量上限的可选范围。 */
export const MAX_TABS_MIN = 1
export const MAX_TABS_MAX = 100

interface Settings {
  fontFamily: string
  fontSize: number
  /** 界面主题 id（见 utils/theme 的 THEME_PRESETS，共 10 套）。 */
  theme: string
  /** 由 theme 派生的明暗标记，保留给依赖“是否暗色”的逻辑（如 Monaco）。 */
  dark: boolean
  /** 主题配色预设 id（见 utils/theme 的 ACCENT_PRESETS）。 */
  accent: string
  /** 工作台最多同时打开的标签页数，超出时自动关闭最早的标签。 */
  maxTabs: number
}

const DEFAULTS: Settings = {
  fontFamily: FONT_OPTIONS[0].value,
  fontSize: 14,
  theme: 'light',
  dark: false,
  accent: 'indigo',
  maxTabs: 10,
}

function load(): Settings {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) {
      const parsed = { ...DEFAULTS, ...JSON.parse(raw) }
      // 兼容历史数据：旧版本只有 dark 布尔值
      if (!parsed.theme) parsed.theme = parsed.dark ? 'dark' : 'light'
      parsed.dark = themeMode(parsed.theme) === 'dark'
      // 兼容历史数据：maxTabs 校正到合法范围
      parsed.maxTabs = Math.min(MAX_TABS_MAX, Math.max(MAX_TABS_MIN, Number(parsed.maxTabs) || DEFAULTS.maxTabs))
      return parsed
    }
  } catch { /* ignore */ }
  return { ...DEFAULTS }
}

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<Settings>(load())

  function apply() {
    const root = document.documentElement
    root.style.setProperty('--app-font-family', settings.value.fontFamily)
    root.style.setProperty('--app-font-size', settings.value.fontSize + 'px')
    const mode = themeMode(settings.value.theme)
    // dark 是 theme 的派生值，供 Monaco 等只关心明暗的地方使用
    settings.value.dark = mode === 'dark'
    // Arco Design Vue 明暗模式：body[arco-theme='dark']
    document.body.setAttribute('arco-theme', mode)
    // 具体主题（10 套）的令牌覆写：body[data-theme='xxx']
    document.body.setAttribute('data-theme', settings.value.theme)
    // 浏览器地址栏 / 状态栏颜色跟随主题
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) meta.setAttribute('content', themePreset(settings.value.theme).swatch)
    // 主色阶跟随所选配色（明暗两套色阶由基色推导）
    applyAccent(settings.value.accent, mode === 'dark')
  }

  function persist() {
    localStorage.setItem(KEY, JSON.stringify(settings.value))
    apply()
  }

  function init() {
    apply()
    watch(settings, persist, { deep: true })
  }

  function reset() {
    settings.value = { ...DEFAULTS }
  }

  return { settings, init, reset, persist, maxTabsMin: MAX_TABS_MIN, maxTabsMax: MAX_TABS_MAX }
})

if (import.meta.hot) import.meta.hot.accept(acceptHMRUpdate(useSettingsStore, import.meta.hot))
