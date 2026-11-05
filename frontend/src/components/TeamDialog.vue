<template>
  <a-modal
    :visible="true"
    :footer="false"
    :closable="true"
    width="560px"
    modal-class="team-dialog"
    @cancel="emit('close')"
  >
    <template #title>团队管理</template>

    <!-- 顶部：团队下拉 + 新建 -->
    <div class="team-toolbar">
      <a-select
        v-if="teams.myTeams.length"
        v-model="selectedId"
        class="team-select"
        placeholder="选择团队"
        :allow-search="teams.myTeams.length > 6"
      >
        <template #prefix><icon-user-group /></template>
        <a-option v-for="t in teams.myTeams" :key="t.id" :value="t.id" :label="t.name">
          <span class="ui-menu-item ui-scope-opt">
            <icon-user-group />
            <span class="ui-scope-name" :title="t.name">{{ t.name }}</span>
            <span v-if="t.owner_id === myId" class="ui-scope-role">创建者</span>
            <span v-else-if="t.role === 'admin'" class="ui-scope-role">管理员</span>
          </span>
        </a-option>
      </a-select>
      <a-button
        v-if="!creating"
        :type="teams.myTeams.length ? 'secondary' : 'primary'"
        class="create-btn"
        @click="startCreate"
      >
        <template #icon><icon-plus /></template>
        新建团队
      </a-button>
    </div>

    <!-- 新建团队（内联） -->
    <div v-if="creating" class="inline-form">
      <a-input
        ref="createInputRef"
        v-model="newTeamName"
        placeholder="团队名称，2-32 位中英文 / 数字 / _ -"
        :max-length="32"
        allow-clear
        @press-enter="onCreateTeam"
        @keydown.esc="cancelCreate"
      />
      <a-button type="primary" :loading="busy" @click="onCreateTeam">创建</a-button>
      <a-button @click="cancelCreate">取消</a-button>
    </div>

    <!-- 空状态 -->
    <div v-if="!teams.myTeams.length && !creating" class="empty">
      <icon-user-group class="empty-ico" />
      <div class="empty-title">还没有团队</div>
      <div class="empty-desc">创建团队后可邀请成员，共享同一份集合与环境</div>
    </div>

    <template v-if="current">
      <!-- 团队信息卡 -->
      <div class="team-card">
        <span class="team-avatar">{{ current.name.charAt(0).toUpperCase() }}</span>

        <div class="team-main">
          <template v-if="editing">
            <div class="edit-row">
              <a-input
                ref="editInputRef"
                v-model="editName"
                size="small"
                :max-length="32"
                @press-enter="onRename"
                @keydown.esc="cancelEdit"
              />
              <a-button size="small" type="primary" :loading="busy" @click="onRename">保存</a-button>
              <a-button size="small" @click="cancelEdit">取消</a-button>
            </div>
          </template>
          <template v-else>
            <div class="team-name-row">
              <span class="team-name" :title="current.name">{{ current.name }}</span>
              <span class="role-tag" :class="isOwner ? 'owner' : current.role">
                {{ isOwner ? '创建者' : current.role === 'admin' ? '管理员' : '成员' }}
              </span>
            </div>
            <div class="team-meta">{{ teams.members.length }} 名成员</div>
          </template>
        </div>

        <div v-if="!editing" class="team-actions">
          <a-tooltip v-if="isAdmin" content="编辑团队名称" mini>
            <a-button size="small" class="icon-btn" @click="startEdit">
              <template #icon><icon-edit /></template>
            </a-button>
          </a-tooltip>
          <a-dropdown trigger="click" position="br" @select="onMore">
            <a-button size="small" class="icon-btn">
              <template #icon><icon-more /></template>
            </a-button>
            <template #content>
              <a-doption value="enter">
                <span class="ui-menu-item"><icon-swap /> 切换到该团队空间</span>
              </a-doption>
              <a-doption v-if="isOwner" value="delete" class="ui-danger-option">
                <span class="ui-menu-item"><icon-delete /> 解散团队</span>
              </a-doption>
              <a-doption v-else value="leave" class="ui-danger-option">
                <span class="ui-menu-item"><icon-export /> 退出团队</span>
              </a-doption>
            </template>
          </a-dropdown>
        </div>
      </div>

      <!-- 成员 -->
      <div class="section-title">
        <span>成员</span>
        <span class="count">{{ teams.members.length }}</span>
      </div>

      <div v-if="isAdmin" class="inline-form invite-form">
        <a-input
          v-model="inviteName"
          placeholder="输入用户名邀请加入"
          allow-clear
          @press-enter="onInvite"
        >
          <template #prefix><icon-user-add /></template>
        </a-input>
        <a-button type="primary" :loading="busy" @click="onInvite">邀请</a-button>
      </div>

      <a-spin :loading="loadingMembers" class="member-spin">
        <div class="member-list">
          <div v-if="!teams.members.length && !loadingMembers" class="member-empty">暂无成员</div>
          <div v-for="m in teams.members" :key="m.id" class="member-row">
            <span class="member-avatar">{{ (m.display_name || m.username).charAt(0).toUpperCase() }}</span>
            <div class="member-info">
              <div class="member-name">
                {{ m.display_name || m.username }}
                <span v-if="m.id === myId" class="me">（我）</span>
              </div>
              <div class="member-sub">@{{ m.username }}</div>
            </div>
            <span class="role-tag" :class="m.id === current.owner_id ? 'owner' : m.role">
              {{ m.id === current.owner_id ? '创建者' : m.role === 'admin' ? '管理员' : '成员' }}
            </span>
            <a-popconfirm
              v-if="isAdmin && m.role !== 'admin'"
              :content="`确定将 ${m.display_name || m.username} 移出团队？`"
              type="warning"
              @ok="onRemove(m)"
            >
              <a-button size="mini" type="text" status="danger" class="remove-btn">移除</a-button>
            </a-popconfirm>
          </div>
        </div>
      </a-spin>
    </template>
  </a-modal>

  <!-- 解散团队二次确认：需输入团队名 -->
  <a-modal
    v-model:visible="deleteOpen"
    title="解散团队"
    width="420px"
    :ok-button-props="{ status: 'danger', disabled: deleteConfirmText.trim() !== current?.name, loading: busy }"
    ok-text="解散团队"
    :on-before-ok="onDeleteTeam"
    unmount-on-close
  >
    <div class="danger-tip">
      <icon-exclamation-circle-fill />
      <div>
        解散后，团队「<b>{{ current?.name }}</b>」下的<b>全部集合、环境与成员关系</b>将被永久删除，且无法恢复。
      </div>
    </div>
    <div class="confirm-label">请输入团队名称以确认：</div>
    <a-input v-model="deleteConfirmText" :placeholder="current?.name" />
  </a-modal>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import { useTeamsStore, type Team } from '@/stores/teams'
import { useUserStore } from '@/stores/user'
import { confirmDialog, toast } from '@/utils/feedback'

const props = defineProps<{ activeTeamId?: number | null }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select-team', team: Team): void
  (e: 'team-removed', teamId: number): void
}>()

const teams = useTeamsStore()
const user = useUserStore()

const myId = computed(() => user.user?.id ?? -1)

const selectedId = ref<number | undefined>(undefined)
const current = computed<Team | null>(() => teams.myTeams.find((t) => t.id === selectedId.value) ?? null)
const isOwner = computed(() => !!current.value && current.value.owner_id === myId.value)
const isAdmin = computed(() => !!current.value && (isOwner.value || current.value.role === 'admin'))

const busy = ref(false)
const loadingMembers = ref(false)

// —— 新建 ——
const creating = ref(false)
const newTeamName = ref('')
const createInputRef = ref<{ focus: () => void } | null>(null)

// —— 编辑 ——
const editing = ref(false)
const editName = ref('')
const editInputRef = ref<{ focus: () => void } | null>(null)

// —— 邀请 / 解散 ——
const inviteName = ref('')
const deleteOpen = ref(false)
const deleteConfirmText = ref('')

onMounted(() => {
  const preferred = props.activeTeamId
  selectedId.value =
    teams.myTeams.find((t) => t.id === preferred)?.id ?? teams.myTeams[0]?.id
})

// 切换团队：退出编辑态并加载成员
watch(selectedId, async (id) => {
  editing.value = false
  inviteName.value = ''
  if (id == null) {
    teams.members = []
    return
  }
  loadingMembers.value = true
  try {
    await teams.loadMembers(id)
  } catch (err) {
    toast.error((err as Error).message || '成员加载失败')
  } finally {
    loadingMembers.value = false
  }
})

function startCreate() {
  creating.value = true
  newTeamName.value = ''
  void nextTick(() => createInputRef.value?.focus())
}

function cancelCreate() {
  creating.value = false
  newTeamName.value = ''
}

async function onCreateTeam() {
  const n = newTeamName.value.trim()
  if (!n) return
  busy.value = true
  try {
    const t = await teams.createTeam(n)
    toast.success(`团队「${t.name}」已创建`)
    cancelCreate()
    selectedId.value = t.id
  } catch (err) {
    toast.error((err as Error).message || '创建失败')
  } finally {
    busy.value = false
  }
}

function startEdit() {
  if (!current.value) return
  editName.value = current.value.name
  editing.value = true
  void nextTick(() => editInputRef.value?.focus())
}

function cancelEdit() {
  editing.value = false
}

async function onRename() {
  const t = current.value
  const n = editName.value.trim()
  if (!t || !n) return
  if (n === t.name) {
    editing.value = false
    return
  }
  busy.value = true
  try {
    await teams.renameTeam(t.id, n)
    toast.success('团队名称已更新')
    editing.value = false
  } catch (err) {
    toast.error((err as Error).message || '修改失败')
  } finally {
    busy.value = false
  }
}

async function onMore(v: string | number | Record<string, unknown> | undefined) {
  const t = current.value
  if (!t) return
  if (v === 'enter') {
    emit('select-team', t)
  } else if (v === 'delete') {
    deleteConfirmText.value = ''
    deleteOpen.value = true
  } else if (v === 'leave') {
    const ok = await confirmDialog('退出团队', `确定退出团队「${t.name}」？退出后将无法访问该团队的集合。`)
    if (!ok) return
    try {
      await teams.leaveTeam(t.id)
      toast.success(`已退出团队「${t.name}」`)
      afterRemoved(t.id)
    } catch (err) {
      toast.error((err as Error).message || '退出失败')
    }
  }
}

async function onDeleteTeam(): Promise<boolean> {
  const t = current.value
  if (!t || deleteConfirmText.value.trim() !== t.name) return false
  busy.value = true
  try {
    await teams.deleteTeam(t.id)
    toast.success(`团队「${t.name}」已解散`)
    afterRemoved(t.id)
    return true
  } catch (err) {
    toast.error((err as Error).message || '解散失败')
    return false
  } finally {
    busy.value = false
  }
}

/** 团队被解散 / 退出后：选中剩余第一个团队，并通知父组件。 */
function afterRemoved(teamId: number) {
  selectedId.value = teams.myTeams[0]?.id
  emit('team-removed', teamId)
}

async function onInvite() {
  const u = inviteName.value.trim()
  if (!u || !current.value) return
  busy.value = true
  try {
    await teams.invite(current.value.id, u)
    toast.success(`已邀请 ${u}`)
    inviteName.value = ''
  } catch (err) {
    toast.error((err as Error).message || '邀请失败')
  } finally {
    busy.value = false
  }
}

async function onRemove(m: { id: number; username: string }) {
  if (!current.value) return
  try {
    await teams.removeMember(current.value.id, m.id)
    toast.success(`已移除 ${m.username}`)
  } catch (err) {
    toast.error((err as Error).message || '移除失败')
  }
}
</script>

<style scoped lang="less">
.team-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;

  .team-select {
    flex: 1;
    min-width: 0;

    :deep(.arco-select-view-prefix) {
      padding-right: 6px;
      color: rgb(var(--primary-6));
    }

    :deep(.arco-select-view-value) {
      font-weight: 600;
    }
  }

  .create-btn {
    flex-shrink: 0;
  }
}

.inline-form {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;

  :deep(.arco-input-wrapper) {
    flex: 1;
  }
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28px 0 16px;
  color: var(--color-text-3);

  .empty-ico {
    font-size: 2.14em;
    color: var(--color-text-4);
  }

  .empty-title {
    margin-top: 10px;
    font-size: 0.93em;
    font-weight: 600;
    color: var(--color-text-2);
  }

  .empty-desc {
    margin-top: 4px;
    font-size: 0.86em;
  }
}

.team-card {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 12px 12px 12px 14px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-bg-subtle);
}

.team-avatar,
.member-avatar {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(var(--primary-6), 0.14);
  color: rgb(var(--primary-6));
  font-weight: 700;
}

.team-avatar {
  width: 38px;
  height: 38px;
  font-size: 1.14em;
}

.team-main {
  flex: 1;
  min-width: 0;
}

.team-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.team-name {
  overflow: hidden;
  font-size: 1em;
  font-weight: 600;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: var(--color-text-1);
}

.team-meta {
  margin-top: 3px;
  font-size: 0.86em;
  color: var(--color-text-3);
}

.edit-row {
  display: flex;
  align-items: center;
  gap: 6px;

  :deep(.arco-input-wrapper) {
    flex: 1;
  }
}

.team-actions {
  display: flex;
  flex-shrink: 0;
  gap: 4px;

  .icon-btn {
    width: 28px;
    padding: 0;
  }
}

.role-tag {
  flex-shrink: 0;
  padding: 0 7px;
  border-radius: 9px;
  font-size: 0.79em;
  line-height: 18px;
  background: var(--color-fill-2);
  color: var(--color-text-3);

  &.owner {
    background: rgba(var(--primary-6), 0.14);
    color: rgb(var(--primary-6));
  }

  &.admin {
    background: rgba(var(--arcoblue-6), 0.12);
    color: rgb(var(--arcoblue-6));
  }
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 16px 0 2px;
  font-size: 0.86em;
  font-weight: 600;
  color: var(--color-text-2);

  .count {
    padding: 0 6px;
    border-radius: 8px;
    background: var(--color-fill-2);
    color: var(--color-text-3);
    font-size: 0.79em;
    font-weight: 500;
    line-height: 16px;
  }
}

.invite-form {
  margin-top: 8px;
}

.member-spin {
  display: block;
  width: 100%;
}

.member-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 300px;
  margin-top: 10px;
  overflow-y: auto;
}

.member-empty {
  padding: 16px 0;
  text-align: center;
  font-size: 12.5px;
  color: var(--color-text-3);
}

.member-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: var(--ui-radius-sm);
  transition: background-color 0.12s ease;

  &:hover {
    background: var(--ui-bg-hover);

    .remove-btn {
      opacity: 1;
    }
  }
}

.member-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 0.86em;
}

.member-info {
  flex: 1;
  min-width: 0;
}

.member-name {
  overflow: hidden;
  font-size: 0.93em;
  font-weight: 500;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: var(--color-text-1);

  .me {
    font-weight: 400;
    color: var(--color-text-4);
  }
}

.member-sub {
  margin-top: 1px;
  font-size: 11.5px;
  color: var(--color-text-4);
}

.remove-btn {
  opacity: 0;
  transition: opacity 0.12s ease;
}

.danger-tip {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--ui-radius-sm);
  background: rgba(var(--danger-6), 0.08);
  color: var(--color-text-2);
  font-size: 12.5px;
  line-height: 1.6;

  .arco-icon {
    flex-shrink: 0;
    margin-top: 3px;
    color: rgb(var(--danger-6));
    font-size: 1.07em;
  }
}

.confirm-label {
  margin: 14px 0 6px;
  font-size: 12.5px;
  color: var(--color-text-2);
}
</style>
