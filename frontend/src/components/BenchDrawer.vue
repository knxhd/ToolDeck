<template>
  <a-drawer
    :visible="visible"
    :width="560"
    title="批量测试 / 压测"
    @cancel="close"
    :footer="false"
  >
    <div class="bench-drawer">
      <!-- 配置区 -->
      <section class="cfg">
        <div class="row">
          <label>任务名称</label>
          <a-input v-model="name" placeholder="批量测试" />
        </div>

        <div class="row">
          <label>数据文件</label>
          <div class="file-box">
            <input ref="fileInput" type="file" accept=".csv,text/csv" style="display: none" @change="onPick" />
            <a-button long @click="pickFile">
              <template #icon><icon-upload /></template>
              上传 CSV（首行表头为占位符名）
            </a-button>
            <div v-if="upload" class="upload-info">
              <a-tag color="green">{{ upload.filename }}</a-tag>
              <span class="muted">{{ upload.rows }} 行</span>
            </div>
          </div>
        </div>

        <div v-if="upload" class="row">
          <label>占位符列</label>
          <div class="chips">
            <a-tag v-for="c in upload.columns" :key="c" color="arcoblue">{{ c }}</a-tag>
          </div>
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

        <a-button type="primary" long :loading="starting" :disabled="!upload" @click="start">
          开始测试
        </a-button>
        <div v-if="resolvedUrl" class="resolved-url" :title="resolvedUrl">
          <span class="muted">将请求：</span>
          <b>{{ method }}</b> {{ resolvedUrl }}
        </div>
        <p v-if="!upload" class="hint muted">先上传 CSV；CSV 每一行会替换模板里与表头同名的占位符，并发起一次请求。</p>
      </section>

      <a-divider>
        <span class="jobs-head">
          任务记录
          <a-button size="mini" type="text" :loading="refreshing" @click="refresh" title="刷新进度">
            <template #icon><icon-refresh /></template>刷新
          </a-button>
        </span>
      </a-divider>

      <!-- 任务列表 -->
      <section class="jobs">
        <div v-if="!jobs.length" class="empty muted">暂无任务</div>
        <div v-for="j in jobs" :key="j.id" class="job-card">
          <div class="job-head">
            <span class="job-name">{{ j.name }}</span>
            <a-tag :color="statusColor(j.status)">{{ statusText(j.status) }}</a-tag>
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
              v-if="j.status === 'running'"
              size="mini"
              type="text"
              status="warning"
              @click="cancel(j)"
            >
              <template #icon><icon-stop /></template>取消
            </a-button>
            <a-button size="mini" type="text" :disabled="j.status === 'running'" @click="download(j, 'csv', 'result')">
              <template #icon><icon-download /></template>下载结果
            </a-button>
            <a-button size="mini" type="text" @click="download(j, 'params', 'params')">
              <template #icon><icon-upload /></template>下载参数
            </a-button>
            <a-button size="mini" type="text" status="danger" @click="remove(j)">
              <template #icon><icon-delete /></template>删除
            </a-button>
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
import { toast } from '@/utils/feedback'
import { useEnvironmentsStore } from '@/stores/environments'
import { renderVars } from '@/utils/env'
import type { HttpRequestData } from '@/api/types'

const props = defineProps<{ visible: boolean; request: HttpRequestData }>()
const emit = defineEmits<{ 'update:visible': [v: boolean] }>()

const envStore = useEnvironmentsStore()

const name = ref('批量测试')
const concurrency = ref(10)
const streaming = ref(false)
const upload = ref<{ upload_id: string; filename: string; columns: string[]; rows: number } | null>(null)
const starting = ref(false)
const refreshing = ref(false)
const jobs = ref<any[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
let timer: number | null = null

const method = computed(() => props.request.method)
// 用当前环境变量解析后的真实 URL（内置占位符无法在前端完全还原，未解析的原样保留）
const resolvedUrl = computed(() => {
  const url = props.request.url || ''
  if (!url) return ''
  return renderVars(url, envStore.scopeVars)
})

function close() {
  emit('update:visible', false)
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
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await fetch('/api/bench/upload', {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: fd,
    })
    if (!res.ok) {
      const d = await res.json().catch(() => ({}))
      throw new Error(d.detail || '上传失败')
    }
    const info = await res.json()
    upload.value = info
    toast.success(`已上传：${info.rows} 行数据`)
  } catch (err: any) {
    toast.error(err.message || '上传失败')
  }
}

async function start() {
  const up = upload.value
  if (!up) return
  starting.value = true
  try {
    await api.post('/api/bench/run', {
      name: name.value,
      upload_id: up.upload_id,
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
    })
    upload.value = null
    toast.success('批量测试已在后台开始')
    await loadJobs()
  } catch (err: any) {
    toast.error(err.message || '发起失败')
  } finally {
    starting.value = false
  }
}

async function loadJobs() {
  try {
    jobs.value = await api.get<any[]>('/api/bench/jobs')
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

async function cancel(j: any) {
  try {
    await api.post(`/api/bench/jobs/${j.id}/cancel`, {})
    toast.success('已发送取消请求')
    await loadJobs()
  } catch (err: any) {
    toast.error(err.message || '取消失败')
  }
}

function statusText(s: string) {
  return { running: '运行中', done: '已完成', failed: '失败', cancelled: '已取消' }[s] || s
}
function statusColor(s: string) {
  return { running: 'blue', done: 'green', failed: 'red', cancelled: 'orange' }[s] || 'gray'
}

async function download(j: any, kind: 'csv' | 'params', label: string) {
  try {
    const res = await fetch(`/api/bench/jobs/${j.id}/${kind}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
    if (!res.ok) throw new Error(`下载${label}失败`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `benchmark-${label}-${j.name}-${j.id}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err: any) {
    toast.error(err.message || '下载失败')
  }
}

function remove(j: any) {
  Modal.warning({
    title: '删除该任务？',
    content: `将删除任务「${j.name}」及其参数/结果 CSV 文件，此操作不可恢复。`,
    okText: '删除',
    okButtonProps: { status: 'danger' },
    cancelText: '取消',
    hideCancel: false,
    onOk: async () => {
      await api.del(`/api/bench/jobs/${j.id}`)
      jobs.value = jobs.value.filter((x) => x.id !== j.id)
      toast.success('已删除')
    },
  })
}

// 有运行中任务时轮询
watch(jobs, (list) => {
  const running = list.some((j) => j.status === 'running')
  if (running && !timer) {
    timer = window.setInterval(loadJobs, 2000)
  } else if (!running && timer) {
    clearInterval(timer)
    timer = null
  }
})

onMounted(loadJobs)
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
    font-size: 12px;
    color: var(--el-text-color-secondary);
    font-weight: 600;
  }
  &.two {
    flex-direction: row;
    gap: 16px;
    > div { flex: 1; display: flex; flex-direction: column; gap: 6px; }
  }
}
.file-box { display: flex; flex-direction: column; gap: 8px; }
.upload-info { display: flex; align-items: center; gap: 8px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.hint { font-size: 12px; margin: 0; }
.muted { color: var(--el-text-color-placeholder); font-size: 12px; }

.resolved-url {
  font-size: 12px;
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

.jobs { display: flex; flex-direction: column; gap: 10px; }
.job-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.job-head { display: flex; align-items: center; justify-content: space-between; }
.job-name { font-weight: 600; }
.job-meta {
  display: flex; flex-wrap: wrap; gap: 12px;
  font-size: 12px; color: var(--el-text-color-secondary);
  .ok { color: var(--el-color-success); }
  .err { color: var(--el-color-danger); }
}
.job-err { color: var(--el-color-danger); font-size: 12px; }
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
.bar-text { font-size: 12px; color: var(--el-text-color-secondary); min-width: 38px; text-align: right; }
.empty { text-align: center; padding: 24px 0; }
</style>
