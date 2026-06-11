<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { useDebounce } from '@vueuse/core'
import { MagnifyingGlass } from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Button from '@/components/ui/Button.vue'
import Spinner from '@/components/ui/Spinner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { fetchPayments } from '@/api/payments'
import { formatVND, formatNumber, formatDateTime, NO_VALUE } from '@/lib/format'

const search = ref('')
const debouncedSearch = useDebounce(search, 300)
const status = ref('')
const page = ref(1)

const params = computed(() => ({
  page: page.value,
  search: debouncedSearch.value || undefined,
  status: status.value || undefined,
}))

const { data, isLoading } = useQuery({
  queryKey: ['payments', params],
  queryFn: () => fetchPayments(params.value),
  placeholderData: (prev) => prev,
})

watch([debouncedSearch, status], () => {
  page.value = 1
})

const totalPages = computed(() => Math.max(1, Math.ceil((data.value?.count ?? 0) / 25)))
const statusOptions = [
  { label: 'Tất cả', value: '' },
  { label: 'Chờ xác nhận', value: 'pending' },
  { label: 'Đã xác nhận', value: 'confirmed' },
  { label: 'Thất bại', value: 'failed' },
  { label: 'Hoàn tiền', value: 'refunded' },
]
</script>

<template>
  <div class="space-y-6">
    <header>
      <p class="text-[12px] uppercase tracking-wider text-brand-700 font-semibold">Tài chính</p>
      <h2 class="text-3xl font-semibold tracking-tighter text-ink mt-1">Thanh toán</h2>
      <p class="text-[13px] text-ink-60 mt-1">
        {{ formatNumber(data?.count ?? null) }} giao dịch. Tự đối soát qua Casso webhook trong 2 phút.
      </p>
    </header>

    <Card :padded="false">
      <div class="grid grid-cols-1 gap-3 p-4 lg:grid-cols-[2fr_1fr] lg:items-end">
        <Input v-model="search" placeholder="Tìm theo mã đơn, số tiền…" icon-left>
          <template #iconLeft><MagnifyingGlass :size="16" /></template>
        </Input>
        <Select v-model="status" placeholder="Trạng thái" :options="statusOptions" />
      </div>
    </Card>

    <Card :padded="false">
      <div v-if="isLoading" class="flex justify-center py-20">
        <Spinner label="Đang tải giao dịch..." />
      </div>
      <div v-else-if="(data?.results.length ?? 0) === 0" class="py-12">
        <EmptyState title="Chưa có giao dịch" description="Khi học viên cọc, giao dịch xuất hiện ở đây." />
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-[13.5px]">
          <thead class="bg-paper-alt/70 text-[11px] uppercase tracking-wider text-ink-60 font-semibold">
            <tr>
              <th scope="col" class="px-6 py-3 text-left">Mã đơn</th>
              <th scope="col" class="px-3 py-3 text-right">Số tiền</th>
              <th scope="col" class="px-3 py-3 text-left">Phương thức</th>
              <th scope="col" class="px-3 py-3 text-left">Trạng thái</th>
              <th scope="col" class="px-3 py-3 text-left">Xác nhận lúc</th>
              <th scope="col" class="px-3 py-3 text-left pr-6">Ghi chú</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-line-soft">
            <tr v-for="p in data?.results" :key="p.id" class="hover:bg-paper-alt/60">
              <td class="px-6 py-3.5 font-mono text-ink">{{ p.enrollment_code }}</td>
              <td class="px-3 py-3.5 text-right tabular-nums text-ink font-medium">{{ formatVND(p.amount) }}</td>
              <td class="px-3 py-3.5 text-ink-60">{{ p.payment_method }}</td>
              <td class="px-3 py-3.5"><StatusBadge :status="p.status" kind="payment" /></td>
              <td class="px-3 py-3.5 text-ink-60 text-[12px]">{{ formatDateTime(p.confirmed_at) }}</td>
              <td class="px-3 py-3.5 pr-6 text-ink-60 text-[12px] truncate max-w-xs">{{ p.note || NO_VALUE }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-if="(data?.count ?? 0) > 25"
        class="flex items-center justify-between border-t border-line-soft px-6 py-4"
      >
        <p class="text-[12px] text-ink-60 tabular-nums">Trang {{ page }} / {{ totalPages }}</p>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" :disabled="page <= 1" @click="page = page - 1">Trước</Button>
          <Button variant="outline" size="sm" :disabled="page >= totalPages" @click="page = page + 1">Sau</Button>
        </div>
      </div>
    </Card>
  </div>
</template>
