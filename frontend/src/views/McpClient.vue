<template>
  <div class="mcp-client">
    <!-- 左：Server 列表 -->
    <div class="panel server-panel">
      <div class="panel-header">
        <span>MCP Servers</span>
        <el-button size="small" type="primary" plain :icon="Plus" @click="openAdd">添加</el-button>
      </div>
      <div class="server-list">
        <div
          v-for="s in store.servers"
          :key="s.name"
          class="server-item"
          :class="{ active: store.selectedServer === s.name }"
          @click="store.loadTools(s.name)"
        >
          <div class="server-name">{{ s.name }}</div>
          <div class="server-url" :title="s.url">{{ s.url }}</div>
          <div class="server-actions">
            <el-button size="small" link @click.stop="onTest(s.name)">测试</el-button>
            <el-button size="small" link @click.stop="openEdit(s)">编辑</el-button>
            <el-button size="small" link type="danger" @click.stop="onDelete(s.name)">删除</el-button>
          </div>
        </div>
        <el-empty v-if="!store.servers.length" description="暂无 Server" :image-size="60" />
      </div>
    </div>

    <!-- 右：工具列表 + 结果 -->
    <div class="panel tool-panel">
      <div v-if="!store.selectedServer" class="empty-tip">
        <el-empty description="选择左侧 MCP Server 查看工具" />
      </div>
      <template v-else>
        <div class="tool-header">{{ store.selectedServer }} 的工具</div>
        <div v-if="store.error" class="error-box">{{ store.error }}</div>
        <div class="tool-list">
          <el-collapse v-if="store.tools.length">
            <el-collapse-item v-for="t in store.tools" :key="t.name" :name="t.name">
              <template #title>
                <div class="tool-title">
                  <span class="tool-name">{{ t.name }}</span>
                  <span class="tool-desc">{{ t.description }}</span>
                </div>
              </template>
              <div class="tool-detail">
                <div class="detail-label">inputSchema</div>
                <MonacoEditor :model-value="JSON.stringify(t.input_schema, null, 2)" language="json" read-only height="180px" />
                <el-button size="small" type="primary" style="margin-top: 8px" @click="openCall(t)">调用</el-button>
              </div>
            </el-collapse-item>
          </el-collapse>
          <el-empty v-else description="无可用工具" :image-size="60" />
        </div>

        <!-- 调用结果 -->
        <div v-if="store.lastResult || store.loading" class="result-box">
          <div class="detail-label">调用结果</div>
          <div v-if="store.loading" class="loading-tip">调用中...</div>
          <template v-else>
            <el-tag :type="store.lastResult?.is_error ? 'danger' : 'success'" size="small">
              {{ store.lastResult?.is_error ? '错误' : '成功' }}
            </el-tag>
            <MonacoEditor :model-value="JSON.stringify(store.lastResult?.content, null, 2)" language="json" read-only height="240px" auto-scroll-to-end />
          </template>
        </div>
      </template>
    </div>

    <!-- 添加/编辑 Server 对话框 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑 Server' : '添加 Server'" width="520px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="name"><el-input v-model="form.name" :disabled="editing" /></el-form-item>
        <el-form-item label="url"><el-input v-model="form.url" placeholder="http://127.0.0.1:8001/mcp" /></el-form-item>
        <el-form-item label="headers">
          <el-input v-model="headersText" type="textarea" :rows="3" placeholder='{"Authorization":"Bearer xxx"}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 调用工具对话框 -->
    <el-dialog v-model="callDialogVisible" :title="`调用 ${callTool?.name}`" width="600px">
      <div class="detail-label">参数（JSON）</div>
      <MonacoEditor v-model="callArgs" language="json" height="240px" />
      <template #footer>
        <el-button @click="callDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="store.loading" @click="onCall">调用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import MonacoEditor from '@/components/MonacoEditor.vue'
import { useMcpStore, type McpServer, type McpTool } from '@/stores/mcp'

const store = useMcpStore()

const dialogVisible = ref(false)
const editing = ref(false)
const form = ref<McpServer>({ name: '', url: '', headers: {} })
const headersText = ref('{}')

const callDialogVisible = ref(false)
const callTool = ref<McpTool | null>(null)
const callArgs = ref('{}')

onMounted(() => store.loadServers())

function openAdd() {
  editing.value = false
  form.value = { name: '', url: '', headers: {} }
  headersText.value = '{}'
  dialogVisible.value = true
}

function openEdit(s: McpServer) {
  editing.value = true
  form.value = { ...s }
  headersText.value = JSON.stringify(s.headers || {}, null, 2)
  dialogVisible.value = true
}

async function onSave() {
  try {
    form.value.headers = JSON.parse(headersText.value || '{}')
  } catch {
    ElMessage.error('headers 不是合法 JSON')
    return
  }
  try {
    if (editing.value) await store.updateServer(form.value.name, form.value)
    else await store.addServer(form.value)
    dialogVisible.value = false
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error((e as Error).message)
  }
}

async function onDelete(name: string) {
  await ElMessageBox.confirm(`删除 MCP Server '${name}'？`, '确认', { type: 'warning' })
  await store.deleteServer(name)
  ElMessage.success('已删除')
}

async function onTest(name: string) {
  const r = await store.testServer(name)
  r.ok ? ElMessage.success(r.message) : ElMessage.error(r.message)
}

function openCall(tool: McpTool) {
  callTool.value = tool
  // 基于 inputSchema 生成示例参数（兜底空对象）
  callArgs.value = '{}'
  callDialogVisible.value = true
}

async function onCall() {
  if (!callTool.value || !store.selectedServer) return
  let args: Record<string, unknown>
  try {
    args = JSON.parse(callArgs.value)
  } catch {
    ElMessage.error('参数不是合法 JSON')
    return
  }
  await store.callTool(store.selectedServer, callTool.value.name, args)
  callDialogVisible.value = false
}
</script>

<style lang="less" scoped>
.mcp-client { display: flex; height: 100%; gap: 1px; background: var(--el-border-color); }
.panel { background: #fff; overflow: auto; display: flex; flex-direction: column; }
.server-panel { width: 300px; flex-shrink: 0; }
.tool-panel { flex: 1; min-width: 0; padding: 8px; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid var(--el-border-color); font-weight: 600; }
.server-list { flex: 1; overflow-y: auto; }
.server-item { padding: 10px 12px; border-bottom: 1px solid var(--el-border-color-lighter); cursor: pointer; }
.server-item.active { background: var(--el-color-primary-light-9); }
.server-item:hover { background: var(--el-fill-color-light); }
.server-name { font-weight: 600; }
.server-url { font-size: 12px; color: var(--el-text-color-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.server-actions { margin-top: 4px; }
.tool-header { font-weight: 600; padding: 4px 0 8px; }
.tool-list { flex: 1; overflow-y: auto; }
.tool-title { display: flex; gap: 12px; align-items: center; }
.tool-name { font-weight: 600; }
.tool-desc { color: var(--el-text-color-secondary); font-size: 12px; }
.tool-detail { padding: 4px 0; }
.detail-label { font-weight: 600; margin: 4px 0; }
.result-box { margin-top: 12px; }
.error-box { color: var(--el-color-danger); padding: 8px; background: var(--el-color-danger-light-9); border-radius: 4px; margin-bottom: 8px; }
.loading-tip { padding: 8px; color: var(--el-text-color-secondary); }
.empty-tip { display: flex; align-items: center; justify-content: center; height: 100%; }
</style>
