/** 全局设置：字体、字号、明暗主题、Tab数量，持久化到 localStorage。 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { ref, watch } from 'vue'

const KEY = 'api-tool-settings'

export const FONT_OPTIONS = [
  { label: '系统默认', value: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif' },
  { label: '等宽（代码）', value: 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace' },
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
  dark: boolean
  /** 工作台最多同时打开的标签页数，超出时自动关闭最早的标签。 */
  maxTabs: number
}

const DEFAULTS: Settings = {
  fontFamily: FONT_OPTIONS[0].value,
  fontSize: 14,
  dark: false,
  maxTabs: 10,
}

function load(): Settings {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) {
      const parsed = { ...DEFAULTS, ...JSON.parse(raw) }
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
    // Arco Design Vue 深色模式：body[arco-theme='dark']
    document.body.setAttribute('arco-theme', settings.value.dark ? 'dark' : 'light')
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
