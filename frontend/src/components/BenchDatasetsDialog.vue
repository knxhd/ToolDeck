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
    :title="`预览 · ${preview.name || ''}`"
    width="1080px"
    :footer="false"
    class="ds-preview-modal"
    @cancel="previewOpen = false"
  >
    <div class="ds-preview">
      <div class="muted ds-preview-tip">
        共 {{ preview.rows }} 行 · {{ preview.columns.length }} 列，当前只显示前 {{ preview.preview.length }} 行。
      </div>
      <a-spin :loading="previewLoading" style="width: 100%">
        <a-table
          :data="preview.preview"
          :pagination="false"
          size="mini"
          :scroll="{ x: '100%', y: 420 }"
          :bordered="false"
        >
          <template #columns>
            <a-table-column
              v-for="c in preview.columns"
              :key="c"
              :title="c"
              :data-index="c"
              :width="180"
              ellipsis
              tooltip
            />
          </template>
        </a-table>
      </a-spin>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
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
  gap: 8px;
  min-height: 440px;

  .ds-preview-tip {
    font-size: 0.86em;
    color: var(--color-text-3);
  }
}
</style>
