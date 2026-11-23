import { createRouter, createWebHashHistory } from 'vue-router'
import WorkspaceView from '@/views/WorkspaceView.vue'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: WorkspaceView
    },
    ...(import.meta.env.DEV ? [{
      path: '/workspace-spike',
      name: 'workspace-spike',
      component: () => import('@/views/WorkspaceSpikeView.vue'),
    }] : []),
  ],
})

export default router
