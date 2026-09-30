<template>
  <a-modal
    :visible="visible"
    width="960px"
    :footer="false"
    :mask-closable="false"
    @cancel="onClose"
  >
    <template #title>
      <span>环境变量</span>
      <span v-if="collection" class="collection-tag">{{ collection.name }}</span>
    </template>

    <a-empty v-if="!collection" description="请先从某个集合打开请求，或在集合节点上点击齿轮图标" />

    <div v-else class="env-layout">
      <!-- 左：环境列表 -->
      <div class="env-list">
        <div class="env-list-header">
          <span class="env-list-title">ENVIRONMENTS</span>
          <a-button size="mini" @click="onAddEnv" title="新建环境">
            <template #icon><icon-plus /></template>
          </a-button>
        </div>
        <div
          v-for="e in localEnvs"
          :key="e.id"
          class="env-item"
          :class="{ active: e.id === activeId }"
          @click="activeId = e.id"
        >
          <span class="env-name" :title="e.name">{{ e.name }}</span>
          <icon-edit class="op" @click.stop="onRenameEnv(e)" />
          <icon-delete class="op danger" @click.stop="onRemoveEnv(e)" />
        </div>
        <a-empty v-if="!localEnvs.length" description="暂无环境" :image-size="50" />
      </div>

      <!-- 右：变量编辑 -->
      <div class="env-detail">
        <template v-if="currentEnv">
          <div class="detail-header">
            <span class="detail-title">{{ currentEnv.name }}</span>
            <a-button size="mini" @click="onAddVar">添加变量</a-button>
          </div>
          <table class="var-table">
            <thead>
              <tr>
                <th class="col-on"></th>
                <th class="col-name">Name</th>
                <th class="col-value">Value</th>
                <th class="col-desc">Description</th>
                <th class="col-op"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(v, i) in currentEnv.variables" :key="i">
                <td class="col-on">
                  <a-checkbox v-model="v.enabled" />
                </td>
                <td class="col-name">
                  <a-input v-model="v.key" placeholder="例如 knowledge_agent" size="small" />
                </td>
                <td class="col-value">
                  <a-input v-model="v.value" placeholder="例如 10.18.217.60:32706" size="small" />
                </td>
                <td class="col-desc">
                  <a-input v-model="v.description" placeholder="备注（可选）" size="small" />
                </td>
                <td class="col-op">
                  <a-button size="mini" type="text" status="danger" @click="currentEnv.variables.splice(i, 1)">
                    <template #icon><icon-delete /></template>
                  </a-button>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="hint">请求 URL / Header / Params / Body 中用 <code v-pre>{{变量名}}</code> 引用，发送时自动替换。</div>
        </template>
        <a-empty v-else description="选择左侧环境，或点击 + 新建环境" style="padding: 48px 0" />
      </div>
    </div>

    <div v-if="collection" class="dialog-footer">
      <a-button @click="onReset">重置</a-button>
      <a-button type="primary" @click="onSave">保存</a-button>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useEnvironmentsStore } from '@/stores/environments'
import { confirmDialog, promptInput, toast } from '@/utils/feedback'
import type { Environment } from '@/api/types'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [v: boolean] }>()

const envStore = useEnvironmentsStore()

const localEnvs = ref<Environment[]>([])
const activeId = ref<string | null>(null)

const collection = computed(() => envStore.targetCollection())

const currentEnv = computed(
  () => localEnvs.value.find((e) => e.id === activeId.value) ?? null,
)

watch(
  () => props.visible,
  (v) => {
    if (v) loadFromStore()
  },
)

function loadFromStore() {
  const c = envStore.targetCollection()
  localEnvs.value = c ? JSON.parse(JSON.stringify(c.environments ?? [])) : []
  activeId.value = c?.activeEnvId ?? localEnvs.value[0]?.id ?? null
}

async function onAddEnv() {
  const name = await promptInput('新建环境', 'local')
  if (!name) return
  const e: Environment = { id: envStore.envId(), name, variables: [] }
  localEnvs.value.push(e)
  activeId.value = e.id
}

async function onRenameEnv(e: Environment) {
  const name = await promptInput('重命名环境', e.name)
  if (!name) return
  e.name = name
}

async function onRemoveEnv(e: Environment) {
  const ok = await confirmDialog('删除环境', `确定删除环境「${e.name}」？`)
  if (!ok) return
  const idx = localEnvs.value.findIndex((x) => x.id === e.id)
  if (idx >= 0) localEnvs.value.splice(idx, 1)
  if (activeId.value === e.id) activeId.value = localEnvs.value[0]?.id ?? null
}

function onAddVar() {
  currentEnv.value?.variables.push({ key: '', value: '', enabled: true, description: '' })
}

async function onSave() {
  await envStore.replaceEnvs(localEnvs.value)
  toast.success('环境变量已保存')
  emit('update:visible', false)
}

function onReset() {
  loadFromStore()
}

function onClose() {
  emit('update:visible', false)
}
</script>

<style lang="less" scoped>
.collection-tag {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.env-layout {
  display: flex;
  gap: 12px;
  min-height: 360px;
}

.env-list {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid var(--el-border-color);
  padding-right: 12px;
}

.env-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.env-list-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
}

.env-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;

  &:hover { background: var(--el-fill-color-light); }
  &.active {
    background: var(--el-color-primary-light-9);
    font-weight: 600;
  }

  .env-name {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .op {
    visibility: hidden;
    cursor: pointer;
    color: var(--el-text-color-secondary);
    &:hover { color: var(--el-color-primary); }
    &.danger:hover { color: var(--el-color-danger); }
  }
  &:hover .op { visibility: visible; }
}

.env-detail {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.detail-title { font-weight: 600; }

.var-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th, td {
    border-bottom: 1px solid var(--el-border-color-lighter);
    padding: 4px 6px;
    text-align: left;
    font-weight: 500;
  }

  .col-on { width: 40px; }
  .col-name { width: 26%; }
  .col-value { width: 34%; }
  .col-desc { width: 26%; }
  .col-op { width: 40px; }
}

.hint {
  margin-top: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  code {
    background: var(--el-fill-color);
    padding: 1px 4px;
    border-radius: 3px;
  }
}

.dialog-footer {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
