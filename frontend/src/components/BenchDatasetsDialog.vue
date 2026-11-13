<template>
  <a-modal
    :visible="visible"
    title="测试集管理"
    width="1000px"
    :mask-closable="false"
    :footer="false"
    @update:visible="(v: boolean) => emit('update:visible', v)"
    @cancel="emit('update:visible', false)"
  >
    <div class="ds-manager">
      <div class="ds-toolbar">
        <span class="muted">
          测试集是保存下来的 CSV 数据，批量测试时直接选用，不用每次重新上传。共 {{ datasets.length }} 个。
        </span>
        <div class="ds-toolbar-right">
          <a-button size="small" :loading="loading" @click="load">
            <template #icon><icon-refresh /></template>
            刷新
          </a-button>
          <a-button type="primary" size="small" @click="pickFile">
            <template #icon><icon-upload /></template>
            上传新建
          </a-button>
        </div>
      </div>

      <input ref="fileInput" type="file" accept=".csv,text/csv" style="display: none" @change="onPick" />

      <div v-if="!datasets.length" class="ds-empty muted">
        还没有测试集，点右上角「上传新建」上传一份 CSV。
      </div>
      <a-table
        v-else
        :data="datasets"
        :pagination="false"
        row-key="id"
        size="small"
        :scroll="{ y: 460 }"
        :bordered="false"
      >
        <template #columns>
          <a-table-column title="名称" data-index="name" :width="270" ellipsis tooltip />
          <a-table-column title="行数" data-index="rows" :width="80" />
          <a-table-column title="列数" :width="80">
            <template #cell="{ record }">{{ record.columns?.length || 0 }}</template>
          </a-table-column>
          <a-table-column title="创建时间" :width="200" ellipsis tooltip>
            <template #cell="{ record }">{{ fmtTime(record.created_at) }}</template>
          </a-table-column>
          <a-table-column title="操作" :width="320">
            <template #cell="{ record }">
              <div class="ds-actions">
                <a-button size="mini" type="text" @click="openPreview(record)">
                  <template #icon><icon-eye /></template>查看
                </a-button>
                <a-button size="mini" type="text" @click="download(record)">
                  <template #icon><icon-download /></template>下载
                </a-button>
                <a-button size="mini" type="text" @click="rename(record)">重命名</a-button>
                <a-button size="mini" type="text" status="danger" @click="remove(record)">删除</a-button>
              </div>
            </template>
          </a-table-column>
        </template>
      </a-table>
    </div>
  </a-modal>

  <!-- 内容预览（独立根节点，避免与上面的管理弹框嵌套导致不渲染） -->
  <a-modal
    :visible="previewOpen"
    fullscreen
    :footer="false"
    :mask-closable="true"
    class="ds-preview-modal"
    @cancel="previewOpen = false"
  >
    <template #title>
      <div class="pv-title">
        <icon-file />
        <span class="pv-name" :title="preview.name">{{ preview.name || '测试集预览' }}</span>
        <a-tag size="small" color="arcoblue">{{ preview.rows }} 行</a-tag>
        <a-tag size="small">{{ preview.columns.length }} 列</a-tag>
        <a-tag v-if="previewLoading" size="small" color="orange">加载中…</a-tag>
      </div>
    </template>

    <div class="ds-preview">
      <div class="pv-toolbar">
        <span class="pv-tip">
          仅显示前 {{ preview.preview.length }} 行（共 {{ preview.rows }} 行），完整内容请下载 CSV。
        </span>
        <div class="pv-toolbar-right">
          <a-input
            v-model="previewFilter"
            size="small"
            allow-clear
            placeholder="在预览数据中搜索…"
            style="width: 240px"
          >
            <template #prefix><icon-search /></template>
          </a-input>
          <a-button size="small" :disabled="!previewSource" @click="downloadPreview">
            <template #icon><icon-download /></template>
            下载 CSV
          </a-button>
        </div>
      </div>

      <a-spin :loading="previewLoading" class="pv-body">
        <a-table
          :data="previewRows"
          :pagination="false"
          size="small"
          stripe
          :scroll="{ x: '100%', y: tableHeight }"
          :bordered="false"
          class="pv-table"
        >
          <template #columns>
            <a-table-column
              v-for="c in preview.columns"
              :key="c"
              :title="c"
              :data-index="c"
              :width="colWidth"
              ellipsis
              tooltip
            />
            <a-table-column v-if="!preview.columns.length" title="内容">
              <template #cell>
                <span class="pv-placeholder">{{ previewLoading ? '加载中…' : '暂无数据' }}</span>
              </template>
            </a-table-column>
          </template>
          <template #empty>
            <div class="pv-placeholder">
              {{ previewLoading ? '加载中…' : previewFilter ? '没有匹配的行' : '暂无数据' }}
            </div>
          </template>
        </a-table>
      </a-spin>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Modal } from '@arco-design/web-vue'
import { api, getToken } from '@/api/client'
import { toast, promptInput } from '@/utils/feedback'

interface BenchDataset {
  id: string
  name: string
  rows: number
  columns: string[]
  created_at?: string
}

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [v: boolean] }>()

const datasets = ref<BenchDataset[]>([])
const loading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const previewOpen = ref(false)
const previewLoading = ref(false)
const preview = ref<{ name: string; columns: string[]; rows: number; preview: Array<Record<string, string>> }>({
  name: '',
  columns: [],
  rows: 0,
  preview: [],
})

/** 当前预览对应的测试集（用于弹框内「下载 CSV」）。 */
const previewSource = ref<BenchDataset | null>(null)
const previewFilter = ref('')

const previewRows = computed(() => {
  const q = previewFilter.value.trim().toLowerCase()
  const rows = preview.value.preview
  if (!q) return rows
  return rows.filter((r) => Object.values(r).some((v) => String(v ?? '').toLowerCase().includes(q)))
})

/** 预览表格列宽：列少时铺满，列多时收窄并横向滚动。 */
const colWidth = computed(() => {
  const n = Math.max(1, preview.value.columns.length)
  const usable = Math.max(640, window.innerWidth * 0.86)
  return Math.max(180, Math.min(460, Math.floor(usable / n)))
})

/** 预览表格高度：全屏弹框内填满剩余空间，跟随窗口变化。 */
const viewportH = ref(window.innerHeight)
/** 头部标题栏 + 工具条 + 内边距的占位高度。 */
const CHROME_H = 210
const tableHeight = computed(() => Math.max(240, viewportH.value - CHROME_H))
function onResize() {
  viewportH.value = window.innerHeight
}
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

function downloadPreview() {
  if (previewSource.value) void download(previewSource.value)
}

/** 极简 CSV 解析：支持引号包裹、字段内逗号、转义引号、CRLF。 */
function parseCsv(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let field = ''
  let inQuotes = false
  const s = text.replace(/^\uFEFF/, '')
  for (let i = 0; i < s.length; i++) {
    const c = s[i]
    if (inQuotes) {
      if (c === '"') {
        if (s[i + 1] === '"') {
          field += '"'
          i++
        } else {
          inQuotes = false
        }
      } else {
        field += c
      }
    } else if (c === '"') {
      inQuotes = true
    } else if (c === ',') {
      row.push(field)
      field = ''
    } else if (c === '\n') {
      if (field !== '' || row.length) {
        row.push(field)
        rows.push(row)
      }
      row = []
      field = ''
    } else if (c !== '\r') {
      field += c
    }
  }
  if (field !== '' || row.length) {
    row.push(field)
    rows.push(row)
  }
  return rows
}

/** 兜底方案：直接取原始 CSV 在前端解析（老后端没有 preview 接口时也能查看）。 */
async function loadCsvPreview(ds: BenchDataset, limit: number) {
  const res = await fetch(`/api/bench/datasets/${ds.id}/csv`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  if (!res.ok) throw new Error('读取测试集失败')
  const all = parseCsv(await res.text())
  const columns = (all[0] || []).map((c, i) => c || `列${i + 1}`)
  const body = all.slice(1).filter((r) => r.length && r.some((v) => v !== ''))
  const rows = body.slice(0, limit).map((r) => {
    const obj: Record<string, string> = {}
    columns.forEach((c, i) => {
      obj[c] = r[i] ?? ''
    })
    return obj
  })
  return { name: ds.name, columns, rows: body.length, preview: rows }
}

async function load() {
  loading.value = true
  try {
    datasets.value = await api.get<BenchDataset[]>('/api/bench/datasets')
  } catch {
    datasets.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.visible,
  (v) => {
    if (v) load()
    else previewOpen.value = false
  },
)

function fmtTime(t?: string) {
  if (!t) return '—'
  return t.replace('T', ' ').slice(0, 16)
}

function pickFile() {
  fileInput.value?.click()
}

async function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (file.size > 10 * 1024 * 1024) {
    toast.error('文件超过 10MB')
    return
  }
  const defaultName = file.name.replace(/\.csv$/i, '') || '测试集'
  const name = await promptInput('新建测试集', defaultName)
  if (name === null) return

  const fd = new FormData()
  fd.append('file', file)
  fd.append('name', name.trim() || defaultName)
  try {
    const res = await fetch('/api/bench/datasets', {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: fd,
    })
    if (!res.ok) {
      const d = await res.json().catch(() => ({}))
      throw new Error(d.detail || '创建测试集失败')
    }
    const info = await res.json()
    toast.success(`测试集已保存：${info.name}（${info.rows} 行）`)
    await load()
  } catch (err: any) {
    toast.error(err.message || '创建测试集失败')
  }
}

async function openPreview(ds: BenchDataset) {
  // 先开弹框再取数：点击立即有反馈，加载态在弹框内显示
  previewSource.value = ds
  previewFilter.value = ''
  preview.value = { name: ds.name, columns: [], rows: ds.rows, preview: [] }
  previewOpen.value = true
  previewLoading.value = true
  try {
    preview.value = await api.get<typeof preview.value>(
      `/api/bench/datasets/${ds.id}/preview?limit=50`,
    )
  } catch {
    // 老后端没有 preview 接口时，退回前端解析原始 CSV
    try {
      preview.value = await loadCsvPreview(ds, 50)
    } catch (err: any) {
      previewOpen.value = false
      toast.error(err.message || '预览失败')
    }
  } finally {
    previewLoading.value = false
  }
}

async function download(ds: BenchDataset) {
  try {
    const res = await fetch(`/api/bench/datasets/${ds.id}/csv`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!res.ok) throw new Error('下载测试集失败')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${ds.name}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err: any) {
    toast.error(err.message || '下载失败')
  }
}

async function rename(ds: BenchDataset) {
  const newName = await promptInput('重命名测试集', ds.name)
  if (newName === null) return
  const trimmed = newName.trim()
  if (!trimmed || trimmed === ds.name) return
  try {
    await api.put(`/api/bench/datasets/${ds.id}`, { name: trimmed })
    ds.name = trimmed
    toast.success('已重命名')
  } catch (err: any) {
    toast.error(err.message || '重命名失败')
  }
}

function remove(ds: BenchDataset) {
  Modal.warning({
    title: `删除测试集「${ds.name}」？`,
    content: '只删除测试集文件，已跑过的任务记录与结果不受影响。',
    okText: '删除',
    okButtonProps: { status: 'danger' },
    cancelText: '取消',
    hideCancel: false,
    onOk: async () => {
      try {
        await api.del(`/api/bench/datasets/${ds.id}`)
        toast.success('测试集已删除')
        await load()
      } catch (err: any) {
        toast.error(err.message || '删除失败')
      }
    },
  })
}
</script>

<style scoped lang="less">
.ds-manager {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 470px;
}

.ds-actions {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 2px;
  white-space: nowrap;

  :deep(.arco-btn) {
    padding: 0 6px;
    flex-shrink: 0;
  }
}

.ds-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;

  .muted {
    flex: 1;
    min-width: 0;
    font-size: 0.86em;
    color: var(--color-text-3);
    line-height: 1.5;
  }

  .ds-toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
}

.ds-empty {
  padding: 28px 0;
  text-align: center;
  font-size: 0.86em;
  color: var(--color-text-3);
}

.ds-preview {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
  min-height: 0;
}

/* 预览弹框标题行 */
.pv-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;

  > .pv-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 1em;
    font-weight: 600;
    color: var(--color-text-1);
  }
}

.pv-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 4px 12px;
  border-bottom: 1px solid var(--ui-border-soft);

  .pv-tip {
    flex: 1;
    min-width: 0;
    font-size: 0.86em;
    color: var(--color-text-3);
    line-height: 1.5;
  }

  .pv-toolbar-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
}

/* 预览表格：放宽行高与内边距，避免过密 */
.pv-body {
  display: block;
  width: 100%;
}

.pv-table {
  :deep(.arco-table-th) {
    background: var(--ui-bg-subtle) !important;
  }

  :deep(.arco-table-th .arco-table-cell) {
    padding: 10px 16px;
    font-weight: 600;
    color: var(--color-text-2);
    white-space: nowrap;
  }

  :deep(.arco-table-td .arco-table-cell) {
    padding: 10px 16px;
    line-height: 1.65;
    color: var(--color-text-1);
  }

  :deep(.arco-table-tr:hover .arco-table-td) {
    background: var(--ui-bg-hover);
  }
}

.pv-placeholder {
  display: block;
  padding: 32px 0;
  text-align: center;
  font-size: 0.9em;
  color: var(--color-text-3);
}
</style>

<style lang="less">
/* 全屏预览弹框：去掉圆角，避免四角露出遮罩 */
.ds-preview-modal,
.ds-preview-modal .arco-modal {
  border-radius: 0;
}
</style>
