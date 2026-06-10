import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/Login.vue'),
    meta: { public: true, layout: 'blank' },
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppShell.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/pages/Dashboard.vue'),
        meta: { title: 'Tổng quan' },
      },
      {
        path: 'leads',
        name: 'leads',
        component: () => import('@/pages/leads/LeadsList.vue'),
        meta: { title: 'Khách tiềm năng' },
      },
      {
        path: 'leads/:id(\\d+)',
        name: 'lead-detail',
        component: () => import('@/pages/leads/LeadDetail.vue'),
        meta: { title: 'Chi tiết khách' },
      },
      {
        path: 'orders',
        name: 'orders',
        component: () => import('@/pages/orders/OrdersList.vue'),
        meta: { title: 'Đơn đăng ký' },
      },
      {
        path: 'orders/:id(\\d+)',
        name: 'order-detail',
        component: () => import('@/pages/orders/OrderDetail.vue'),
        meta: { title: 'Chi tiết đơn' },
      },
      {
        path: 'payments',
        name: 'payments',
        component: () => import('@/pages/PaymentsList.vue'),
        meta: { title: 'Thanh toán' },
      },
      {
        path: 'documents',
        name: 'documents',
        component: () => import('@/pages/DocumentsList.vue'),
        meta: { title: 'Hồ sơ học viên' },
      },
      {
        path: 'students',
        name: 'students',
        component: () => import('@/pages/StudentsList.vue'),
        meta: { title: 'Học viên' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/pages/NotFound.vue'),
    meta: { public: true, layout: 'blank' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(_to, _from, saved) {
    return saved ?? { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.initialized) await auth.bootstrap()

  if (to.meta.public) {
    // Đã login mà vào /login → bounce về dashboard
    if (to.name === 'login' && auth.isAuthenticated) {
      const next = typeof to.query.next === 'string' ? to.query.next : '/'
      return next.startsWith('/') ? next : '/'
    }
    return true
  }

  if (!auth.isAuthenticated) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  return true
})
