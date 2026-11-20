<template>
  <a-modal
    :visible="visible"
    width="1180px"
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
          <a-button size="mini" type="text" @click="onAddEnv" title="新建环境">
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
            <span class="detail-tip">在最后一行输入即可新增变量</span>
          </div>
          <div class="var-scroll">
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
                  <a-input v-model="v.key" placeholder="占位符" size="small" />
                </td>
                <td class="col-value">
                  <a-tooltip :content="v.value" position="top" :disabled="!v.value || v.value.length < 24">
                    <a-input v-model="v.value" placeholder="占位值" size="small" />
                  </a-tooltip>
                </td>
                <td class="col-desc">
                  <a-input v-model="v.description" placeholder="备注" size="small" />
                </td>
                <td class="col-op">
                  <a-button v-if="!(isBlankRow(v) && i === currentEnv.variables.length - 1)" size="mini" type="text"
                    status="danger" @click="removeRow(i)">
                    <template #icon><icon-delete /></template>
                  </a-button>
                </td>
              </tr>
            </tbody>
            </table>
          </div>
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
  // 优先选中当前生效的环境；没有（或未设置）时默认选中第一个
  activeId.value =
    localEnvs.value.find((e) => e.id === c?.activeEnvId)?.id ?? localEnvs.value[0]?.id ?? null
  // 每个环境末尾都留一个空行
  localEnvs.value.forEach((e) => ensureTail(e))
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

/** 完全空白的一行（Name / Value / Description 都没填）。 */
function isBlankRow(v: Environment['variables'][number]): boolean {
  return !(v.key || '').trim() && !(v.value || '').trim() && !(v.description || '').trim()
}

/** 保证变量列表末尾始终有一个空行：填完最后一行后自动补一个新空行。 */
function ensureTail(env: Environment | null) {
  if (!env) return
  const last = env.variables[env.variables.length - 1]
  if (!last || !isBlankRow(last)) {
    env.variables.push({ key: '', value: '', enabled: true, description: '' })
  }
}

/** 删除一行；删到只剩空行时补回一个空行，表格不会变成空表。 */
function removeRow(i: number) {
  const env = currentEnv.value
  if (!env) return
  env.variables.splice(i, 1)
  ensureTail(env)
}

// 末尾空行一旦被填上内容，立刻补一个新空行（任何字段输入都算）
watch(
  () => currentEnv.value?.variables.map((v) => `${v.key}|${v.value}|${v.description}`).join('\n') ?? '',
  () => ensureTail(currentEnv.value),
)

async function onSave() {
  // 末尾（以及被清空的）空白行不落库
  const cleaned = localEnvs.value.map((e) => ({
    ...e,
    variables: e.variables.filter((v) => !isBlankRow(v)),
  }))
  await envStore.replaceEnvs(cleaned)
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
  display: inline-block;
  margin-left: 8px;
  padding: 1px 8px;
  border: 1px solid var(--ui-border);
  border-radius: 10px;
  background: var(--ui-bg-subtle);
  color: var(--color-text-3);
  font-size: 0.79em;
  font-weight: 500;
  vertical-align: middle;
}

.env-layout {
  display: flex;
  gap: 12px;
  min-height: 380px;
}

.env-list {
  width: 208px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 6px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);
}

.env-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 26px;
  padding: 0 2px 4px 6px;

  :deep(.arco-btn) {
    width: 22px;
    height: 22px;
    padding: 0;
    border-radius: var(--ui-radius-sm);
    color: var(--color-text-3);

    &:hover {
      background: var(--ui-bg-hover);
      color: rgb(var(--primary-6));
    }
  }
}

.env-list-title {
  font-family: var(--ui-font-mono);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--color-text-4);
}

.env-item {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 28px;
  padding: 3px 8px;
  border-radius: var(--ui-radius-sm);
  cursor: pointer;
  font-size: 12.5px;
  color: var(--color-text-2);
  transition: background-color 0.12s ease, color 0.12s ease;

  &:hover {
    background: var(--ui-bg-hover);

    .op {
      visibility: visible;
    }
  }

  &.active {
    background: var(--ui-bg-panel);
    box-shadow: var(--ui-shadow-1);
    color: rgb(var(--primary-6));
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
    flex-shrink: 0;
    cursor: pointer;
    font-size: 0.86em;
    color: var(--color-text-4);
    transition: color 0.12s ease;

    &:hover {
      color: rgb(var(--primary-6));
    }

    &.danger:hover {
      color: var(--ui-accent-danger);
    }
  }
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
  margin-bottom: 10px;
}

.detail-title {
  font-size: 0.93em;
  font-weight: 600;
  color: var(--color-text-1);
}

.detail-tip {
  font-size: 11.5px;
  color: var(--color-text-3);
}

.var-table {
  width: 100%;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
  overflow: hidden;
  font-size: 0.86em;

  th {
    position: sticky;
    top: 0;
    z-index: 1;
    height: 28px;
    padding: 0 8px;
    border-bottom: 1px solid var(--ui-border);
    background: var(--ui-bg-subtle);
    font-family: var(--ui-font-mono);
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-3);
    text-align: left;
  }

  td {
    padding: 3px 8px;
    border-bottom: 1px solid var(--ui-border-soft);
    text-align: left;
  }

  tr:last-child td {
    border-bottom: none;
  }

  tbody tr:hover td {
    background: var(--ui-bg-hover);
  }



  /* 行内输入默认熔入表格 */
  :deep(.arco-input-wrapper) {
    background: transparent;
    border-color: transparent;
    border-radius: var(--ui-radius-sm);
    font-family: var(--ui-font-mono);
    font-size: 0.86em;

    &:hover {
      background: var(--ui-bg-panel);
      border-color: var(--ui-border);
    }
  }

  .col-on {
    width: 44px;
  }
  .col-name {
    width: 240px;
  }
  .col-value {
    width: auto;
  }
  .col-desc {
    width: 220px;
  }
  .col-op {
    width: 44px;
    text-align: center;

    :deep(.arco-btn) {
      width: 22px;
      height: 22px;
      padding: 0;
      border-radius: var(--ui-radius-sm);
      opacity: 0.55;

      &:hover {
        opacity: 1;
      }
    }
  }
}

.var-scroll {
  max-height: 58vh;
  overflow-y: auto;
  border-radius: var(--ui-radius-md);
}

.hint {
  margin-top: 12px;
  padding: 8px 10px;
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);
  color: var(--color-text-3);
  font-size: 11.5px;
  line-height: 1.7;

  code {
    padding: 1px 5px;
    border-radius: var(--ui-radius-sm);
    background: rgba(var(--primary-6), 0.12);
    color: rgb(var(--primary-6));
    font-family: var(--ui-font-mono);
    font-size: 0.79em;
  }
}

.dialog-footer {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
