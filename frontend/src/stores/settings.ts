/** 全局设置：字体、字号、明暗主题，持久化到 localStorage。 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const KEY = 'api-tool-settings'

export const FONT_OPTIONS = [
  { label: '系统默认', value: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif' },
  { label: '等宽（代码）', value: 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace' },
  { label: '微软雅黑', value: '"Microsoft YaHei", sans-serif' },
  { label: '宋体', value: 'SimSun, serif' },
]

export const FONT_SIZE_OPTIONS = [12, 13, 14, 15, 16, 18]

interface Settings {
  fontFamily: string
  fontSize: number
  dark: boolean
}

const DEFAULTS: Settings = {
  fontFamily: FONT_OPTIONS[0].value,
  fontSize: 13,
  dark: false,
}

function load(): Settings {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch { /* ignore */ }
  return { ...DEFAULTS }
}

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<Settings>(load())

  function apply() {
    const root = document.documentElement
    root.style.setProperty('--app-font-family', settings.value.fontFamily)
    root.style.setProperty('--app-font-size', settings.value.fontSize + 'px')
    root.classList.toggle('dark', settings.value.dark)
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

  return { settings, init, reset, persist }
})
