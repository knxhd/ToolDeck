import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import MainLayout from '@/layouts/MainLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/http',
    children: [
      {
        path: 'http',
        name: 'http',
        component: () => import('@/views/HttpWorkbench.vue'),
      },
      {
        path: 'mcp',
        name: 'mcp',
        component: () => import('@/views/McpClient.vue'),
      },
      {
        path: 'llm',
        name: 'llm',
        component: () => import('@/views/LlmPlayground.vue'),
      },
      {
        path: 'history',
        name: 'history',
        component: () => import('@/views/HistoryView.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
