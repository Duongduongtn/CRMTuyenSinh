<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import {
  TrendUp,
  UsersThree,
  ClipboardText,
  Wallet,
  FileXls,
  CaretRight,
} from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Spinner from '@/components/ui/Spinner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { exportRevenueXlsx, fetchConversion, fetchRevenue } from '@/api/reports'
import { formatNumber, formatVND } from '@/lib/format'

/**
 * Mặc định 30 ngày gần nhất theo timezone máy người dùng (sát với BE
 * `DEFAULT_RANGE_DAYS=30` chạy ở Asia/Ho_Chi_Minh). Format YYYY-MM-DD cho
 * type=date input + query string BE.
 */
function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function daysAgoIso(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const from = ref(daysAgoIso(29))
const to = ref(todayIso())
const range = computed(() => ({ from: from.value, to: to.value }))

const revenueQuery = useQuery({
  queryKey: ['report', 'revenue', range],
  queryFn: () => fetchRevenue(range.value),
  placeholderData: (prev) => prev,
})

const conversionQuery = useQuery({
  queryKey: ['report', 'conversion', range],
  queryFn: () => fetchConversion(range.value),
  placeholderData: (prev) => prev,
})

const exporting = ref(false)
async function downloadXlsx() {
  exporting.value = true
  try {
    await exportRevenueXlsx(range.value)
    toast.success('Đã tải Excel doanh thu.')
  } catch (err: unknown) {
    const msg = (err as { response?: { status?: number } })?.response?.status === 429
      ? 'Bạn tải Excel quá nhiều lần. Thử lại sau 1 giờ.'
      : 'Không tạo được file. Kiểm tra khoảng ngày rồi thử lại.'
    toast.error(msg)
  } finally {
    exporting.value = false
  }
}

/** Format ngày VN dd/mm cho hàng table revenue. */
function dateLabel(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

const conversion = computed(() => conversionQuery.data.value)
const revenue = computed(() => revenueQuery.data.value)

/** Đỉnh doanh thu để vẽ bar đơn giản (CSS width %). */
const maxAmount = computed(() => {
  if (!revenue.value?.rows.length) return 0
  return revenue.value.rows.reduce((m, r) => Math.max(m, Number(r.confirmed_amount)), 0)
})

function barWidth(amount: string): string {
  const n = Number(amount)
  if (!maxAmount.value) return '0%'
  return `${Math.max(2, Math.round((n / maxAmount.value) * 100))}%`
}
</script>

<template>
  <div class="space-y-6">
    <header class="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-[12px] uppercase tracking-wider text-brand-700 font-semibold">Tài chính</p>
        <h2 class="text-3xl font-semibold tracking-tighter text-ink mt-1">Báo cáo</h2>
        <p class="text-[13px] text-ink-60 mt-1">
          Doanh thu xác nhận theo ngày và tỉ lệ chuyển đổi lead → đơn → paid.
        </p>
      </div>
      <Button
        variant="primary"
        size="md"
        :loading="exporting"
        @click="downloadXlsx"
      >
        <FileXls :size="16" weight="duotone" />
        Tải Excel
      </Button>
    </header>

    <!-- Range picker -->
    <Card>
      <div class="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
        <Input
          v-model="from"
          type="date"
          label="Từ ngày"
        />
        <Input
          v-model="to"
          type="date"
          label="Đến ngày"
        />
        <p class="text-[12px] text-ink-40 lg:pb-3">
          Tối đa 366 ngày. Múi giờ Asia/Ho_Chi_Minh.
        </p>
      </div>
    </Card>

    <!-- Conversion loading / error / empty -->
    <Card v-if="conversionQuery.isLoading.value" class="py-2">
      <div class="flex justify-center py-10">
        <Spinner label="Đang tải tỉ lệ chuyển đổi..." />
      </div>
    </Card>
    <Card v-else-if="conversionQuery.isError.value" class="py-2">
      <ErrorState
        title="Không tải được tỉ lệ chuyển đổi"
        resource="báo cáo chuyển đổi"
        :error="conversionQuery.error.value"
        retryable
        @retry="conversionQuery.refetch()"
      />
    </Card>

    <!-- Conversion summary bento -->
    <section
      v-else-if="conversion"
      class="grid gap-4 grid-cols-2 lg:grid-cols-12"
    >
      <Card class="lg:col-span-3">
        <div class="flex items-start justify-between gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-700 border border-brand-100">
            <UsersThree :size="20" weight="duotone" />
          </div>
        </div>
        <div class="mt-4 space-y-1">
          <p class="text-[12px] text-ink-60 font-medium">Lead trong khoảng</p>
          <p class="text-[26px] font-semibold tracking-tighter text-ink tabular-nums">
            {{ formatNumber(conversion.leads) }}
          </p>
        </div>
      </Card>

      <Card class="lg:col-span-3">
        <div class="flex items-start justify-between gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-info-soft text-info border border-info/20">
            <ClipboardText :size="20" weight="duotone" />
          </div>
        </div>
        <div class="mt-4 space-y-1">
          <p class="text-[12px] text-ink-60 font-medium">Đơn tạo trong khoảng</p>
          <p class="text-[26px] font-semibold tracking-tighter text-ink tabular-nums">
            {{ formatNumber(conversion.enrollments) }}
          </p>
          <p class="text-[11px] text-ink-40">
            {{ conversion.rate_lead_to_enrollment_pct }}% từ lead
          </p>
        </div>
      </Card>

      <Card class="lg:col-span-3">
        <div class="flex items-start justify-between gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-success-soft text-success border border-success/20">
            <Wallet :size="20" weight="duotone" />
          </div>
        </div>
        <div class="mt-4 space-y-1">
          <p class="text-[12px] text-ink-60 font-medium">Đơn đã đóng cọc</p>
          <p class="text-[26px] font-semibold tracking-tighter text-ink tabular-nums">
            {{ formatNumber(conversion.paid) }}
          </p>
          <p class="text-[11px] text-ink-40">
            {{ conversion.rate_enrollment_to_paid_pct }}% từ đơn
          </p>
        </div>
      </Card>

      <Card class="lg:col-span-3" tone="tint">
        <div class="flex items-start justify-between gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600/10 text-brand-700 border border-brand-200">
            <TrendUp :size="20" weight="duotone" />
          </div>
        </div>
        <div class="mt-4 space-y-1">
          <p class="text-[12px] text-ink-60 font-medium">Chuyển đổi tổng</p>
          <p class="text-[26px] font-semibold tracking-tighter text-brand-800 tabular-nums">
            {{ conversion.rate_overall_pct }}%
          </p>
          <p class="text-[11px] text-ink-40">Lead → cọc</p>
        </div>
      </Card>
    </section>

    <!-- Revenue table + simple bar -->
    <Card :padded="false">
      <div class="px-6 py-5 border-b border-line-soft flex items-center justify-between">
        <div>
          <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">Doanh thu xác nhận</p>
          <h3 class="text-base font-semibold text-ink tracking-tight">Theo ngày</h3>
        </div>
        <div v-if="revenue" class="text-right">
          <p class="text-[11px] text-ink-40">Tổng khoảng</p>
          <p class="text-[18px] font-semibold tabular-nums tracking-tight text-ink">
            {{ formatVND(revenue.summary.total_amount) }}
          </p>
          <p class="text-[11px] text-ink-40 tabular-nums">
            {{ formatNumber(revenue.summary.total_count) }} giao dịch
          </p>
        </div>
      </div>

      <div v-if="revenueQuery.isLoading.value" class="flex justify-center py-20">
        <Spinner label="Đang tải báo cáo..." />
      </div>
      <div v-else-if="revenueQuery.isError.value" class="py-12">
        <ErrorState
          title="Không tải được doanh thu"
          resource="báo cáo doanh thu"
          :error="revenueQuery.error.value"
          retryable
          @retry="revenueQuery.refetch()"
        />
      </div>
      <div v-else-if="!revenue?.rows.length" class="py-12">
        <EmptyState
          title="Chưa có giao dịch xác nhận trong khoảng"
          description="Thử mở rộng khoảng ngày, đợi đối soát Casso, hoặc kiểm tra trạng thái thanh toán ở mục Thanh toán."
        />
      </div>
      <div v-else class="px-6 py-4">
        <ul class="divide-y divide-line-soft">
          <li
            v-for="row in revenue.rows"
            :key="row.date"
            class="grid grid-cols-[80px_1fr_120px_70px] items-center gap-3 py-3"
          >
            <span class="text-[12px] tabular-nums text-ink-60">{{ dateLabel(row.date) }}</span>
            <div class="relative h-2 rounded-full bg-paper-alt overflow-hidden">
              <div
                class="absolute inset-y-0 left-0 bg-brand-500 rounded-full transition-all"
                :style="{ width: barWidth(row.confirmed_amount) }"
                aria-hidden="true"
              />
            </div>
            <span class="text-right text-[13.5px] font-medium tabular-nums text-ink">
              {{ formatVND(row.confirmed_amount) }}
            </span>
            <span class="text-right text-[11px] tabular-nums text-ink-40">
              {{ formatNumber(row.confirmed_count) }} GD
            </span>
          </li>
        </ul>
      </div>
    </Card>

    <p class="text-[11px] text-ink-40 leading-relaxed max-w-2xl">
      <CaretRight :size="11" class="inline -mt-0.5" weight="bold" />
      Báo cáo dựa trên Payment có status xác nhận và Enrollment trong cohort khoảng.
      Lưu ý: số "Đơn đã đóng cọc" tính enrollment tạo trong khoảng đã có ít nhất 1
      payment xác nhận (kể cả sau khoảng); khác doanh thu (chỉ tính payment xác
      nhận trong khoảng).
    </p>
  </div>
</template>
