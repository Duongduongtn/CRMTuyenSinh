<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  House,
  UsersThree,
  ClipboardText,
  Wallet,
  FolderSimple,
  GraduationCap,
  ShieldCheck,
} from '@/lib/icons'
import { useAuthStore } from '@/stores/auth'
import { useSiteStore } from '@/stores/site'
import { ROLES } from '@/lib/roles'

const auth = useAuthStore()
const site = useSiteStore()
const route = useRoute()

interface NavItem {
  to: string
  label: string
  icon: typeof House
  groups?: string[] // null = ai cũng thấy
  badge?: string
}

const items = computed<NavItem[]>(() => [
  { to: '/', label: 'Tổng quan', icon: House },
  { to: '/leads', label: 'Khách tiềm năng', icon: UsersThree, groups: [ROLES.ADMIN, ROLES.SALE] },
  { to: '/orders', label: 'Đơn đăng ký', icon: ClipboardText, groups: [ROLES.ADMIN, ROLES.SALE, ROLES.ACCOUNTANT, ROLES.CLERK] },
  { to: '/payments', label: 'Thanh toán', icon: Wallet, groups: [ROLES.ADMIN, ROLES.ACCOUNTANT] },
  { to: '/documents', label: 'Hồ sơ', icon: FolderSimple, groups: [ROLES.ADMIN, ROLES.CLERK] },
  { to: '/students', label: 'Học viên', icon: GraduationCap, groups: [ROLES.ADMIN, ROLES.CLERK, ROLES.SALE] },
])

const visibleItems = computed(() =>
  items.value.filter((item) => {
    if (!item.groups) return true
    return auth.hasAnyGroup(item.groups)
  }),
)

function isActive(to: string): boolean {
  if (to === '/') return route.path === '/'
  return route.path === to || route.path.startsWith(to + '/')
}
</script>

<template>
  <aside
    class="hidden lg:flex w-64 shrink-0 flex-col border-r border-line-soft bg-paper sticky top-0 h-screen"
  >
    <!-- Brand -->
    <div class="flex h-16 items-center gap-3 border-b border-line-soft px-5">
      <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-ink text-paper">
        <ShieldCheck :size="18" weight="duotone" class="text-brand-300" />
      </div>
      <div class="min-w-0">
        <p class="text-[10px] uppercase tracking-wider text-ink-40 font-semibold">CRM nội bộ</p>
        <p class="text-sm font-semibold text-ink tracking-tight truncate">
          {{ site.settings?.brand_short_name || site.settings?.brand_name || 'CRM nội bộ' }}
        </p>
      </div>
    </div>

    <!-- Nav -->
    <nav class="flex-1 overflow-y-auto px-3 py-5" aria-label="Điều hướng chính">
      <p class="px-3 text-[10px] uppercase tracking-wider text-ink-40 font-semibold mb-2">Điều hướng</p>
      <ul class="space-y-0.5">
        <li v-for="item in visibleItems" :key="item.to">
          <RouterLink
            :to="item.to"
            :class="
              [
                'group flex items-center gap-3 rounded-md px-3 py-2 text-[13.5px] font-medium transition-colors duration-200',
                isActive(item.to)
                  ? 'bg-paper-tint text-brand-800'
                  : 'text-ink-60 hover:bg-paper-alt hover:text-ink',
              ]
            "
          >
            <component
              :is="item.icon"
              :size="18"
              :weight="isActive(item.to) ? 'duotone' : 'regular'"
              :class="isActive(item.to) ? 'text-brand-700' : 'text-ink-40 group-hover:text-ink-60'"
            />
            <span class="flex-1">{{ item.label }}</span>
            <span
              v-if="isActive(item.to)"
              class="h-1.5 w-1.5 rounded-full bg-brand-600"
              aria-hidden="true"
            />
          </RouterLink>
        </li>
      </ul>
    </nav>

    <!-- Footer mini -->
    <div class="border-t border-line-soft px-4 py-3 text-[11px] text-ink-40 leading-relaxed">
      <p>v0.1 · Sprint 3</p>
      <p>Nội bộ trung tâm tuyển sinh.</p>
    </div>
  </aside>
</template>
