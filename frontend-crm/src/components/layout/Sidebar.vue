<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  House,
  UsersThree,
  ClipboardText,
  Wallet,
  FolderSimple,
  GraduationCap,
  ChartBar,
  X,
} from '@/lib/icons'
import { useAuthStore } from '@/stores/auth'
import { ROLES } from '@/lib/roles'
import { useMobileNav } from '@/composables/useMobileNav'
import BrandTile from '@/components/BrandTile.vue'

const auth = useAuthStore()
const route = useRoute()
const { open: navOpen, close: closeNav } = useMobileNav()

// Auto đóng drawer khi đổi route, tránh user kẹt trong nav sau khi click link.
watch(() => route.fullPath, () => closeNav())

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && navOpen.value) closeNav()
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

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
  { to: '/reports', label: 'Báo cáo', icon: ChartBar, groups: [ROLES.ADMIN, ROLES.ACCOUNTANT] },
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
  <!-- Backdrop chỉ hiện khi drawer mở trên mobile, click ngoài để đóng. -->
  <Transition
    enter-active-class="transition-opacity duration-200 ease-out"
    leave-active-class="transition-opacity duration-200 ease-in"
    enter-from-class="opacity-0"
    leave-to-class="opacity-0"
  >
    <div
      v-if="navOpen"
      class="fixed inset-0 z-30 bg-ink/40 backdrop-blur-[2px] lg:hidden"
      aria-hidden="true"
      @click="closeNav"
    />
  </Transition>

  <aside
    :class="
      [
        'flex w-64 shrink-0 flex-col border-r border-line-soft bg-paper h-screen',
        'lg:sticky lg:top-0 lg:translate-x-0',
        'fixed inset-y-0 left-0 z-40 transition-transform duration-300 ease-out-expo lg:transition-none',
        navOpen ? 'translate-x-0 shadow-[0_18px_36px_-12px_rgba(15,31,26,0.18)]' : '-translate-x-full lg:translate-x-0 lg:shadow-none',
      ]
    "
    role="navigation"
    aria-label="Điều hướng chính"
  >
    <!-- Brand -->
    <div class="flex h-16 items-center gap-3 border-b border-line-soft px-5">
      <BrandTile class="flex-1 min-w-0" variant="paper" size="sm" caption="CRM nội bộ" fallback="CRM nội bộ" />
      <button
        type="button"
        class="lg:hidden flex h-9 w-9 items-center justify-center rounded-md text-ink-40 hover:bg-paper-alt hover:text-ink transition-colors"
        aria-label="Đóng menu"
        @click="closeNav"
      >
        <X :size="18" />
      </button>
    </div>

    <!-- Nav -->
    <nav class="flex-1 overflow-y-auto px-3 py-5">
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
