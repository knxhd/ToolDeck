<template>
  <a-drawer
    :visible="visible"
    :width="560"
    title="批量测试 / 压测"
    @cancel="close"
    :footer="false"
  >
    <div class="bench-drawer">
      <div v-if="loopbackTip" class="loopback-tip">
        <icon-info-circle />
        <span>请求地址含回环地址，发送时会解析为 <b>{{ loopbackTip }}</b>（设置 → 网络 可调整）</span>
      </div>

      <!-- 配置区 -->
      <section class="cfg">
        <div class="row">
          <label>任务名称</label>
          <a-input v-model="name" placeholder="批量测试" />
        </div>

        <div class="row">
          <label class="label-inline">
            测试集
            <a-tooltip position="right" content="测试集是保存下来的 CSV 数据，上传一次即可反复压测，不用每次重新上传">
              <icon-question-circle class="tips-ico" />
            </a-tooltip>
          </label>
          <input ref="fileInput" type="file" accept=".csv,text/csv" style="display: none" @change="onPick" />
          <div class="ds-pick">
            <a-select
              v-model="datasetId"
              placeholder="选择测试集"
              :loading="dsLoading"
              allow-search
              allow-clear
              style="flex: 1; min-width: 0"
            >
              <a-option v-for="d in datasets" :key="d.id" :value="d.id">
                {{ d.name }}（{{ d.rows }} 行）
              </a-option>
              <template #empty>还没有测试集，点右侧「新建」上传 CSV</template>
            </a-select>
            <a-button title="上传 CSV 新建测试集" @click="pickFile">
              <template #icon><icon-plus /></template>
              新建
            </a-button>
            <a-button :disabled="!currentDataset" title="下载测试集原始 CSV" @click="downloadDataset">
              <template #icon><icon-download /></template>
            </a-button>
            <a-button
              :disabled="!currentDataset"
              status="danger"
              title="删除测试集"
              @click="removeDataset"
            >
              <template #icon><icon-delete /></template>
            </a-button>
          </div>
          <div v-if="currentDataset" class="upload-info">
            <a-tag color="green">{{ currentDataset.name }}</a-tag>
            <span class="muted">{{ currentDataset.rows }} 行 · {{ currentDataset.columns.length }} 列</span>
            <a-button size="mini" type="text" @click="renameDataset">重命名</a-button>
          </div>
        </div>

        <div v-if="currentDataset" class="row">
          <label class="label-inline">
            输入列
            <a-tooltip
              position="right"
              content="测试集的列名，用于替换请求里的 {{占位符}}。勾选的列会一并写进结果 CSV，便于对照「输入 → 输出」；不影响请求本身。"
            >
              <icon-question-circle class="tips-ico" />
            </a-tooltip>
          </label>
          <div class="chips">
            <a-tag
              v-for="c in currentDataset.columns"
              :key="c"
              :color="inputCols.includes(c) ? 'arcoblue' : 'gray'"
              class="chip-toggle"
              @click="toggleInputCol(c)"
            >
              <icon-check v-if="inputCols.includes(c)" class="chip-ck" />{{ c }}
            </a-tag>
            <a-button size="mini" type="text" @click="selectAllInputCols">全选</a-button>
            <a-button size="mini" type="text" @click="clearInputCols">清空</a-button>
          </div>
          <p class="hint muted">
            共 {{ currentDataset.columns.length }} 列，已勾选 {{ inputCols.length }} 列写入结果 CSV
            <template v-if="!inputCols.length">（不勾选则只保留指标列与自定义列）</template>。
          </p>
        </div>

        <div class="row two">
          <div>
            <label>并发数</label>
            <a-input-number v-model="concurrency" :min="1" :max="100" style="width: 100%" add-before="1"
              add-after="100" />
          </div>
          <div>
            <label>OpenAI 流式接口(SSE)</label>
            <a-switch v-model="streaming" checked-text="流式" unchecked-text="普通" />
          </div>
        </div>

        <div class="row">
          <label class="label-inline">
            自定义结果列
            <a-tooltip position="right" :content-style="{ maxWidth: '400px', lineHeight: '1.65' }">
              <template #content>
                <div class="tips-body">
                  <p>固定指标列（序号/状态码/耗时等）始终保留；自定义列追加在其后。</p>
                  <p>
                    结果 CSV 列顺序：勾选的输入列（{{ inputCols.length }} 列）→ 指标列 → 自定义列，可直接对照「输入
                    → 输出」。
                  </p>
                  <p>
                    路径示例：<code>response.data</code>、<code>response.data[0].id</code>、<code>data.items.0.name</code>（忽略
                    <code>response.</code> / <code>body.</code> 前缀）。
                  </p>
                  <p v-if="streaming">
                    流式：每帧下发后，某列若还没取到值，就从该帧数据里提取，取到即定稿；帧内取不到值则跳过该帧。全部帧都没取到值则该列留空。
                  </p>
                  <p v-else>非流式：请求结束后从响应 JSON 里按路径取值；响应不是 JSON 时该列留空。</p>
                </div>
              </template>
              <icon-question-circle class="tips-ico" />
            </a-tooltip>
          </label>
          <div v-if="streaming" class="sys-col">
            <span class="muted">系统默认列</span>
            <a-tag color="gray">content（完整文本）</a-tag>
          </div>
          <div v-for="(c, i) in customCols" :key="i" class="col-row">
            <a-input v-model="c.title" placeholder="表头名，如 total_tokens" allow-clear size="small" />
            <a-input v-model="c.path" placeholder="取值路径，如 response.usage.total_tokens" allow-clear size="small" />
            <a-button size="small" type="text" status="danger" title="删除该列" @click="removeCol(i)">
              <template #icon><icon-delete /></template>
            </a-button>
          </div>
          <a-button size="small" long @click="addCol">
            <template #icon><icon-plus /></template>
            添加提取列
          </a-button>
        </div>

        <a-button type="primary" long :loading="starting" :disabled="!currentDataset" @click="start">
          开始测试
        </a-button>
        <div v-if="resolvedUrl" class="resolved-url" :title="resolvedUrl">
          <span class="muted">将请求：</span>
          <b>{{ method }}</b> {{ resolvedUrl }}
        </div>
        <p v-if="!currentDataset" class="hint muted">
          先选择一个测试集，或点「新建」上传 CSV 保存为测试集；测试集每一行会替换模板里与表头同名的占位符，并发起一次请求。
        </p>
      </section>

      <a-divider>
        <span class="jobs-head">
          任务记录
          <a-button size="mini" type="text" :loading="refreshing" @click="refresh" title="刷新进度">
            <template #icon><icon-refresh /></template>刷新
          </a-button>
          <a-switch v-model="showAll" size="small" @change="loadJobs" />
          <span class="muted">全部接口</span>
        </span>
      </a-divider>

      <!-- 任务列表 -->
      <section class="jobs">
        <div v-if="!jobs.length" class="empty muted">
          {{ showAll ? '暂无任务' : '本接口暂无任务记录' }}
        </div>
        <div v-for="j in jobs" :key="j.id" class="job-card">
          <div class="job-head">
            <span class="job-name">{{ j.name }}</span>
            <a-tag :color="statusColor(j.status)">{{ statusText(j.status) }}</a-tag>
          </div>

          <div v-if="j.dataset_id" class="job-ds">
            <icon-file class="ds-ico" />
            <span class="ds-name" :title="j.dataset_name">{{ j.dataset_name || '测试集' }}</span>
            <a-tag v-if="dsState(j) === 'changed'" size="small" color="orange">数据已变更</a-tag>
            <a-tag v-else-if="dsState(j) === 'missing'" size="small">测试集已删除</a-tag>
          </div>

          <div
            v-if="j.status === 'running' || j.status === 'cancelled'"
            class="bar-wrap"
          >
            <div class="bar">
              <div
                class="bar-fill"
                :class="{ warn: j.status === 'cancelled' }"
                :style="{ width: Math.min(100, Math.round((j.done / j.total) * 100)) + '%' }"
              ></div>
            </div>
            <span class="bar-text">{{ Math.min(100, Math.round((j.done / j.total) * 100)) }}%</span>
          </div>

          <div class="job-meta">
            <span v-if="j.total">进度 {{ j.done }}/{{ j.total }}</span>
            <span v-if="j.status === 'done'">成功 <b class="ok">{{ j.success }}</b> / 失败
              <b :class="{ err: j.fail > 0 }">{{ j.fail }}</b></span>
            <span v-if="j.stats && j.stats.avg_ms">avg {{ j.stats.avg_ms }}ms</span>
            <span v-if="j.stats && j.stats.p95_ms">p95 {{ j.stats.p95_ms }}ms</span>
            <span v-if="j.stats && j.stats.ttft_avg_ms">TTFT {{ j.stats.ttft_avg_ms }}ms</span>
            <span class="muted">{{ j.created_at }}</span>
          </div>
          <div v-if="j.error" class="job-err">{{ j.error }}</div>

          <div class="job-actions">
            <a-button
              v-if="j.status === 'done'"
              size="mini"
              type="text"
              @click="openReport(j)"
            >
              <template #icon><icon-chart-bar /></template>查看报告
            </a-button>
            <a-button
              v-if="j.status === 'running'"
              size="mini"
              type="text"
              status="warning"
              :disabled="isCancelling(j)"
              @click="cancel(j)"
            >
              <template #icon><icon-stop /></template>{{ isCancelling(j) ? '取消中…' : '取消' }}
            </a-button>
            <a-button size="mini" type="text" :disabled="j.status === 'running'" @click="openResult(j)">
              <template #icon><icon-eye /></template>查看结果
            </a-button>
            <a-button size="mini" type="text" :disabled="j.status === 'running'"
              @click="download(j, 'csv', 'result', '?with_annotations=1')">
              <template #icon><icon-download /></template>下载结果(CSV)
            </a-button>
            <a-button size="mini" type="text" @click="download(j, 'params', 'params')">
              <template #icon><icon-upload /></template>下载参数
            </a-button>
            <a-button
              size="mini"
              type="text"
              status="danger"
              :disabled="!canDelete(j)"
              :title="canDelete(j) ? '删除该任务记录' : '任务执行中，需先取消并等待结束后才能删除'"
              @click="remove(j)"
            >
              <template #icon><icon-delete /></template>删除
            </a-button>
          </div>

          <!-- 取消中遮罩：任务在收尾前既不显示可删除状态，也挡住误操作 -->
          <div v-if="isCancelling(j)" class="job-mask">
            <icon-loading class="spin" />
            <span>正在取消，等待当前请求结束后收尾…</span>
          </div>
        </div>
      </section>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Modal } from '@arco-design/web-vue'
import { api, getToken } from '@/api/client'
import { toast, promptInput } from '@/utils/feedback'
import { useEnvironmentsStore } from '@/stores/environments'
import { PLACEHOLDER_SOURCE, renderVars } from '@/utils/env'
import { getLoopbackTarget, hasLoopback, loadNetHost } from '@/utils/loopback'
import type { HttpRequestData } from '@/api/types'

const props = defineProps<{ visible: boolean; request: HttpRequestData; scopeKey?: string }>()
const emit = defineEmits<{ 'update:visible': [v: boolean] }>()

const envStore = useEnvironmentsStore()

/** 测试集：上传一次保存下来，后续批量测试直接选择，不用重复上传。 */
interface BenchDataset {
  id: string
  name: string
  rows: number
  columns: string[]
  created_at?: string
  /** 内容哈希，用于对比任务记录快照与当前测试集是否一致 */
  hash?: string
}

const LAST_DATASET_KEY = 'api-tool.bench.dataset'

const name = ref('批量测试')
const concurrency = ref(10)
const streaming = ref(false)
const datasets = ref<BenchDataset[]>([])
const datasetId = ref('')
const dsLoading = ref(false)
const currentDataset = computed(
  () => datasets.value.find((d) => d.id === datasetId.value) || null,
)
/** 自定义结果列：{ 表头名, 取值路径 }，追加在固定指标列之后。 */
const customCols = ref<Array<{ title: string; path: string }>>([])
/** 要写进结果 CSV 的测试集输入列（原列名）；只写勾选的，避免 10 列数据集把结果撑爆。 */
const inputCols = ref<string[]>([])
/** 任务记录是否显示所有接口（默认只看当前接口）。 */
const showAll = ref(false)
/** 当前请求 URL 含回环地址时，提示会被解析成什么。 */
const loopbackTip = computed(() => (hasLoopback(props.request.url || '') ? getLoopbackTarget() : ''))
const starting = ref(false)
const refreshing = ref(false)
const jobs = ref<any[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
let timer: number | null = null

/* ---------------- 配置随接口保存 / 打开时自动恢复 ---------------- */

interface BenchCfg {
  dataset_id?: string
  concurrency?: number
  streaming?: boolean
  columns?: Array<{ title: string; path: string }>
  input_cols?: string[]
  name?: string
}

const CFG_KEY = 'api-tool.bench.cfg'
/** 每个接口（scope）一份本地缓存，接口没保存时也不会丢配置。 */
function cfgStorageKey() {
  return `${CFG_KEY}:${props.scopeKey || 'default'}`
}

function readLocalCfg(): BenchCfg | null {
  try {
    const raw = localStorage.getItem(cfgStorageKey())
    return raw ? (JSON.parse(raw) as BenchCfg) : null
  } catch {
    return null
  }
}

let cfgReady = false

/** 打开抽屉 / 切换到别的接口时恢复配置：优先本地缓存（最近一次编辑），其次接口里保存的配置。 */
function applyConfig() {
  cfgReady = false
  const cfg = readLocalCfg() || props.request.bench || {}
  name.value = cfg.name || '批量测试'
  concurrency.value = cfg.concurrency ?? 10
  streaming.value = cfg.streaming ?? false
  customCols.value = (cfg.columns || []).map((c) => ({ title: c.title, path: c.path }))
  inputCols.value = [...(cfg.input_cols || [])]
  if (cfg.dataset_id) datasetId.value = cfg.dataset_id
  cfgReady = true
}

/** 配置变化：写回接口请求对象（保存接口时一起入库）并缓存到本地。 */
function persistConfig() {
  const cfg: BenchCfg = {
    name: name.value,
    concurrency: concurrency.value,
    streaming: streaming.value,
    columns: customCols.value.map((c) => ({ title: c.title, path: c.path })),
    input_cols: [...inputCols.value],
    dataset_id: datasetId.value,
  }
  const cur = props.request.bench
  if (!cur || JSON.stringify(cur) !== JSON.stringify(cfg)) {
    props.request.bench = cfg
  }
  try {
    localStorage.setItem(cfgStorageKey(), JSON.stringify(cfg))
  } catch {
    /* 本地缓存失败不影响主流程 */
  }
}

applyConfig()

const method = computed(() => props.request.method)

/** 模板里实际引用的占位符名（不含 $ 内置变量），用于给「输入列」做默认勾选。 */
const usedVars = computed<Set<string>>(() => {
  const names = new Set<string>()
  const re = new RegExp(PLACEHOLDER_SOURCE, 'g')
  const scan = (text?: string) => {
    if (!text) return
    re.lastIndex = 0
    let m: RegExpExecArray | null
    while ((m = re.exec(text))) {
      const n = m[1]
      if (n && !n.startsWith('$')) names.add(n)
    }
  }
  const r = props.request
  scan(r.url)
  for (const kv of r.headers || []) if (kv.enabled) scan(kv.value)
  for (const kv of r.params || []) if (kv.enabled) scan(kv.value)
  scan(r.body)
  return names
})

function toggleInputCol(col: string) {
  inputCols.value = inputCols.value.includes(col)
    ? inputCols.value.filter((c) => c !== col)
    : [...inputCols.value, col]
}

function selectAllInputCols() {
  inputCols.value = [...(currentDataset.value?.columns || [])]
}

function clearInputCols() {
  inputCols.value = []
}

/** 切换测试集：只保留新测试集里有的列；一列都没选时按模板占位符自动勾选。 */
watch(
  () => currentDataset.value?.id,
  () => {
    const cols = currentDataset.value?.columns || []
    const kept = inputCols.value.filter((c) => cols.includes(c))
    inputCols.value = kept.length ? kept : cols.filter((c) => usedVars.value.has(c))
  },
)
// 用当前环境变量解析后的真实 URL（内置占位符无法在前端完全还原，未解析的原样保留）
const resolvedUrl = computed(() => {
  const url = props.request.url || ''
  if (!url) return ''
  return renderVars(url, envStore.scopeVars)
})

function close() {
  emit('update:visible', false)
}

function addCol() {
  if (customCols.value.length >= 20) {
    toast.error('最多 20 个自定义列')
    return
  }
  customCols.value.push({ title: '', path: '' })
}

function removeCol(i: number) {
  customCols.value.splice(i, 1)
}

/** 校验并收集自定义列；返回 null 表示校验失败（已弹提示）。 */
function collectColumns(): Array<{ title: string; path: string }> | null {
  const out: Array<{ title: string; path: string }> = []
  const seen = new Set<string>()
  for (let i = 0; i < customCols.value.length; i++) {
    const title = customCols.value[i].title.trim()
    const path = customCols.value[i].path.trim()
    if (!title && !path) continue // 整行空着视为未填写
    if (!title || !path) {
      toast.error(`第 ${i + 1} 行：表头名与取值路径需同时填写`)
      return null
    }
    if (seen.has(title)) {
      toast.error(`表头名重复：${title}`)
      return null
    }
    seen.add(title)
    out.push({ title, path })
  }
  return out
}

function pickFile() {
  fileInput.value?.click()
}

/** 上传 CSV 并保存为新的测试集（名称默认取文件名，可改）。 */
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
  const dsName = await promptInput('新建测试集', defaultName)
  if (dsName === null) return

  const fd = new FormData()
  fd.append('file', file)
  fd.append('name', dsName.trim() || defaultName)
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
    const info: BenchDataset = await res.json()
    await loadDatasets(info.id)
    datasetId.value = info.id
    rememberDataset(info.id)
    toast.success(`测试集已保存：${info.name}（${info.rows} 行）`)
  } catch (err: any) {
    toast.error(err.message || '创建测试集失败')
  }
}

function rememberDataset(id: string) {
  if (id) localStorage.setItem(LAST_DATASET_KEY, id)
}

/** 拉取测试集列表；preferId 指定要选中的集，否则优先选上次用过的。 */
async function loadDatasets(preferId?: string) {
  dsLoading.value = true
  try {
    datasets.value = await api.get<BenchDataset[]>('/api/bench/datasets')
  } catch {
    datasets.value = []
  } finally {
    dsLoading.value = false
  }
  const wanted = preferId || datasetId.value || localStorage.getItem(LAST_DATASET_KEY) || ''
  if (wanted && datasets.value.some((d) => d.id === wanted)) {
    datasetId.value = wanted
  } else {
    datasetId.value = datasets.value[0]?.id || ''
  }
}

async function renameDataset() {
  const ds = currentDataset.value
  if (!ds) return
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

async function downloadDataset() {
  const ds = currentDataset.value
  if (!ds) return
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

function removeDataset() {
  const ds = currentDataset.value
  if (!ds) return
  Modal.warning({
    title: `删除测试集「${ds.name}」？`,
    content: '只删除测试集文件，已跑过的任务记录与结果不受影响。',
    okText: '删除',
    okButtonProps: { status: 'danger' },
    cancelText: '取消',
    hideCancel: false,
    onOk: async () => {
      await api.del(`/api/bench/datasets/${ds.id}`)
      toast.success('测试集已删除')
      await loadDatasets()
      rememberDataset(datasetId.value)
    },
  })
}

async function start() {
  if (!currentDataset.value) {
    toast.error('请先选择或新建测试集')
    return
  }
  const columns = collectColumns()
  if (columns === null) return
  // 开始测试前兜底落盘一次：确保这些配置随接口一起保存
  cfgReady = true
  persistConfig()
  starting.value = true
  try {
    // 模板 URL 的 host 可能藏在 {{var}} 里，只有后端渲染后才知道；
    // 这里按设置算出回环目标交给后端逐行改写，避免整批都连服务端自己的 127.0.0.1
    await loadNetHost()
    const loopbackTarget = getLoopbackTarget()
    await api.post('/api/bench/run', {
      name: name.value,
      dataset_id: datasetId.value,
      concurrency: concurrency.value,
      streaming: streaming.value,
      request: {
        method: props.request.method,
        url: props.request.url,
        headers: props.request.headers,
        params: props.request.params,
        body_type: props.request.body_type,
        body: props.request.body,
      },
      env_vars: { ...envStore.scopeVars },
      columns,
      input_columns: [...inputCols.value],
      scope_key: props.scopeKey || '',
      loopback_target: loopbackTarget,
    })
    toast.success('批量测试已在后台开始')
    await loadJobs()
  } catch (err: any) {
    toast.error(err.message || '发起失败')
  } finally {
    starting.value = false
  }
}

async function loadJobs() {
  const key = showAll.value ? '' : (props.scopeKey || '')
  const qs = key ? `?scope_key=${encodeURIComponent(key)}` : ''
  try {
    jobs.value = await api.get<any[]>(`/api/bench/jobs${qs}`)
  } catch {
    /* ignore */
  }
}

async function refresh() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await loadJobs()
    toast.success('已刷新')
  } finally {
    setTimeout(() => (refreshing.value = false), 400)
  }
}

/** 已点取消、等待收尾的任务（显示遮罩，期间禁止删除）。 */
const cancellingIds = ref<Record<string, boolean>>({})

function isCancelling(j: any): boolean {
  return !!cancellingIds.value[j.id]
}

/** 执行中（含取消收尾中）不允许删除任务记录。 */
function canDelete(j: any): boolean {
  return j.status !== 'running' && !isCancelling(j)
}

async function cancel(j: any) {
  if (isCancelling(j)) return
  cancellingIds.value[j.id] = true
  try {
    await api.post(`/api/bench/jobs/${j.id}/cancel`, {})
    toast.success('已发送取消请求，等待当前请求结束…')
    await loadJobs()
  } catch (err: any) {
    delete cancellingIds.value[j.id]
    toast.error(err.message || '取消失败')
    return
  }
  // 兜底：60 秒仍未结束就撤掉遮罩，避免一直卡住（此时仍不可删除，由后端 409 兜底）
  window.setTimeout(() => {
    const still = (jobs.value as any[]).find((x) => x.id === j.id)
    if (still && still.status === 'running' && cancellingIds.value[j.id]) {
      delete cancellingIds.value[j.id]
      toast.warning('取消请求已发送，但任务仍在执行（可能正在等待请求超时）')
    }
  }, 60_000)
}

function openResult(j: any) {
  // 结果查看页为独立路由，新窗口共享同源 localStorage 里的登录态
  window.open(`/bench/result/${j.id}`, '_blank')
}

function openReport(j: any) {
  // 直接在新窗口打开报告 HTML（浏览器会带 Authorization 由 fetch 不行，改用带 token 的下载链接）
  const token = getToken()
  const url = `/api/bench/jobs/${j.id}/report`
  // 用隐藏 fetch 拿 blob 再 open，避免 token 暴露在地址栏
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then((r) => {
      if (!r.ok) throw new Error('报告未生成')
      return r.blob()
    })
    .then((blob) => {
      const u = URL.createObjectURL(blob)
      window.open(u, '_blank')
      setTimeout(() => URL.revokeObjectURL(u), 60_000)
    })
    .catch((err) => toast.error(err.message || '打开报告失败'))
}

/** 任务记录的测试集快照与当前测试集是否一致。 */
function dsState(j: any): 'same' | 'changed' | 'missing' | 'none' {
  if (!j.dataset_id) return 'none'
  const cur = datasets.value.find((d) => d.id === j.dataset_id)
  if (!cur) return 'missing'
  // 老记录没有哈希，不做变更判断，避免误报
  if (!j.dataset_hash || !cur.hash) return 'same'
  return cur.hash === j.dataset_hash ? 'same' : 'changed'
}

function statusText(s: string) {
  return { running: '运行中', done: '已完成', failed: '失败', cancelled: '已取消' }[s] || s
}
function statusColor(s: string) {
  return { running: 'blue', done: 'green', failed: 'red', cancelled: 'orange' }[s] || 'gray'
}

/** 任务时间戳 yyyy-mm-dd-hhmmss */
function jobStamp(j: any): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  const raw = String(j?.created_at || '').replace(' ', 'T')
  const d = raw ? new Date(raw) : new Date()
  const t = Number.isNaN(d.getTime()) ? new Date() : d
  return `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}-${pad(t.getHours())}${pad(t.getMinutes())}${pad(t.getSeconds())}`
}

/** 测试集名_测试结果_yyyy-mm-dd-hhmmss（参数/标注各有标记） */
function fileBaseName(j: any, kind: 'csv' | 'params', query: string): string {
  const set = String(j?.dataset_name || j?.name || j?.id || '批量测试').replace(/[\\/:*?"<>|]/g, '_')
  const stamp = jobStamp(j)
  if (kind === 'params') return `${set}_测试参数_${stamp}`
  return `${set}_测试结果${query.includes('annotations') ? '_标注' : ''}_${stamp}`
}

async function download(j: any, kind: 'csv' | 'params', label: string, query = '') {
  try {
    const res = await fetch(`/api/bench/jobs/${j.id}/${kind}${query}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!res.ok) throw new Error(`下载${label}失败`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${fileBaseName(j, kind, query)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err: any) {
    toast.error(err.message || '下载失败')
  }
}

function remove(j: any) {
  if (!canDelete(j)) {
    toast.error('任务正在执行，请先取消并等待结束后再删除')
    return
  }
  Modal.warning({
    title: '删除该任务？',
    content: `将删除任务「${j.name}」及其参数/结果 CSV 文件，此操作不可恢复。`,
    okText: '删除',
    okButtonProps: { status: 'danger' },
    cancelText: '取消',
    hideCancel: false,
    onOk: async () => {
      try {
        await api.del(`/api/bench/jobs/${j.id}`)
      } catch (err: any) {
        toast.error(err.message || '删除失败')
        await loadJobs()
        return
      }
      jobs.value = jobs.value.filter((x) => x.id !== j.id)
      toast.success('已删除')
    },
  })
}

// 有运行中任务时轮询
watch(jobs, (list) => {
  // 任务已收尾（不再是 running）就清掉「取消中」遮罩
  for (const id of Object.keys(cancellingIds.value)) {
    const j = (list as any[]).find((x) => x.id === id)
    if (!j || j.status !== 'running') delete cancellingIds.value[id]
  }
  const running = list.some((j) => j.status === 'running')
  if (running && !timer) {
    timer = window.setInterval(loadJobs, 2000)
  } else if (!running && timer) {
    clearInterval(timer)
    timer = null
  }
})

// 打开抽屉时刷新任务记录与测试集；切换标签页导致所属接口变化时重取记录
watch(
  () => props.visible,
  (v) => {
    if (v) {
      loadJobs()
      loadDatasets()
    }
  },
)
watch(
  () => props.scopeKey,
  () => {
    if (props.visible) loadJobs()
  },
)
// 同一标签页换了接口对象（重新打开某个节点）时，恢复该接口的配置
watch(
  () => props.request,
  () => applyConfig(),
)
// 记住最近使用的测试集，下次打开抽屉自动选中
watch(datasetId, (v) => rememberDataset(v))

// 配置变化即时落盘（本地缓存 + 接口对象），开始测试/关闭抽屉都不会丢
watch(
  [name, concurrency, streaming, customCols, datasetId, inputCols],
  () => {
    if (cfgReady) persistConfig()
  },
  { deep: true },
)

onMounted(() => {
  loadJobs()
  loadDatasets()
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style lang="less" scoped>
.bench-drawer {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cfg {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  label {
    font-size: 0.86em;
    color: var(--el-text-color-secondary);
    font-weight: 600;
  }
  &.two {
    flex-direction: row;
    gap: 16px;
    > div { flex: 1; display: flex; flex-direction: column; gap: 6px; }
  }
}
.ds-pick {
  display: flex;
  align-items: center;
  gap: 6px;
}
.upload-info { display: flex; align-items: center; gap: 8px; }
.chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
/* 「自定义结果列」tooltip 内容：四段说明收进 ? 图标，面板上不再占高度 */
.tips-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.95em;
  line-height: 1.65;

  p { margin: 0; }

  code {
    font-family: var(--ui-font-mono, ui-monospace, monospace);
    padding: 0 3px;
    border-radius: var(--ui-radius-sm, 3px);
    background: rgba(255, 255, 255, 0.14);
  }
}
/* 输入列 chips：点击切换是否写进结果 CSV */
.chip-toggle { cursor: pointer; user-select: none; transition: opacity 0.12s ease; }
.chip-toggle:hover { opacity: 0.82; }
.chip-ck { margin-right: 2px; font-size: 0.86em; vertical-align: -1px; }
.hint { font-size: 0.86em; margin: 0; line-height: 1.6; }
.hint code {
  font-family: var(--ui-font-mono, ui-monospace, monospace);
  padding: 0 3px;
  border-radius: var(--ui-radius-sm, 3px);
  background: var(--ui-bg-subtle, rgba(0, 0, 0, 0.04));
}
.muted { color: var(--el-text-color-placeholder); font-size: 0.86em; }
.label-inline { display: inline-flex; align-items: center; gap: 4px; }
.tips-ico { color: var(--el-text-color-placeholder); cursor: help; }
.sys-col { display: flex; align-items: center; gap: 6px; }
.col-row {
  display: flex;
  align-items: center;
  gap: 6px;
  > :first-child { flex: 1; min-width: 0; }
  > :nth-child(2) { flex: 1.5; min-width: 0; }
  > :last-child { flex: none; }
}

.resolved-url {
  font-size: 0.86em;
  font-family: ui-monospace, 'JetBrains Mono', Menlo, monospace;
  word-break: break-all;
  line-height: 1.5;
  b { color: var(--c-put, #58a6ff); margin-right: 4px; }
}

.jobs-head {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.loopback-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  margin-bottom: 10px;
  border: 1px solid var(--color-warning-light-3, #ffcf8b);
  border-radius: 6px;
  background: var(--color-warning-light-1, #fff7e8);
  color: var(--color-text-2);
  font-size: 12px;
  line-height: 1.5;

  b { color: var(--color-text-1); }
}

.jobs { display: flex; flex-direction: column; gap: 10px; }
.job-card {
  position: relative;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* 取消中：半透明遮罩 + 转圈，挡住删除等操作 */
.job-mask {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 12px;
  border-radius: inherit;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(1.5px);
  font-size: 0.86em;
  color: var(--color-text-2);
  cursor: progress;

  .spin {
    color: var(--el-color-warning, #ff7d00);
    animation: job-spin 1s linear infinite;
  }
}

@keyframes job-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.job-head { display: flex; align-items: center; justify-content: space-between; }
.job-name { font-weight: 600; }
.job-ds {
  display: flex; align-items: center; gap: 6px;
  font-size: 0.86em; color: var(--el-text-color-secondary);
  .ds-ico { color: var(--color-text-3); flex-shrink: 0; }
  .ds-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px; }
}
.job-meta {
  display: flex; flex-wrap: wrap; gap: 12px;
  font-size: 0.86em; color: var(--el-text-color-secondary);
  .ok { color: var(--el-color-success); }
  .err { color: var(--el-color-danger); }
}
.job-err { color: var(--el-color-danger); font-size: 0.86em; }
.job-actions { display: flex; gap: 4px; flex-wrap: wrap; }
.bar-wrap { display: flex; align-items: center; gap: 8px; }
.bar {
  flex: 1; height: 6px; border-radius: 3px;
  background: var(--el-color-fill-1, rgba(0,0,0,0.06));
  overflow: hidden;
}
.bar-fill {
  height: 100%; border-radius: 3px;
  background: var(--el-color-primary, #165dff);
  transition: width 0.3s ease;
  &.warn { background: var(--el-color-warning, #ff7d00); }
}
.bar-text { font-size: 0.86em; color: var(--el-text-color-secondary); min-width: 38px; text-align: right; }
.empty { text-align: center; padding: 24px 0; }
</style>
