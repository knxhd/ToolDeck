/**
 * 主题配色：主色预设与色阶生成。
 *
 * Arco Design 用 `--primary-1..10` 十个 rgb 三元组表示主色阶：
 * 亮色主题 hover 取 5（更亮）、active 取 7（更深）；
 * 暗色主题反过来，hover 取 7（更亮）、active 取 5（更暗）。
 * 这里按此规律由单一基色生成整条色阶并写入 body 内联样式。
 */

export interface AccentPreset {
  id: string
  name: string
  /** 主色，对应 --primary-6 */
  base: string
}

export type ThemeMode = 'light' | 'dark'

/** 界面主题（浅色系 5 套 + 暗色系 5 套），令牌由 styles/themes.less 提供。 */
export interface ThemePreset {
  id: string
  name: string
  /** 明暗模式：决定 Arco 组件使用 light / dark 变量集 */
  mode: ThemeMode
  /** 下拉菜单里的预览小色块（取画布色） */
  swatch: string
  /** 一句话说明 */
  desc: string
}

export const THEME_PRESETS: ThemePreset[] = [
  // ---- 浅色系 ----
  { id: 'light', name: '浅色', mode: 'light', swatch: '#f4f5f8', desc: '冷灰白，默认' },
  { id: 'mono', name: '极简', mode: 'light', swatch: '#f5f5f6', desc: '纯中性灰，无彩色干扰' },
  { id: 'paper', name: '素纸', mode: 'light', swatch: '#f3efe6', desc: '暖白米色，接近纸张' },
  { id: 'sepia', name: '护眼绿', mode: 'light', swatch: '#e8efe4', desc: '豆沙绿底，长时间阅读不刺眼' },
  { id: 'mist', name: '雾蓝', mode: 'light', swatch: '#eef2f9', desc: '淡蓝冷调，清透安静' },
  // ---- 暗色系 ----
  { id: 'dark', name: '暗黑', mode: 'dark', swatch: '#0e1117', desc: '冷灰蓝，默认' },
  { id: 'midnight', name: '午夜蓝', mode: 'dark', swatch: '#0a101c', desc: '深藏蓝，夜空感' },
  { id: 'graphite', name: '石墨', mode: 'dark', swatch: '#141417', desc: '中性纯灰，极简克制' },
  { id: 'forest', name: '松林', mode: 'dark', swatch: '#0c1310', desc: '暗绿底，柔和护眼' },
  { id: 'dusk', name: '暖夜', mode: 'dark', swatch: '#14100d', desc: '暗褐暖调，低蓝光' },
]

/** 按 id 取主题；未知 id 回退默认浅色。 */
export function themePreset(id: string): ThemePreset {
  return THEME_PRESETS.find((t) => t.id === id) || THEME_PRESETS[0]
}

/** 主题对应的明暗模式。 */
export function themeMode(id: string): ThemeMode {
  return themePreset(id).mode
}

export const LIGHT_THEMES = THEME_PRESETS.filter((t) => t.mode === 'light')
export const DARK_THEMES = THEME_PRESETS.filter((t) => t.mode === 'dark')

/** 可选配色预设（默认第一个）。 */
export const ACCENT_PRESETS: AccentPreset[] = [
  { id: 'indigo', name: '靛蓝紫', base: '#4E5BA6' },
  { id: 'blue', name: '拂晓蓝', base: '#1668DC' },
  { id: 'cyan', name: '青碧', base: '#0E9384' },
  { id: 'green', name: '极光绿', base: '#16A34A' },
  { id: 'orange', name: '日暮橙', base: '#D97706' },
  { id: 'rose', name: '玫瑰红', base: '#E11D63' },
  { id: 'violet', name: '电光紫', base: '#7C3AED' },
  { id: 'graphite', name: '石墨灰', base: '#4E5969' },
]

type RGB = [number, number, number]

function hexToRgb(hex: string): RGB {
  let h = hex.replace('#', '').trim()
  if (h.length === 3) h = h.split('').map((c) => c + c).join('')
  const n = Number.parseInt(h, 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

/** 把 from 向 to 混合 t（0~1），返回取整后的 rgb。 */
function mix(from: RGB, to: RGB, t: number): RGB {
  return [
    Math.round(from[0] + (to[0] - from[0]) * t),
    Math.round(from[1] + (to[1] - from[1]) * t),
    Math.round(from[2] + (to[2] - from[2]) * t),
  ]
}

const WHITE: RGB = [255, 255, 255]
const BLACK: RGB = [0, 0, 0]

const toVar = (c: RGB) => `${c[0]}, ${c[1]}, ${c[2]}`

/** 由基色生成 10 级色阶（每项形如 "78, 91, 166"）。 */
export function buildRamp(base: string, dark: boolean): string[] {
  const b = hexToRgb(base)
  const ramp = dark
    ? [
        mix(b, BLACK, 0.72),
        mix(b, BLACK, 0.62),
        mix(b, BLACK, 0.5),
        mix(b, BLACK, 0.36),
        mix(b, BLACK, 0.14),
        mix(b, WHITE, 0.12),
        mix(b, WHITE, 0.28),
        mix(b, WHITE, 0.44),
        mix(b, WHITE, 0.6),
        mix(b, WHITE, 0.78),
      ]
    : [
        mix(b, WHITE, 0.92),
        mix(b, WHITE, 0.82),
        mix(b, WHITE, 0.68),
        mix(b, WHITE, 0.5),
        mix(b, WHITE, 0.26),
        b,
        mix(b, BLACK, 0.2),
        mix(b, BLACK, 0.35),
        mix(b, BLACK, 0.52),
        mix(b, BLACK, 0.68),
      ]
  return ramp.map(toVar)
}

/** 按预设 id 取基色；未知 id 回退默认。 */
export function accentBase(id: string): string {
  return (ACCENT_PRESETS.find((p) => p.id === id) || ACCENT_PRESETS[0]).base
}

/**
 * 把配色写入 body 内联样式。
 * 必须挂在 body 上：tokens.less 在 `body[arco-theme='dark']` 里也定义了色阶，
 * 只有内联样式能同时覆盖明暗两套。
 */
export function applyAccent(accentId: string, dark: boolean): void {
  const base = accentBase(accentId)
  const body = document.body
  buildRamp(base, dark).forEach((c, i) => body.style.setProperty(`--primary-${i + 1}`, c))
  const [r, g, b] = hexToRgb(base)
  // 选中态底色跟随主色（深色下加深一些以保证与暗底有对比）
  body.style.setProperty('--ui-bg-active', `rgba(${r}, ${g}, ${b}, ${dark ? 0.22 : 0.1})`)
}
