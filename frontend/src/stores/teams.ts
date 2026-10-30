/** 团队 store。 */
import { defineStore } from 'pinia'
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

  return { myTeams, members, loadMyTeams, createTeam, loadMembers, invite, removeMember }
})
