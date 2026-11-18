<template>
  <div class="bench-result">
    <!-- 顶部信息栏 -->
    <header class="br-head">
      <div class="br-title">
        <span class="br-name">{{ job.name || '批量测试结果' }}</span>
        <a-tag v-if="job.status" size="small" :color="statusColor(job.status)">{{ statusText(job.status) }}</a-tag>
        <span class="br-meta">
          <span v-if="job.dataset_name">测试集 {{ job.dataset_name }}</span>
          <span v-if="job.total">成功 <b class="ok">{{ job.success }}</b> / 失败
            <b :class="{ err: job.fail > 0 }">{{ job.fail }}</b></span>
          <span v-if="job.concurrency">并发 {{ job.concurrency }}</span>
          <span v-if="job.stats?.avg_ms">avg {{ job.stats.avg_ms }}ms</span>
          <span v-if="job.stats?.p95_ms">p95 {{ job.stats.p95_ms }}ms</span>
          <span v-if="job.stats?.ttft_avg_ms">TTFT {{ job.stats.ttft_avg_ms }}ms</span>
          <span class="muted">{{ job.created_at }}</span>
        </span>
      </div>
      <div class="br-actions">
        <a-button size="small" @click="reload">
          <template #icon><icon-refresh /></template>刷新
        </a-button>
        <a-button size="small" @click="downloadCsv(false)">下载原始</a-button>
        <a-button size="small" type="primary" @click="downloadCsv(true)">下载结果（含标注）</a-button>
        <a-button size="small" @click="closeWindow">关闭</a-button>
      </div>
    </header>

    <!-- 工具条 -->
    <div class="br-toolbar">
      <a-input v-model="keyword" size="small" placeholder="搜索输入 / 输出内容" allow-clear style="width: 220px" />
      <a-checkbox v-model="onlyFail">只看失败</a-checkbox>
      <a-checkbox v-model="onlyAnnotated">只看已标注</a-checkbox>
      <a-button size="small" @click="columnPanelOpen = true">
        <template #icon><icon-settings /></template>列设置
      </a-button>
      <a-button size="small" @click="openAddCol">
        <template #icon><icon-plus /></template>新增标注列
      </a-button>
      <a-button v-if="activeFilterCount" size="small" status="warning" @click="clearAllFilters">
        清除筛选（{{ activeFilterCount }}）
      </a-button>
      <span class="br-count">
        共 {{ rows.length }} 行<template v-if="visibleRows.length !== rows.length">，筛选后 {{ visibleRows.length }} 行</template>
      </span>
      <span v-if="loading" class="br-saving"><icon-loading />加载中…</span>
      <span v-else-if="truncated" class="br-warn" title="可通过「下载结果」查看完整结果">
        <icon-exclamation-circle />结果超过 {{ MAX_ROWS }} 行，仅加载前 {{ MAX_ROWS }} 行
      </span>
      <span v-if="saving" class="br-saving"><icon-loading />保存中…</span>
      <span v-else-if="dirty" class="br-saving">有未保存的标注，稍后自动保存</span>
    </div>

    <!-- 表格 -->
    <div ref="wrapRef" class="br-grid-wrap" @scroll="onScroll">
      <div class="br-inner" :style="{ width: totalWidth + 'px' }">
        <div class="br-head-row">
          <div v-for="c in displayColumns" :key="c.key" class="br-th" :style="{ width: c.width + 'px' }"
            :class="{ 'is-sorted': sortKey === c.key }" @click="openColumnPanel(c, $event)">
            <span class="br-th-name" :title="c.label">{{ c.label }}</span>
            <icon-caret-up v-if="sortKey === c.key && sortDir === 'asc'" class="br-th-flag" />
            <icon-caret-down v-else-if="sortKey === c.key" class="br-th-flag" />
            <icon-filter v-if="hasFilter(c.key)" class="br-th-flag is-active" />
            <span class="br-resize" @mousedown="startResize($event, c.key, c.width)" @click.stop></span>
          </div>
        </div>
        <div class="br-body" :style="{ height: visibleRows.length * rowH + 'px' }">
          <div v-for="item in windowRows" :key="item.rowNo" class="br-row"
            :class="{ fail: item.isFail, 'has-ann': item.hasAnn }"
            :style="{ height: rowH + 'px', transform: `translateY(${item.idx * rowH}px)` }">
            <div v-for="c in displayColumns" :key="c.key" class="br-td" :style="{ width: c.width + 'px' }"
              :class="{ 'br-td-ann': !!c.annId }">
              <template v-if="c.annId">
                <input class="br-ann-input" :value="cellValue(item.rowNo, c.annId)" placeholder="—"
                  @input="onCellInputEvent(item.rowNo, c.annId, $event)" />
              </template>
              <template v-else-if="c.wrap">
                <span class="br-cell-text is-wrap" :title="item.row[c.colIdx]">{{ item.row[c.colIdx] || '' }}</span>
                <a-button v-if="(item.row[c.colIdx] || '').length > 60" class="br-zoom" size="mini" type="text"
                  @click="openDetail(c.label, item.row[c.colIdx])">
                  <template #icon><icon-eye /></template>
                </a-button>
              </template>
              <template v-else>
                <span class="br-cell-text" :title="item.row[c.colIdx]">{{ item.row[c.colIdx] || '' }}</span>
                <a-button v-if="(item.row[c.colIdx] || '').length > 60" class="br-zoom" size="mini" type="text"
                  @click="openDetail(c.label, item.row[c.colIdx])">
                  <template #icon><icon-eye /></template>
                </a-button>
              </template>
            </div>
          </div>
        </div>
        <div v-if="!visibleRows.length && !loading" class="br-empty">
          <a-empty :description="rows.length ? '没有符合筛选条件的行' : '结果文件为空'" />
        </div>
      </div>
    </div>

    <!-- 列操作 / 筛选面板（类似飞书表头下拉） -->
    <div v-if="panel.open" class="br-panel" :style="{ left: panel.x + 'px', top: panel.y + 'px' }">
      <div class="br-panel-head">
        <span class="br-panel-col" :title="panel.label">{{ panel.label }}</span>
        <span class="muted">{{ panel.rowCount }} 行</span>
      </div>

      <div class="br-sort-row">
        <button type="button" class="br-sort-btn" :class="{ on: sortKey === panel.key && sortDir === 'asc' }"
          @click="applySort('asc')">
          <icon-arrow-up /> 升序
        </button>
        <button type="button" class="br-sort-btn" :class="{ on: sortKey === panel.key && sortDir === 'desc' }"
          @click="applySort('desc')">
          <icon-arrow-down /> 降序
        </button>
      </div>

      <div class="br-panel-actions">
        <a-switch size="small" :model-value="panelWrap" @change="onWrapChange" />
        <span class="br-wrap-label">自动换行</span>
        <span class="br-panel-spacer"></span>
        <a-button v-if="panel.annId" size="mini" type="text" @click="renamePanelColumn">
          <template #icon><icon-edit /></template>重命名
        </a-button>
        <a-button size="mini" status="danger" type="text" @click="removePanelColumn">
          <template #icon><icon-delete /></template>{{ panel.annId ? '删除该标注列' : '删除此列' }}
        </a-button>
      </div>

      <div class="br-panel-tabs">
        <span class="br-tab" :class="{ on: panelTab === 'value' }" @click="panelTab = 'value'">按值筛选</span>
        <span class="br-tab" :class="{ on: panelTab === 'cond' }" @click="panelTab = 'cond'">按条件筛选</span>
      </div>

      <!-- 按值筛选 -->
      <template v-if="panelTab === 'value'">
        <div class="br-panel-search">
          <a-input v-model="valueSearch" size="small" placeholder="可使用空格分隔多个关键词" allow-clear>
            <template #prefix><icon-search /></template>
          </a-input>
        </div>
        <div class="br-value-list">
          <div class="br-value-row">
            <a-checkbox :model-value="draftAll" @change="onDraftAllChange">全选</a-checkbox>
            <span class="muted">{{ panelValues.length }} 个值</span>
          </div>
          <div v-for="v in visibleValues" :key="v.value" class="br-value-row">
            <a-checkbox :model-value="draftSel.includes(v.value)" @change="() => toggleDraftValue(v.value)">
              <span class="br-value-text" :title="v.value || '（空白）'">{{ v.value || '（空白）' }}</span>
            </a-checkbox>
            <span class="muted">{{ v.count }}</span>
          </div>
          <div v-if="panelOverflow" class="br-value-tip muted">值过多，仅列出前 300 个</div>
        </div>
      </template>

      <!-- 按条件筛选 -->
      <template v-else>
        <div class="br-cond">
          <a-select v-model="draftCond.op" size="small" style="width: 110px">
            <a-option value="contains">包含</a-option>
            <a-option value="notContains">不包含</a-option>
            <a-option value="equals">等于</a-option>
            <a-option value="empty">为空</a-option>
            <a-option value="notEmpty">不为空</a-option>
          </a-select>
          <a-input v-if="draftCond.op !== 'empty' && draftCond.op !== 'notEmpty'" v-model="draftCond.value"
            size="small" placeholder="输入内容" allow-clear />
        </div>
      </template>

      <div class="br-panel-footer">
        <a-button size="mini" type="text" @click="clearPanelFilter">清除筛选</a-button>
        <span class="br-panel-spacer"></span>
        <a-button size="mini" @click="panel.open = false">取消</a-button>
        <a-button size="mini" type="primary" @click="confirmPanel">确认</a-button>
      </div>
    </div>

    <!-- 单元格全文 -->
    <a-drawer v-model:visible="detailOpen" :width="720" title="单元格内容" :footer="false">
      <div class="br-detail">
        <div class="br-detail-head">
          <span class="muted">{{ detailLabel }}</span>
          <span class="muted">{{ detailText.length }} 字符</span>
        </div>
        <pre class="br-detail-body">{{ detailText }}</pre>
      </div>
    </a-drawer>

    <!-- 标注列：新增 / 重命名 -->
    <a-modal v-model:visible="colDialogOpen" :title="colDialogMode === 'add' ? '新增标注列' : '重命名标注列'"
      :width="360" :on-before-ok="submitColumn" ok-text="确定" cancel-text="取消">
      <a-input v-model="colDialogName" placeholder="例如：状态 / 备注 / 标注结果" :max-length="30" allow-clear
        @press-enter="submitColumn" />
      <div class="br-dialog-tip">标注列的内容由你自己填写，不做固定选项；填好后会自动保存到任务上。</div>
    </a-modal>

    <!-- 列设置 -->
    <a-drawer v-model:visible="columnPanelOpen" :width="320" title="显示哪些列" :footer="false">
      <div class="br-col-panel">
        <div class="br-col-actions">
          <a-button size="mini" @click="showAllColumns">全部显示</a-button>
          <a-button size="mini" @click="hideContentColumns">只看输入 / 指标</a-button>
        </div>
        <a-checkbox-group v-model="visibleKeys">
          <a-checkbox v-for="c in allColumns" :key="c.key" :value="c.key">
            <span class="br-col-panel-name">{{ c.label }}</span>
            <span class="muted">（{{ c.width }}px）</span>
          </a-checkbox>
        </a-checkbox-group>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { getToken } from '@/api/client'
import { toast } from '@/utils/feedback'

type AnyRow = string[]

interface AnnCol { id: string; name: string }
interface ColMeta { width: number; wrap: boolean }
interface CondFilter { op: 'contains' | 'notContains' | 'equals' | 'empty' | 'notEmpty'; value: string }

const ROW_H = 34
const ROW_H_WRAP = 96
const PAGE_SIZE = 300
const MAX_ROWS = 5000

const route = useRoute()
const jobId = String(route.params.jobId || '')

const loading = ref(false)
const truncated = ref(false)
const rows = ref<AnyRow[]>([])
const columns = ref<string[]>([])
const job = reactive<any>({})
const keyword = ref('')
/** 输入框防抖后的关键词（大结果集上避免每次按键都全表扫描） */
const filterKw = ref('')
const onlyFail = ref(false)
const onlyAnnotated = ref(false)

// ---- 标注状态 ----
const annCols = ref<AnnCol[]>([])
/** 行号(1 起) → { colId: 值 } */
const annCells = ref<Record<string, Record<string, string>>>({})
const dirty = ref(false)
const saving = ref(false)
let saveTimer: ReturnType<typeof setTimeout> | null = null

// ---- 列配置（宽度 / 自动换行），key = d<索引> | a<标注列 id> ----
const colMeta = reactive<Record<string, ColMeta>>({})
const hiddenColumns = ref<Set<string>>(new Set())
const columnPanelOpen = ref(false)

// ---- 排序与筛选 ----
const sortKey = ref<string | null>(null)
const sortDir = ref<'asc' | 'desc'>('asc')
/** 按值筛选：列 key → 勾选的值 */
const valueFilters = ref<Record<string, string[]>>({})
/** 按条件筛选：列 key → 条件 */
const condFilters = ref<Record<string, CondFilter>>({})

// ---- 列面板 ----
const panel = reactive({
  open: false, key: '', label: '', annId: null as string | null, x: 0, y: 0, rowCount: 0,
})
const panelTab = ref<'value' | 'cond'>('value')
const valueSearch = ref('')
const draftSel = ref<string[]>([])
const draftAll = ref(true)
const draftCond = ref<CondFilter>({ op: 'contains', value: '' })

// ---- 详情抽屉 / 列对话框 ----
const detailOpen = ref(false)
const detailLabel = ref('')
const detailText = ref('')
const colDialogOpen = ref(false)
const colDialogMode = ref<'add' | 'rename'>('add')
const colDialogName = ref('')
let renameTargetId: string | null = null

const statusText = (s: string) => ({ running: '运行中', done: '已完成', failed: '失败', cancelled: '已取消' }[s] || s)
const statusColor = (s: string) => ({ running: 'blue', done: 'green', failed: 'red', cancelled: 'orange' }[s] || 'gray')

/** 指标列固定宽度；其它列按内容给一个舒服的默认宽度。 */
const METRIC_WIDTH: Record<string, number> = {
  序号: 60,
  状态码: 78,
  是否成功: 84,
  总耗时ms: 96,
  首帧耗时ms: 104,
  响应字节数: 104,
  是否重试: 80,
  错误信息: 220,
  content: 360,
  响应原文: 360,
}
const ANN_WIDTH = 160

function widthFor(name: string): number {
  if (METRIC_WIDTH[name]) return METRIC_WIDTH[name]
  if (/^(content|响应原文)$/.test(name)) return 360
  return 150
}

/** 表头 / 列定义：数据列 + 标注列，宽度与换行取 colMeta 里的用户配置。 */
const allColumns = computed(() => {
  const data = columns.value.map((name, i) => {
    const key = `d${i}`
    return {
      key,
      label: name,
      colIdx: i,
      annId: null as string | null,
      width: colMeta[key]?.width ?? widthFor(name),
      wrap: colMeta[key]?.wrap ?? false,
    }
  })
  const ann = annCols.value.map((c) => {
    const key = `a${c.id}`
    return {
      key,
      label: c.name || '未命名',
      colIdx: -1,
      annId: c.id as string | null,
      width: colMeta[key]?.width ?? ANN_WIDTH,
      wrap: colMeta[key]?.wrap ?? false,
    }
  })
  return [...data, ...ann]
})

const displayColumns = computed(() => allColumns.value.filter((c) => !hiddenColumns.value.has(c.key)))

/** 列设置抽屉用：checkbox-group 双向绑定「显示中的列 key」。 */
const visibleKeys = computed<string[]>({
  get: () => allColumns.value.filter((c) => !hiddenColumns.value.has(c.key)).map((c) => c.key),
  set: (keys) => {
    const next = new Set<string>()
    for (const c of allColumns.value) {
      if (!keys.includes(c.key)) next.add(c.key)
    }
    hiddenColumns.value = next
  },
})

const totalWidth = computed(() => displayColumns.value.reduce((s, c) => s + c.width, 0) || 800)

/** 任一可见列开启自动换行时，行高切到多行模式。 */
const rowH = computed(() => (displayColumns.value.some((c) => c.wrap) ? ROW_H_WRAP : ROW_H))

// ---- 取值 ----
function valueOf(row: AnyRow, rowNo: number, key: string): string {
  if (key.startsWith('a')) {
    return annCells.value[String(rowNo)]?.[key.slice(1)] || ''
  }
  const idx = Number(key.slice(1))
  return row[idx] ?? ''
}

// ---- 行数据（筛选 + 排序） ----
const successIdx = computed(() => columns.value.findIndex((n) => n === '是否成功'))

interface RenderRow { idx: number; rowNo: number; row: AnyRow; isFail: boolean; hasAnn: boolean }

function rowPassesFilters(row: AnyRow, rowNo: number, kw: string): boolean {
  for (const key of Object.keys(valueFilters.value)) {
    const sel = valueFilters.value[key]
    if (!sel || !sel.length) continue
    if (!sel.includes(valueOf(row, rowNo, key))) return false
  }
  for (const key of Object.keys(condFilters.value)) {
    const c = condFilters.value[key]
    const v = valueOf(row, rowNo, key)
    if (c.op === 'contains' && !v.includes(c.value)) return false
    if (c.op === 'notContains' && v.includes(c.value)) return false
    if (c.op === 'equals' && v !== c.value) return false
    if (c.op === 'empty' && v.trim() !== '') return false
    if (c.op === 'notEmpty' && v.trim() === '') return false
  }
  if (kw) {
    const hitRow = row.some((v) => String(v || '').toLowerCase().includes(kw))
    const cellMap = annCells.value[String(rowNo)]
    const hitAnn = !!cellMap && Object.values(cellMap).some((v) => String(v || '').toLowerCase().includes(kw))
    if (!hitRow && !hitAnn) return false
  }
  return true
}

const visibleRows = computed<RenderRow[]>(() => {
  const kw = filterKw.value.trim().toLowerCase()
  const failIdx = successIdx.value
  const out: RenderRow[] = []
  for (let i = 0; i < rows.value.length; i++) {
    const row = rows.value[i]
    const rowNo = i + 1
    const isFail = failIdx >= 0 && row[failIdx] === '失败'
    if (onlyFail.value && !isFail) continue
    const cellMap = annCells.value[String(rowNo)]
    const hasAnn = !!cellMap && Object.values(cellMap).some((v) => String(v || '').trim())
    if (onlyAnnotated.value && !hasAnn) continue
    if (!rowPassesFilters(row, rowNo, kw)) continue
    out.push({ idx: out.length, rowNo, row, isFail, hasAnn })
  }
  // 排序：数字优先按数值，其余按本地化字符串
  const key = sortKey.value
  if (key) {
    const dir = sortDir.value === 'asc' ? 1 : -1
    out.sort((a, b) => {
      const va = valueOf(a.row, a.rowNo, key)
      const vb = valueOf(b.row, b.rowNo, key)
      const na = Number(va)
      const nb = Number(vb)
      if (va !== '' && vb !== '' && !Number.isNaN(na) && !Number.isNaN(nb)) return (na - nb) * dir
      return va.localeCompare(vb, 'zh-CN') * dir
    })
    out.forEach((r, i) => { r.idx = i })
  }
  return out
})

// ---- 虚拟滚动 ----
const wrapRef = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const viewportH = ref(600)
const overscan = 8

const windowRows = computed(() => {
  const h = rowH.value
  const start = Math.max(0, Math.floor(scrollTop.value / h) - overscan)
  const end = Math.min(visibleRows.value.length, Math.ceil((scrollTop.value + viewportH.value) / h) + overscan)
  return visibleRows.value.slice(start, end)
})

function onScroll() {
  const el = wrapRef.value
  if (el) scrollTop.value = el.scrollTop
}

function measure() {
  if (wrapRef.value) viewportH.value = wrapRef.value.clientHeight
}

// ---- 数据加载 ----
async function apiGet<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      detail = ((await res.json()) as any).detail || detail
    } catch { /* ignore */ }
    throw new Error(detail)
  }
  return (await res.json()) as T
}

async function reload() {
  loading.value = true
  truncated.value = false
  rows.value = []
  try {
    // 先取第一页拿到表头与任务信息
    const first = await apiGet<any>(`/api/bench/jobs/${jobId}/rows?offset=0&limit=${PAGE_SIZE}`)
    Object.assign(job, first.job || {})
    columns.value = first.columns || []
    const total = first.total || 0
    const cap = Math.min(total, MAX_ROWS)
    truncated.value = total > MAX_ROWS
    rows.value = first.rows || []
    await nextTick()
    measure()
    // 剩余行分批补齐（虚拟滚动下渲染量恒定，加载期间表格已可交互）
    while (rows.value.length < cap) {
      const page = await apiGet<any>(
        `/api/bench/jobs/${jobId}/rows?offset=${rows.value.length}&limit=${PAGE_SIZE}`,
      )
      const got: AnyRow[] = page.rows || []
      if (!got.length) break
      rows.value = rows.value.concat(got)
    }
    await loadAnnotations()
  } catch (err: any) {
    toast.error(err.message || '加载结果失败')
  } finally {
    loading.value = false
  }
}

async function loadAnnotations() {
  try {
    const data = await apiGet<{ cols: AnnCol[]; cells: Record<string, Record<string, string>> }>(
      `/api/bench/jobs/${jobId}/annotations`,
    )
    annCols.value = (data.cols || []).filter((c) => c && c.id)
    annCells.value = data.cells || {}
    dirty.value = false
  } catch (err: any) {
    toast.error(err.message || '加载标注失败')
  }
}

// ---- 标注保存（防抖整体提交） ----
function scheduleSave() {
  dirty.value = true
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => { void flushSave() }, 800)
}

async function flushSave() {
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  if (!dirty.value) return
  saving.value = true
  try {
    const res = await fetch(`/api/bench/jobs/${jobId}/annotations`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({ cols: annCols.value, cells: annCells.value }),
    })
    if (!res.ok) throw new Error('保存标注失败')
    dirty.value = false
  } catch (err: any) {
    toast.error(err.message || '保存标注失败')
  } finally {
    saving.value = false
  }
}

function cellValue(rowNo: number, colId: string | null): string {
  if (!colId) return ''
  return annCells.value[String(rowNo)]?.[colId] || ''
}

function onCellInputEvent(rowNo: number, colId: string | null, e: Event) {
  if (!colId) return
  onCellInput(rowNo, colId, (e.target as HTMLInputElement).value)
}

function onCellInput(rowNo: number, colId: string, value: string) {
  const key = String(rowNo)
  const map = annCells.value[key] || (annCells.value[key] = {})
  if (value) map[colId] = value
  else delete map[colId]
  if (!Object.keys(map).length) delete annCells.value[key]
  scheduleSave()
}

// ---- 列宽拖拽 ----
let resizing: { key: string; startX: number; startW: number } | null = null

function startResize(e: MouseEvent, key: string, width: number) {
  e.preventDefault()
  e.stopPropagation()
  resizing = { key, startX: e.clientX, startW: width }
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
}

function onResizeMove(e: MouseEvent) {
  if (!resizing) return
  const next = Math.max(60, Math.min(900, resizing.startW + (e.clientX - resizing.startX)))
  const meta = colMeta[resizing.key] || (colMeta[resizing.key] = { width: next, wrap: false })
  meta.width = next
}

function stopResize() {
  resizing = null
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
}

// ---- 列面板：打开 / 排序 / 换行 / 删除列 ----
function openColumnPanel(col: { key: string; label: string; annId: string | null }, e: MouseEvent) {
  // 再次点击同一列：收起面板
  if (panel.open && panel.key === col.key) {
    panel.open = false
    return
  }
  const el = (e.currentTarget as HTMLElement).getBoundingClientRect()
  panel.key = col.key
  panel.label = col.label
  panel.annId = col.annId
  panel.x = Math.min(el.left, window.innerWidth - 340)
  panel.y = Math.min(el.bottom + 4, window.innerHeight - 540)
  panel.rowCount = rows.value.length
  panelTab.value = 'value'
  valueSearch.value = ''
  panel.open = true // 先打开，panelValues 才会按该列算值
  // 草稿：沿用已有筛选，否则默认全选
  const existing = valueFilters.value[col.key]
  draftSel.value = existing ? [...existing] : panelValues.value.map((v) => v.value)
  draftAll.value = !existing
  draftCond.value = { ...(condFilters.value[col.key] || { op: 'contains', value: '' }) }
}

/** 面板里该列的全部去重值与出现次数（最多 300 个，超出时提示）。 */
const panelValueData = computed<{ values: { value: string; count: number }[]; overflow: boolean }>(() => {
  if (!panel.open) return { values: [], overflow: false }
  const key = panel.key
  const map = new Map<string, number>()
  for (let i = 0; i < rows.value.length; i++) {
    const v = valueOf(rows.value[i], i + 1, key)
    map.set(v, (map.get(v) || 0) + 1)
  }
  const arr = [...map.entries()].map(([value, count]) => ({ value, count }))
  arr.sort((a, b) => b.count - a.count || a.value.localeCompare(b.value, 'zh-CN'))
  return { values: arr.slice(0, 300), overflow: arr.length > 300 }
})

const panelValues = computed(() => panelValueData.value.values)
const panelOverflow = computed(() => panelValueData.value.overflow)

/** 值列表再叠一层关键词过滤。 */
const visibleValues = computed(() => {
  const kws = valueSearch.value.trim().toLowerCase().split(/\s+/).filter(Boolean)
  if (!kws.length) return panelValues.value
  return panelValues.value.filter((v) => kws.every((kw) => v.value.toLowerCase().includes(kw)))
})

const panelWrap = computed(() => colMeta[panel.key]?.wrap ?? false)

function onDraftAllChange(v: unknown) {
  toggleDraftAll(!!v)
}

function onWrapChange(v: unknown) {
  setWrap(!!v)
}

/** 标注列重命名：先收起面板，再打开对话框。 */
function renamePanelColumn() {
  const id = panel.annId
  if (!id) return
  const col = annCols.value.find((c) => c.id === id)
  panel.open = false
  if (!col) return
  colDialogMode.value = 'rename'
  renameTargetId = id
  colDialogName.value = col.name
  colDialogOpen.value = true
}

function toggleDraftAll(checked: boolean) {
  draftAll.value = checked
  draftSel.value = checked ? panelValues.value.map((v) => v.value) : []
}

function toggleDraftValue(value: string) {
  const set = new Set(draftSel.value)
  if (set.has(value)) set.delete(value)
  else set.add(value)
  draftSel.value = [...set]
  draftAll.value = draftSel.value.length === panelValues.value.length
}

function applySort(dir: 'asc' | 'desc') {
  sortKey.value = panel.key
  sortDir.value = dir
  panel.open = false
  resetScroll()
}

function setWrap(v: boolean) {
  const meta = colMeta[panel.key] || (colMeta[panel.key] = { width: 150, wrap: false })
  meta.wrap = v
  nextTick(() => { measure() })
}

function hasFilter(key: string): boolean {
  const sel = valueFilters.value[key]
  const cond = condFilters.value[key]
  return (!!sel && sel.length > 0) || !!cond
}

const activeFilterCount = computed(() =>
  Object.keys(valueFilters.value).filter((k) => valueFilters.value[k]?.length).length
  + Object.keys(condFilters.value).length,
)

function clearPanelFilter() {
  const key = panel.key
  delete valueFilters.value[key]
  delete condFilters.value[key]
  draftSel.value = panelValues.value.map((v) => v.value)
  draftAll.value = true
  draftCond.value = { op: 'contains', value: '' }
  panel.open = false
  resetScroll()
}

function confirmPanel() {
  const key = panel.key
  if (panelTab.value === 'value') {
    const all = panelValues.value.map((v) => v.value)
    if (draftSel.value.length === 0 || draftSel.value.length >= all.length) delete valueFilters.value[key]
    else valueFilters.value[key] = [...draftSel.value]
    // 按值筛选与按条件筛选互斥，避免叠加后结果为空
    delete condFilters.value[key]
  } else {
    const c = draftCond.value
    const needsValue = c.op !== 'empty' && c.op !== 'notEmpty'
    if (needsValue && !c.value.trim()) {
      toast.warning('请输入筛选内容')
      return
    }
    condFilters.value[key] = { op: c.op, value: c.value }
    delete valueFilters.value[key]
  }
  panel.open = false
  resetScroll()
}

function clearAllFilters() {
  valueFilters.value = {}
  condFilters.value = {}
  resetScroll()
}

function removePanelColumn() {
  const { key, annId } = panel
  if (annId) {
    // 标注列：连同已填内容一起删除
    annCols.value = annCols.value.filter((c) => c.id !== annId)
    for (const rowNo of Object.keys(annCells.value)) {
      const map = annCells.value[rowNo]
      delete map[annId]
      if (!Object.keys(map).length) delete annCells.value[rowNo]
    }
    delete colMeta[key]
    scheduleSave()
    void flushSave()
  } else {
    // 数据列：只从当前视图隐藏，原始 CSV 与下载不受影响
    const set = new Set(hiddenColumns.value)
    set.add(key)
    hiddenColumns.value = set
  }
  delete valueFilters.value[key]
  delete condFilters.value[key]
  panel.open = false
  resetScroll()
}

// ---- 标注列管理 ----
function openAddCol() {
  colDialogMode.value = 'add'
  renameTargetId = null
  colDialogName.value = ''
  colDialogOpen.value = true
}

function submitColumn(): boolean {
  const name = colDialogName.value.trim()
  if (!name) {
    toast.error('列名不能为空')
    return false
  }
  if (colDialogMode.value === 'add') {
    const id = `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`
    annCols.value.push({ id, name })
  } else if (renameTargetId) {
    const col = annCols.value.find((c) => c.id === renameTargetId)
    if (col) col.name = name
  }
  scheduleSave()
  void flushSave()
  colDialogOpen.value = false
  return true
}

// ---- 列显隐 ----
function showAllColumns() {
  hiddenColumns.value = new Set()
}

/** 只看输入列与固定指标列（隐藏自定义列 / content 等长文本列）。 */
function hideContentColumns() {
  const hidden = new Set<string>()
  const metrics = new Set(Object.keys(METRIC_WIDTH))
  columns.value.forEach((name, i) => {
    if (!metrics.has(name)) hidden.add(`d${i}`)
  })
  hiddenColumns.value = hidden
}

// ---- 单元格详情 ----
function openDetail(label: string, text: string) {
  detailLabel.value = label
  detailText.value = text || ''
  detailOpen.value = true
}

// ---- 下载 / 关闭 ----
async function downloadCsv(withAnnotations: boolean) {
  try {
    const url = `/api/bench/jobs/${jobId}/csv${withAnnotations ? '?with_annotations=1' : ''}`
    const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } })
    if (!res.ok) throw new Error('下载失败')
    const blob = await res.blob()
    const u = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = u
    a.download = `benchmark-result-${job.name || jobId}${withAnnotations ? '-annotated' : ''}.csv`
    a.click()
    URL.revokeObjectURL(u)
  } catch (err: any) {
    toast.error(err.message || '下载失败')
  }
}

function closeWindow() {
  window.close()
}

function resetScroll() {
  scrollTop.value = 0
  if (wrapRef.value) wrapRef.value.scrollTop = 0
}

function onResize() {
  measure()
  if (panel.open) panel.open = false
}

/** 点击面板与表头之外的地方关闭面板（表头自身负责切换/收起）。 */
function onDocMousedown(e: MouseEvent) {
  if (!panel.open) return
  const target = e.target as HTMLElement | null
  if (target?.closest('.br-panel') || target?.closest('.br-th')) return
  panel.open = false
}

onMounted(() => {
  void reload()
  window.addEventListener('resize', onResize)
  document.addEventListener('mousedown', onDocMousedown)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  document.removeEventListener('mousedown', onDocMousedown)
  stopResize()
  if (saveTimer) clearTimeout(saveTimer)
  if (kwTimer) clearTimeout(kwTimer)
  if (dirty.value) void flushSave()
})

watch([filterKw, onlyFail, onlyAnnotated], resetScroll)

let kwTimer: ReturnType<typeof setTimeout> | null = null
watch(keyword, (v) => {
  if (kwTimer) clearTimeout(kwTimer)
  kwTimer = setTimeout(() => { filterKw.value = v }, 200)
})

// 换行 / 列宽变化后重算可视区
watch(rowH, () => { nextTick(measure) })
</script>

<style lang="less" scoped>
.bench-result {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-fill-1);
}

.br-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
  background: var(--color-bg-2);
  border-bottom: 1px solid var(--color-border-2);
}

.br-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.br-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-1);
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.br-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-2);
}

.br-meta .ok { color: rgb(var(--green-6)); }
.br-meta .err { color: rgb(var(--red-6)); }
.muted { color: var(--color-text-3); }

.br-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.br-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--color-bg-2);
  border-bottom: 1px solid var(--color-border-2);
  font-size: 12px;
}

.br-count { color: var(--color-text-3); margin-left: auto; }
.br-saving { color: rgb(var(--orange-6)); display: inline-flex; align-items: center; gap: 4px; }
.br-warn { color: rgb(var(--red-6)); display: inline-flex; align-items: center; gap: 4px; cursor: default; }

.br-grid-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: var(--color-bg-2);
}

.br-inner {
  position: relative;
  min-width: 100%;
}

.br-head-row {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  background: var(--color-fill-2);
  border-bottom: 1px solid var(--color-border-2);
  height: 36px;
}

.br-th {
  position: relative;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-1);
  border-right: 1px solid var(--color-border-2);
  overflow: hidden;
  cursor: pointer;
  user-select: none;

  &:hover { background: var(--color-fill-3); }
  &.is-sorted { background: rgba(var(--primary-1), 0.6); }

  &:first-child {
    position: sticky;
    left: 0;
    z-index: 4;
    background: var(--color-fill-2);
  }
}

.br-th-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.br-th-flag {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--color-text-3);

  &.is-active { color: rgb(var(--primary-6)); }
}

/* 列宽拖拽手柄 */
.br-resize {
  position: absolute;
  top: 0;
  right: -2px;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 1;

  &::after {
    content: '';
    display: block;
    width: 1px;
    height: 100%;
    margin-left: 2px;
    background: transparent;
  }

  &:hover::after { background: rgb(var(--primary-6)); }
}

.br-body {
  position: relative;
}

.br-row {
  position: absolute;
  left: 0;
  top: 0;
  display: flex;
  border-bottom: 1px solid var(--color-border-1);
  background: var(--color-bg-2);

  &.fail { background: rgba(var(--red-1), 0.5); }
  &.has-ann { box-shadow: inset 2px 0 0 rgb(var(--green-5)); }

  &:hover { background: var(--color-fill-1); }
}

.br-td {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 8px;
  font-size: 12px;
  color: var(--color-text-1);
  border-right: 1px solid var(--color-border-1);
  overflow: hidden;

  &:first-child {
    position: sticky;
    left: 0;
    z-index: 2;
    background: inherit;
  }
}

.br-td-ann {
  background: rgba(var(--green-1), 0.35);
}

.br-cell-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 自动换行：多行截断，点眼睛看全文 */
.br-cell-text.is-wrap {
  white-space: normal;
  word-break: break-all;
  line-height: 18px;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.br-zoom {
  flex-shrink: 0;
  color: var(--color-text-3);

  &:hover { color: rgb(var(--primary-6)); }
}

.br-ann-input {
  width: 100%;
  height: 26px;
  padding: 0 6px;
  font-size: 12px;
  color: var(--color-text-1);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 3px;
  outline: none;

  &:hover { border-color: var(--color-border-2); background: var(--color-bg-2); }
  &:focus { border-color: rgb(var(--primary-5)); background: var(--color-bg-2); }
}

.br-empty {
  padding: 60px 0;
}

/* ---- 列面板 ---- */
.br-panel {
  position: fixed;
  z-index: 1000;
  width: 320px;
  max-height: 520px;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-2);
  border: 1px solid var(--color-border-2);
  border-radius: 6px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  font-size: 12px;
  overflow: hidden;
}

.br-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px 6px;
}

.br-panel-col {
  font-weight: 600;
  color: var(--color-text-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.br-sort-row {
  display: flex;
  gap: 8px;
  padding: 0 12px 8px;
}

.br-sort-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 28px;
  font-size: 12px;
  color: var(--color-text-1);
  background: var(--color-fill-1);
  border: 1px solid var(--color-border-2);
  border-radius: 4px;
  cursor: pointer;

  &:hover { border-color: rgb(var(--primary-5)); color: rgb(var(--primary-6)); }
  &.on { border-color: rgb(var(--primary-6)); color: rgb(var(--primary-6)); background: rgba(var(--primary-1), 0.5); }
}

.br-panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px 8px;
  border-bottom: 1px solid var(--color-border-2);
}

.br-wrap-label {
  color: var(--color-text-2);
}

.br-panel-tabs {
  display: flex;
  gap: 16px;
  padding: 8px 12px 0;
}

.br-tab {
  padding-bottom: 6px;
  color: var(--color-text-2);
  cursor: pointer;
  border-bottom: 2px solid transparent;

  &.on { color: rgb(var(--primary-6)); border-bottom-color: rgb(var(--primary-6)); }
}

.br-panel-search {
  padding: 8px 12px 4px;
}

.br-value-list {
  flex: 1;
  min-height: 120px;
  max-height: 240px;
  overflow: auto;
  padding: 4px 12px;
}

.br-value-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  height: 30px;

  :deep(.arco-checkbox) {
    display: flex;
    align-items: center;
    min-width: 0;
  }
}

.br-value-text {
  display: inline-block;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.br-value-tip {
  padding: 6px 0;
}

.br-cond {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  min-height: 76px;
}

.br-panel-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-top: 1px solid var(--color-border-2);
  background: var(--color-fill-1);
}

.br-panel-spacer { flex: 1; }

.br-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.br-detail-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border-2);
}

.br-detail-body {
  flex: 1;
  margin: 8px 0 0;
  padding: 10px;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--color-fill-1);
  border-radius: 4px;
  overflow: auto;
}

.br-dialog-tip {
  margin-top: 10px;
  font-size: 12px;
  color: var(--color-text-3);
  line-height: 1.6;
}

.br-col-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.br-col-actions {
  display: flex;
  gap: 8px;
}

.br-col-panel-name {
  font-size: 12px;
}
</style>
