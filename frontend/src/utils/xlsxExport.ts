/** 把结果表格按当前视图导出为 xlsx（列宽 / 自动换行 / 冻结表头 / 数值列 / 单元格样式）。 */
import ExcelJS from 'exceljs'

export interface XlsxColumn {
  label: string
  /** 像素宽度（与页面单元格一致），导出时换算成 Excel 列宽 */
  width: number
  /** 是否自动换行 */
  wrap: boolean
  /** 数值型列：数字串写成数字，便于在 Excel 里排序求和 */
  numeric?: boolean
}

/** 与页面一致的单元格样式（颜色用 #rrggbb 或 rgb()/rgba() 字符串） */
export interface XlsxCellStyle {
  bold?: boolean
  /** 斜体 / 下划线 / 删除线 */
  italic?: boolean
  underline?: boolean
  strike?: boolean
  color?: string
  bg?: string
  /** 字体名，如「微软雅黑」 */
  font?: string
  /** 字号，单位 px（与页面一致，导出时换算为 pt） */
  fontSize?: number
  /** 水平对齐 */
  halign?: 'left' | 'center' | 'right'
  /** 垂直对齐 */
  valign?: 'top' | 'middle' | 'bottom'
}

export interface XlsxExportOptions {
  sheetName?: string
  columns: XlsxColumn[]
  /** 每行按 columns 顺序排列的文本值 */
  rows: string[][]
  fileName: string
  /** 整表默认字体名 */
  defaultFont?: string
  /** 整表默认字号，单位 px */
  defaultSize?: number
  /** 按（行下标, 列下标）返回该单元格的追加样式 */
  cellStyle?: (rowIndex: number, colIndex: number) => XlsxCellStyle | null | undefined
}

const HEADER_FILL = 'FFF2F3F5'
const DEFAULT_PX = 12

/** 颜色统一转 Excel 的 ARGB；无法识别时返回 undefined（保持默认色） */
function toArgb(color?: string): string | undefined {
  if (!color) return undefined
  const c = color.trim()
  if (/^#[0-9a-f]{6}$/i.test(c)) return `FF${c.slice(1).toUpperCase()}`
  if (/^#[0-9a-f]{3}$/i.test(c)) {
    const [r, g, b] = [c[1], c[2], c[3]]
    return `FF${(r + r + g + g + b + b).toUpperCase()}`
  }
  const m = c.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i)
  if (m) {
    const hex = [m[1], m[2], m[3]].map((n) => Number(n).toString(16).padStart(2, '0')).join('')
    return `FF${hex.toUpperCase()}`
  }
  if (/^[0-9a-f]{8}$/i.test(c)) return c.toUpperCase()
  return undefined
}

/** 页面 px 换算为 Excel pt（96dpi → 72pt） */
function pxToPt(px?: number): number | undefined {
  if (!px) return undefined
  return Math.round(px * 0.75 * 10) / 10
}

export async function exportRowsToXlsx(opts: XlsxExportOptions): Promise<void> {
  const { columns, rows, fileName, defaultFont, defaultSize, cellStyle } = opts
  const wb = new ExcelJS.Workbook()
  wb.creator = 'api-tool'
  // 不写冻结窗格：WPS 会把冻结分界线渲染成绿色粗线，看起来像表格里多了一道边框
  const ws = wb.addWorksheet((opts.sheetName || '结果').slice(0, 31))

  const baseSize = defaultSize || DEFAULT_PX
  const headerPt = pxToPt(baseSize + 2) ?? 10

  // 列宽：页面 px 近似换算成 Excel 字符宽度
  columns.forEach((c, i) => {
    const col = ws.getColumn(i + 1)
    col.width = Math.max(8, Math.min(120, Math.round(c.width / 7)))
  })

  const header = ws.addRow(columns.map((c) => c.label))
  header.height = 20
  header.eachCell((cell) => {
    const font: Partial<ExcelJS.Font> = { bold: true, size: headerPt }
    if (defaultFont) font.name = defaultFont
    cell.font = font
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: HEADER_FILL } }
    cell.alignment = { vertical: 'middle' }
    cell.border = {
      bottom: { style: 'thin', color: { argb: 'FFD9D9D9' } },
    }
  })

  rows.forEach((row, rowIndex) => {
    const values = columns.map((c, i) => {
      const raw = row[i] ?? ''
      if (!c.numeric || raw === '') return raw
      return /^-?\d+(\.\d+)?$/.test(raw) ? Number(raw) : raw
    })
    const added = ws.addRow(values)
    columns.forEach((c, i) => {
      const cell = added.getCell(i + 1)
      const st = cellStyle ? cellStyle(rowIndex, i) : null
      // 对齐：页面设置的优先；自动换行的列默认顶端对齐，行高由内容撑开
      const v = st?.valign || (c.wrap ? 'top' : undefined)
      const h = st?.halign
      if (c.wrap || v || h) {
        cell.alignment = { wrapText: c.wrap || undefined, vertical: v, horizontal: h }
      }
      const font: Partial<ExcelJS.Font> = {
        size: pxToPt(st?.fontSize || baseSize) ?? 9,
      }
      const name = st?.font || defaultFont
      if (name) font.name = name
      if (st?.bold) font.bold = true
      if (st?.italic) font.italic = true
      if (st?.underline) font.underline = true
      if (st?.strike) font.strike = true
      const color = toArgb(st?.color)
      if (color) font.color = { argb: color }
      cell.font = font
      const bg = toArgb(st?.bg)
      if (bg) cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: bg } }
    })
  })

  const buffer = await wb.xlsx.writeBuffer()
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName.endsWith('.xlsx') ? fileName : `${fileName}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}
