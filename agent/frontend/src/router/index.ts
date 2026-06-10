import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/components/Layout.vue'
import Dashboard from '@/pages/Dashboard.vue'
import Chat from '@/pages/Chat.vue'
import History from '@/pages/History.vue'
import Settings from '@/pages/Settings.vue'
import PerformanceAnalysis from '@/pages/PerformanceAnalysis.vue'
import PerformanceReportDetail from '@/pages/PerformanceReportDetail.vue'

const routes = [
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: Dashboard,
        meta: { title: '集群概览', icon: 'Odometer' }
      },
      {
        path: 'chat',
        name: 'Chat',
        component: Chat,
        meta: { title: '智能对话', icon: 'ChatDotRound' }
      },
      {
        path: 'history',
        name: 'History',
        component: History,
        meta: { title: '历史记录', icon: 'Clock' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: Settings,
        meta: { title: '系统配置', icon: 'Setting' }
      },
      {
        path: 'performance-analysis',
        name: 'PerformanceAnalysis',
        component: PerformanceAnalysis,
        meta: { title: '业务性能分析', icon: 'DataAnalysis' }
      },
      {
        path: 'performance-analysis/:id',
        name: 'PerformanceReportDetail',
        component: PerformanceReportDetail,
        meta: { title: '报告详情', icon: 'Document' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
