<template>
  <a-modal :visible="true" :footer="false" :closable="true" @cancel="emit('close')" width="560">
    <template #title>团队管理</template>

    <a-tabs v-model:active-key="activeTab">
      <a-tab-pane key="list" title="我的团队">
        <div v-if="!teams.myTeams.length" style="padding: 12px 0; color: var(--color-text-3); font-size: 13px">
          还没有团队，创建一个吧。
        </div>
        <div v-for="t in teams.myTeams" :key="t.id" class="team-row">
          <div class="team-info" @click="selectTeam(t)">
            <div class="team-name">{{ t.name }}</div>
            <div class="team-meta">{{ t.role === 'admin' ? '管理员' : '成员' }}</div>
          </div>
          <a-button size="mini" @click="selectTeam(t)">成员</a-button>
        </div>
        <a-divide style="margin: 12px 0" />
        <a-input-search
          v-model="newTeamName"
          placeholder="新团队名称"
          search-button="创建团队"
          @search="onCreateTeam"
        />
      </a-tab-pane>

      <a-tab-pane v-for="t in teams.myTeams" :key="String(t.id)" :title="t.name">
        <div style="margin-bottom: 12px">
          <a-input-search
            v-model="inviteName"
            placeholder="输入用户名邀请加入"
            search-button="邀请"
            @search="onInvite"
          />
        </div>
        <div v-if="!teams.members.length" style="color: var(--color-text-3); font-size: 13px">
          暂无成员
        </div>
        <div v-for="m in teams.members" :key="m.id" class="member-row">
          <div>
            <div style="font-weight: 500">{{ m.display_name || m.username }}</div>
            <div style="font-size: 12px; color: var(--color-text-3)">@{{ m.username }} · {{ m.role }}</div>
          </div>
          <a-button v-if="m.role !== 'admin'" size="mini" status="danger" @click="onRemove(m)">移除</a-button>
        </div>
      </a-tab-pane>
    </a-tabs>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'

import { useTeamsStore, type Team } from '@/stores/teams'

const emit = defineEmits<{ (e: 'close'): void; (e: 'select-team', team: Team): void }>()

const teams = useTeamsStore()
const activeTab = ref('list')
const newTeamName = ref('')
const inviteName = ref('')
const currentTeam = ref<Team | null>(null)

// 直接点击团队 tab 时，加载成员列表
watch(activeTab, async (key) => {
  if (key === 'list') {
    currentTeam.value = null
    return
  }
  const tid = Number(key)
  const t = teams.myTeams.find((x) => x.id === tid)
  if (t && currentTeam.value?.id !== tid) {
    currentTeam.value = t
    await teams.loadMembers(tid)
  }
})

async function onCreateTeam(name: string) {
  const n = name.trim()
  if (!n) return
  try {
    const t = await teams.createTeam(n)
    Message.success(`团队「${t.name}」已创建`)
    newTeamName.value = ''
  } catch (err: any) {
    Message.error(err.message || '创建失败')
  }
}

async function selectTeam(t: Team) {
  currentTeam.value = t
  activeTab.value = String(t.id)
  await teams.loadMembers(t.id)
}

async function onInvite(username: string) {
  const u = username.trim()
  if (!u || !currentTeam.value) return
  try {
    await teams.invite(currentTeam.value.id, u)
    Message.success(`已邀请 ${u}`)
    inviteName.value = ''
  } catch (err: any) {
    Message.error(err.message || '邀请失败')
  }
}

async function onRemove(m: { id: number; username: string }) {
  if (!currentTeam.value) return
  try {
    await teams.removeMember(currentTeam.value.id, m.id)
    Message.success(`已移除 ${m.username}`)
  } catch (err: any) {
    Message.error(err.message || '移除失败')
  }
}
</script>

<style scoped>
.team-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 4px;
  border-bottom: 1px solid var(--color-border-2);
}
.team-info {
  cursor: pointer;
}
.team-name {
  font-weight: 500;
}
.team-meta {
  font-size: 12px;
  color: var(--color-text-3);
}
.member-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 4px;
  border-bottom: 1px solid var(--color-border-2);
}
</style>
