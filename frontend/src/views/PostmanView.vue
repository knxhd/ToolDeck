<template>
  <div class="postman-view">
    <!-- 左侧：Collections + History -->
    <aside class="sidebar">
      <CollectionsTree @open="onOpenNode" />
      <div class="side-divider"></div>
      <div class="side-section">
        <div class="section-header" @click="historyOpen = !historyOpen">
          <el-icon><ArrowDown v-if="historyOpen" /><ArrowRight v-else /></el-icon>
          <span>History</span>
          <el-button v-if="history.length" size="small" type="danger" plain :disabled="!history.length" @click.stop="onClear">清空</el-button>
        </div>
        <div v-if="historyOpen" class="history-list">
          <div v-for="(item, i) in history" :key="i" class="history-item" @click="onLoadHistory(item)">
            <span class="m" :class="item.method.toLowerCase()">{{ item.method }}</span>
            <span class="u" :title="item.url">{{ item.url }}</span>
            <span class="s" :class="statusClass(item.status_code)">{{ item.status_code || '—' }}</span>
          </div>
          <el-empty v-if="!history.length" description="暂无历史" :image-size="40" />
        </div>
      </div>
    </aside>

    <!-- 右侧：标签页 + 工作区 -->
    <section class="workbench">
      <div class="tab-bar">
        <div
          v-for="t in wb.tabs"
          :key="t.id"
          class="tab"
          :class="{ active: t.id === wb.activeId }"
          @click="wb.setActive(t.id)"
        >
          <span class="tab-method" :class="t.kind === 'websocket' ? 'ws' : t.request.method.toLowerCase()">
            {{ t.kind === 'websocket' ? 'WS' : t.request.method }}
          </span>
          <span class="tab-title">{{ t.title }}</span>
          <el-icon class="tab-close" @click.stop="wb.closeTab(t.id)"><Close /></el-icon>
        </div>
        <el-dropdown trigger="click" @command="(k: string) => wb.openBlank(k as 'http' | 'websocket')">
          <el-button circle size="small" :icon="Plus" />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="http">HTTP Request</el-dropdown-item>
              <el-dropdown-item command="websocket">WebSocket</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div class="pane" v-if="wb.activeTab" :key="wb.activeTab.id">
        <template v-if="wb.activeTab.kind === 'http'">
          <div class="half top">
            <RequestPane :tab="wb.activeTab" @send="onSend" @cancel="wb.cancel" />
          </div>
          <div class="half bottom">
            <ResponsePane :tab="wb.activeTab" />
          </div>
        </template>
        <WebSocketPane v-else :tab="wb.activeTab" />
      </div>
      <div class="empty" v-else>
        <el-empty description="从左侧 Collections 选择请求，或点击 + 新建" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { ArrowDown, ArrowRight, Close, Plus } from '@element-plus/icons-vue'

import CollectionsTree from '@/components/CollectionsTree.vue'
import RequestPane from '@/components/RequestPane.vue'
import ResponsePane from '@/components/ResponsePane.vue'
import WebSocketPane from '@/components/WebSocketPane.vue'
import { useCollectionsStore } from '@/stores/collections'
import { useWorkbenchStore } from '@/stores/workbench'
import { useHttpStore } from '@/stores/http'
import { api } from '@/api/client'
import type { CollectionNode, HttpCallRecord } from '@/api/types'

const collections = useCollectionsStore()
const wb = useWorkbenchStore()
const http = useHttpStore()

const history = ref<HttpCallRecord[]>([])
const historyOpen = ref(true)

onMounted(async () => {
  await Promise.all([collections.load(), http.loadHistory()])
  history.value = http.history
})

function onOpenNode(node: CollectionNode) {
  wb.openFromNode(node)
}

function onSend() {
  const tab = wb.activeTab
  if (!tab) return
  wb.send(tab, (req) => {
    if (tab.nodeId) collections.saveRequest(tab.nodeId, req)
  })
}

function onLoadHistory(item: HttpCallRecord) {
  wb.openBlank('http')
  const tab = wb.activeTab
  if (!tab) return
  tab.request.method = item.method as typeof tab.request.method
  tab.request.url = item.url
  tab.request.headers = item.headers?.length ? JSON.parse(JSON.stringify(item.headers)) : [{ key: '', value: '', enabled: true }]
  tab.request.body_type = (item.body_type as typeof tab.request.body_type) || 'none'
  tab.request.body = item.body || ''
  tab.title = `${item.method} ${item.url}`
}

async function onClear() {
  await ElMessageBox.confirm('确定清空所有 HTTP 历史？', '确认', { type: 'warning' })
  await api.del('/api/http/history')
  await http.loadHistory()
  history.value = http.history
}

function statusClass(code: number) {
  if (!code) return ''
  if (code < 300) return 'ok'
  if (code < 400) return 'redirect'
  return 'err'
}
</script>

<style scoped>
.postman-view { display: flex; height: 100%; }
.sidebar {
  width: 280px; flex-shrink: 0; border-right: 1px solid var(--el-border-color);
  display: flex; flex-direction: column; background: #fff;
}
.side-divider { height: 1px; background: var(--el-border-color-lighter); }
.side-section { display: flex; flex-direction: column; min-height: 0; flex: 1; }
.section-header {
  display: flex; align-items: center; gap: 4px; padding: 6px 8px;
  font-weight: 600; font-size: 13px; cursor: pointer;
}
.history-list { flex: 1; overflow-y: auto; }
.history-item {
  display: flex; align-items: center; gap: 6px; padding: 4px 10px;
  cursor: pointer; font-size: 12px;
}
.history-item:hover { background: var(--el-fill-color-light); }
.history-item .m { font-weight: 700; width: 48px; }
.history-item .m.get { color: #49cc90; } .history-item .m.post { color: #fca130; }
.history-item .m.put { color: #61affe; } .history-item .m.delete { color: #f93e3e; }
.history-item .u { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.history-item .s.ok { color: var(--el-color-success); } .history-item .s.err { color: var(--el-color-danger); }

.workbench { flex: 1; display: flex; flex-direction: column; min-width: 0; background: #fff; }
.tab-bar {
  display: flex; align-items: center; gap: 2px; padding: 4px 8px 0;
  border-bottom: 1px solid var(--el-border-color); background: var(--el-bg-color-page);
}
.tab {
  display: flex; align-items: center; gap: 6px; padding: 4px 10px;
  border: 1px solid var(--el-border-color); border-bottom: none;
  border-radius: 6px 6px 0 0; cursor: pointer; font-size: 12px;
  background: #fff; max-width: 200px;
}
.tab.active { font-weight: 600; background: var(--el-color-primary-light-9); }
.tab-method { font-size: 10px; font-weight: 700; padding: 1px 4px; border-radius: 3px; color: #fff; }
.tab-method.get { background: #49cc90; } .tab-method.post { background: #fca130; }
.tab-method.put { background: #61affe; } .tab-method.delete { background: #f93e3e; }
.tab-method.patch { background: #50e3c2; } .tab-method.ws { background: #8e44ad; }
.tab-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tab-close { cursor: pointer; border-radius: 50%; }
.tab-close:hover { background: var(--el-fill-color-dark); }

.pane { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.half { display: flex; flex-direction: column; min-height: 0; }
.half.top { flex: 1; border-bottom: 1px solid var(--el-border-color); }
.half.bottom { flex: 1; }
.empty { flex: 1; display: flex; align-items: center; justify-content: center; }
</style>
