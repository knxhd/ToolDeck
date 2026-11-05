/** 团队 store。 */
import { acceptHMRUpdate, defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '@/api/client'

export interface Team {
  id: number
  name: string
  owner_id: number
  role: 'admin' | 'member'
}

export interface TeamMember {
  id: number
  username: string
  display_name: string
  role: string
}

export const useTeamsStore = defineStore('teams', () => {
  const myTeams = ref<Team[]>([])
  const members = ref<TeamMember[]>([])

  async function loadMyTeams() {
    myTeams.value = await api.get<Team[]>('/api/teams')
  }

  async function createTeam(name: string): Promise<Team> {
    const t = await api.post<Team>('/api/teams', { name })
    myTeams.value.push(t)
    return t
  }

  async function loadMembers(teamId: number) {
    members.value = await api.get<TeamMember[]>(`/api/teams/${teamId}/members`)
  }

  async function invite(teamId: number, username: string): Promise<TeamMember> {
    const m = await api.post<TeamMember>(`/api/teams/${teamId}/members`, { username })
    members.value.push(m)
    return m
  }

  async function removeMember(teamId: number, userId: number) {
    await api.del(`/api/teams/${teamId}/members/${userId}`)
    members.value = members.value.filter((m) => m.id !== userId)
  }

  /** 修改团队名称（管理员）。 */
  async function renameTeam(teamId: number, name: string): Promise<Team> {
    const res = await api.put<{ id: number; name: string; owner_id: number }>(`/api/teams/${teamId}`, { name })
    const t = myTeams.value.find((x) => x.id === teamId)
    if (t) t.name = res.name
    return t ?? { ...res, role: 'admin' }
  }

  /** 解散团队（创建者）。 */
  async function deleteTeam(teamId: number) {
    await api.del(`/api/teams/${teamId}`)
    myTeams.value = myTeams.value.filter((t) => t.id !== teamId)
    members.value = []
  }

  /** 成员退出团队。 */
  async function leaveTeam(teamId: number) {
    await api.post(`/api/teams/${teamId}/leave`)
    myTeams.value = myTeams.value.filter((t) => t.id !== teamId)
    members.value = []
  }

  function clear() {
    myTeams.value = []
    members.value = []
  }

  return {
    myTeams,
    members,
    loadMyTeams,
    createTeam,
    loadMembers,
    invite,
    removeMember,
    renameTeam,
    deleteTeam,
    leaveTeam,
    clear,
  }
})

if (import.meta.hot) import.meta.hot.accept(acceptHMRUpdate(useTeamsStore, import.meta.hot))
