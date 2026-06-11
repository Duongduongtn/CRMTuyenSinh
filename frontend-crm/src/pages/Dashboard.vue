<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import {
  UsersThree,
  ClipboardText,
  Wallet,
  FolderSimple,
  CaretRight,
  TrendUp,
  ArrowRight,
} from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Spinner from '@/components/ui/Spinner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { fetchLeads } from '@/api/leads'
import { fetchEnrollments } from '@/api/orders'
import { fetchPayments } from '@/api/payments'
import { formatVND, formatNumber, timeAgo, formatPhone, NO_VALUE } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const recentLeads = useQuery({
  queryKey: ['dashboard', 'leads', 'recent'],
  queryFn: () => fetchLeads({ page_size: 5, ordering: '-created_at' }),
})

const recentOrders = useQuery({
  queryKey: ['dashboard', 'orders', 'recent'],
  queryFn: () => fetchEnrollments({ page: 1, ordering: '-created_at' }),
})

const recentPayments = useQuery({
  queryKey: ['dashboard', 'payments', 'recent'],
  queryFn: () => fetchPayments({ page: 1, ordering: '-created_at' }),
})

const stats = computed(() => {
  const leadsCount = recentLeads.data.value?.count ?? 0
  const ordersCount = recentOrders.data.value?.count ?? 0
  const paymentsRows = recentPayments.data.value?.results ?? []
  const confirmedTotal = paymentsRows
    .filter((p) => p.status === 'confirmed')
    .reduce((acc, p) => acc + Number(p.amount), 0)
  const pendingDocs = (recentOrders.data.value?.results ?? []).filter(
    (o) => o.status === 'pending_deposit' || o.status === 'deposit_paid',
  ).length

  return [
    {
      label: 'Khách tiềm năng',
      hint: 'Tổng số lead trong hệ thống',
      value: formatNumber(leadsCount),
      icon: UsersThree,
      tone: 'brand',
      to: '/leads',
      span: 'lg:col-span-3',
    },
    {
      label: 'Đơn đăng ký',
      hint: 'Tổng số đơn',
      value: formatNumber(ordersCount),
      icon: ClipboardText,
      tone: 'info',
      to: '/orders',
      span: 'lg:col-span-3',
    },
    {
      label: 'Hồ sơ chờ xử lý',
      hint: 'Đơn còn trong giai đoạn cọc / cọc 1 phần',
      value: formatNumber(pendingDocs),
      icon: FolderSimple,
      tone: 'warning',
      to: '/documents',
      span: 'lg:col-span-2',
    },
    {
      label: 'Doanh thu xác nhận',
      hint: 'Tổng tiền payment đã xác nhận gần đây',
      value: formatVND(confirmedTotal),
      icon: Wallet,
      tone: 'success',
      to: '/payments',
      span: 'lg:col-span-4',
    },
  ]
})

function toneClasses(tone: string): string {
  const map: Record<string, string> = {
    brand: 'bg-paper-tint text-brand-700 border-brand-100',
    info: 'bg-info-soft text-info border-info/20',
    success: 'bg-success-soft text-success border-success/20',
    warning: 'bg-warning-soft text-warning border-warning/20',
  }
  return map[tone] ?? 'bg-paper-alt text-ink-60 border-line-soft'
}
</script>

<template>
  <div class="space-y-10">
    <!-- Greeting -->
    <section class="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-[12px] uppercase tracking-wider text-brand-700 font-semibold">Hôm nay</p>
        <h2 class="text-3xl font-semibold tracking-tighter text-ink mt-1">
          Chào {{ auth.user?.display_name?.split(' ').pop() || auth.user?.username }}
        </h2>
        <p class="text-[14px] text-ink-60 mt-1">
          {{ auth.user?.role_labels.join(' · ') }}. Đây là tình hình hôm nay.
        </p>
      </div>
      <div class="flex items-center gap-2 text-[12px] text-ink-60">
        <TrendUp :size="14" class="text-brand-600" />
        <span>Cập nhật theo thời gian thực qua /api/admin/*</span>
      </div>
    </section>

    <!-- Stats bento 12-col: 3 / 3 / 2 / 4 (lead, đơn, hồ sơ, doanh thu) -->
    <section class="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-12">
      <RouterLink
        v-for="stat in stats"
        :key="stat.label"
        :to="stat.to"
        :class="['group', stat.span]"
      >
        <Card interactive class="h-full">
          <div class="flex items-start justify-between gap-3">
            <div :class="['flex h-10 w-10 items-center justify-center rounded-lg border', toneClasses(stat.tone)]">
              <component :is="stat.icon" :size="20" weight="duotone" />
            </div>
            <CaretRight
              :size="14"
              class="text-ink-20 group-hover:text-brand-600 group-hover:translate-x-0.5 transition-all"
            />
          </div>
          <div class="mt-4 space-y-1">
            <p class="text-[12px] text-ink-60 font-medium">{{ stat.label }}</p>
            <p class="text-[26px] font-semibold tracking-tighter text-ink tabular-nums">{{ stat.value }}</p>
            <p class="text-[11px] text-ink-40">{{ stat.hint }}</p>
          </div>
        </Card>
      </RouterLink>
    </section>

    <!-- Recent lists 2 cột -->
    <section class="grid gap-4 lg:grid-cols-5">
      <!-- Recent leads 3/5 -->
      <Card class="lg:col-span-3" :padded="false">
        <div class="flex items-center justify-between px-6 py-5 border-b border-line-soft">
          <div>
            <p class="text-[12px] uppercase tracking-wider text-ink-40 font-semibold">Hoạt động</p>
            <h3 class="text-base font-semibold text-ink tracking-tight">Lead mới nhất</h3>
          </div>
          <RouterLink
            to="/leads"
            class="flex items-center gap-1 text-[12px] text-brand-700 hover:text-brand-800 font-medium"
          >
            Xem tất cả <ArrowRight :size="12" weight="bold" />
          </RouterLink>
        </div>

        <div v-if="recentLeads.isLoading.value" class="px-6 py-12 flex justify-center">
          <Spinner label="Đang tải lead..." />
        </div>
        <div v-else-if="recentLeads.isError.value" class="px-6">
          <ErrorState
            title="Không tải được lead gần đây"
            resource="lead gần đây"
            :error="recentLeads.error.value"
            retryable
            @retry="recentLeads.refetch()"
          />
        </div>
        <div v-else-if="(recentLeads.data.value?.results.length ?? 0) === 0" class="px-6">
          <EmptyState title="Chưa có lead nào" description="Khi học viên đăng ký qua form public, lead sẽ xuất hiện ở đây." />
        </div>
        <ul v-else class="divide-y divide-line-soft">
          <li
            v-for="lead in recentLeads.data.value?.results"
            :key="lead.id"
          >
            <RouterLink
              :to="`/leads/${lead.id}`"
              class="flex items-center gap-4 px-6 py-3.5 hover:bg-paper-alt transition-colors"
            >
              <div class="flex h-9 w-9 items-center justify-center rounded-full bg-paper-tint text-brand-700 text-[12px] font-semibold tracking-tight shrink-0">
                {{ lead.name.split(' ').pop()?.[0] || 'L' }}
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-[14px] font-medium text-ink truncate">{{ lead.name }}</p>
                <p class="text-[12px] text-ink-60 tabular-nums">{{ formatPhone(lead.phone) }} · {{ lead.vehicle_class || NO_VALUE }}</p>
              </div>
              <div class="flex flex-col items-end gap-1.5 shrink-0">
                <StatusBadge :status="lead.status" kind="lead" />
                <span class="text-[11px] text-ink-40">{{ timeAgo(lead.created_at) }}</span>
              </div>
            </RouterLink>
          </li>
        </ul>
      </Card>

      <!-- Recent orders 2/5 -->
      <Card class="lg:col-span-2" :padded="false">
        <div class="flex items-center justify-between px-6 py-5 border-b border-line-soft">
          <div>
            <p class="text-[12px] uppercase tracking-wider text-ink-40 font-semibold">Hoạt động</p>
            <h3 class="text-base font-semibold text-ink tracking-tight">Đơn gần đây</h3>
          </div>
          <RouterLink
            to="/orders"
            class="flex items-center gap-1 text-[12px] text-brand-700 hover:text-brand-800 font-medium"
          >
            Xem tất cả <ArrowRight :size="12" weight="bold" />
          </RouterLink>
        </div>

        <div v-if="recentOrders.isLoading.value" class="px-6 py-12 flex justify-center">
          <Spinner label="Đang tải đơn..." />
        </div>
        <div v-else-if="recentOrders.isError.value" class="px-6">
          <ErrorState
            title="Không tải được đơn gần đây"
            resource="đơn gần đây"
            :error="recentOrders.error.value"
            retryable
            @retry="recentOrders.refetch()"
          />
        </div>
        <div v-else-if="(recentOrders.data.value?.results.length ?? 0) === 0" class="px-6">
          <EmptyState title="Chưa có đơn nào" description="Sale chốt lead sẽ tạo đơn ở đây." />
        </div>
        <ul v-else class="divide-y divide-line-soft">
          <li
            v-for="order in (recentOrders.data.value?.results ?? []).slice(0, 6)"
            :key="order.id"
          >
            <RouterLink
              :to="`/orders/${order.id}`"
              class="flex items-center gap-3 px-6 py-3.5 hover:bg-paper-alt transition-colors"
            >
              <div class="flex-1 min-w-0">
                <p class="text-[13px] font-mono font-medium text-ink truncate">{{ order.code }}</p>
                <p class="text-[12px] text-ink-60 truncate">{{ order.person_name }}</p>
              </div>
              <StatusBadge :status="order.status" kind="order" />
            </RouterLink>
          </li>
        </ul>
      </Card>
    </section>
  </div>
</template>
