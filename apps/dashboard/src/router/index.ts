import { createRouter, createWebHashHistory } from 'vue-router'
import DashboardView from '@/views/DashboardView.vue'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView
    },
    ...(import.meta.env.DEV ? [{
      path: '/workspace-spike',
      name: 'workspace-spike',
      component: () => import('@/views/WorkspaceSpikeView.vue'),
    }] : []),
  ],
})

export default router
