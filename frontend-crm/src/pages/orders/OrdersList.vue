<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'
import { useDebounce } from '@vueuse/core'
import { toast } from 'vue-sonner'
import { MagnifyingGlass, FilePdf } from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Button from '@/components/ui/Button.vue'
import Spinner from '@/components/ui/Spinner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { fetchEnrollments, downloadEnrollmentPDF } from '@/api/orders'
import { formatVND, formatNumber, formatDateTime } from '@/lib/format'

const router = useRouter()
const search = ref('')
const debouncedSearch = useDebounce(search, 300)
const status = ref('')
const page = ref(1)

const queryParams = computed(() => ({
  page: page.value,
  search: debouncedSearch.value || undefined,
  status: status.value || undefined,
}))

const { data, isLoading, isError, error, refetch } = useQuery({
  queryKey: ['orders', queryParams],
  queryFn: () => fetchEnrollments(queryParams.value),
  placeholderData: (prev) => prev,
})

const hasActiveFilter = computed(() => !!(debouncedSearch.value || status.value))

function clearFilters() {
  search.value = ''
  status.value = ''
  page.value = 1
}

watch([debouncedSearch, status], () => {
  page.value = 1
})

const totalPages = computed(() => Math.max(1, Math.ceil((data.value?.count ?? 0) / 25)))

const statusOptions = [
  { label: 'Tất cả', value: '' },
  { label: 'Chờ cọc', value: 'pending_deposit' },
  { label: 'Đã cọc', value: 'deposit_paid' },
  { label: 'Cọc 1 phần', value: 'partial_paid' },
  { label: 'Đã đóng đủ', value: 'fully_paid' },
  { label: 'Hoàn tất', value: 'completed' },
  { label: 'Đã huỷ', value: 'cancelled' },
]

const downloading = ref<number | null>(null)
async function printPDF(id: number, code: string, e: MouseEvent) {
  e.stopPropagation()
  e.preventDefault()
  downloading.value = id
  try {
    await downloadEnrollmentPDF(id, code)
    toast.success(`Đã tải PDF đơn ${code}.`)
  } catch {
    toast.error('Không tạo được PDF. Kiểm tra dữ liệu đơn rồi thử lại.')
  } finally {
    downloading.value = null
  }
}
</script>

<template>
  <div class="space-y-6">
    <header class="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-[12px] uppercase tracking-wider text-brand-700 font-semibold">Đơn đăng ký</p>
        <h2 class="text-3xl font-semibold tracking-tighter text-ink mt-1">Danh sách đơn</h2>
        <p class="text-[13px] text-ink-60 mt-1">
          {{ formatNumber(data?.count ?? null) }} đơn trong hệ thống. Click vào dòng để xem chi tiết, hoặc bấm "In PDF" để tải đơn đăng ký nộp Sở.
        </p>
      </div>
    </header>

    <Card :padded="false">
      <div class="grid grid-cols-1 gap-3 p-4 lg:grid-cols-[2fr_1fr] lg:items-end">
        <Input v-model="search" placeholder="Tìm theo mã đơn, tên học viên, SĐT…" icon-left>
          <template #iconLeft><MagnifyingGlass :size="16" /></template>
        </Input>
        <Select v-model="status" placeholder="Trạng thái" :options="statusOptions" />
      </div>
    </Card>

    <Card :padded="false">
      <div v-if="isLoading" class="flex justify-center py-20">
        <Spinner label="Đang tải danh sách đơn..." />
      </div>
      <div v-else-if="isError" class="py-12">
        <ErrorState
          title="Không tải được danh sách đơn"
          resource="danh sách đơn"
          :error="error"
          retryable
          @retry="refetch"
        />
      </div>
      <div v-else-if="(data?.results.length ?? 0) === 0" class="py-12">
        <EmptyState
          v-if="hasActiveFilter"
          title="Không có đơn nào khớp bộ lọc"
          description="Thử mở rộng bộ lọc hoặc bỏ lọc để xem tất cả đơn."
        >
          <template #action>
            <Button variant="secondary" size="sm" @click="clearFilters">Bỏ tất cả bộ lọc</Button>
          </template>
        </EmptyState>
        <EmptyState
          v-else
          title="Chưa có đơn đăng ký nào"
          description="Đơn được tạo khi sale chốt lead thành công. Mỗi đơn sẽ có QR cọc, theo dõi paid, in PDF nộp Sở."
        />
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-[13.5px]">
          <thead class="bg-paper-alt/70 text-[11px] uppercase tracking-wider text-ink-60 font-semibold">
            <tr>
              <th scope="col" class="px-6 py-3 text-left">Mã đơn</th>
              <th scope="col" class="px-3 py-3 text-left">Học viên</th>
              <th scope="col" class="px-3 py-3 text-left">Khoá học</th>
              <th scope="col" class="px-3 py-3 text-right">Tổng tiền</th>
              <th scope="col" class="px-3 py-3 text-right">Đã đóng</th>
              <th scope="col" class="px-3 py-3 text-left">Trạng thái</th>
              <th scope="col" class="px-3 py-3 text-left">Tạo lúc</th>
              <th scope="col" class="px-3 py-3 text-right pr-6"><span class="sr-only">Hành động</span></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-line-soft">
            <tr
              v-for="order in data?.results"
              :key="order.id"
              class="cursor-pointer transition-colors hover:bg-paper-alt/60"
              @click="router.push(`/orders/${order.id}`)"
            >
              <td class="px-6 py-3.5 font-mono font-medium text-ink">{{ order.code }}</td>
              <td class="px-3 py-3.5">
                <div>
                  <p class="font-medium text-ink truncate">{{ order.person_name }}</p>
                  <p class="text-[12px] text-ink-60 tabular-nums">{{ order.person_phone }}</p>
                </div>
              </td>
              <td class="px-3 py-3.5">
                <p class="text-ink truncate">{{ order.course_title }}</p>
                <p class="text-[11px] text-ink-40">{{ order.vehicle_class }}</p>
              </td>
              <td class="px-3 py-3.5 text-right tabular-nums text-ink">{{ formatVND(order.total_amount) }}</td>
              <td class="px-3 py-3.5 text-right tabular-nums text-success font-medium">{{ formatVND(order.paid_amount) }}</td>
              <td class="px-3 py-3.5"><StatusBadge :status="order.status" kind="order" /></td>
              <td class="px-3 py-3.5 text-ink-60 text-[12px]">{{ formatDateTime(order.created_at) }}</td>
              <td class="px-3 py-3.5 pr-6 text-right">
                <Button
                  variant="secondary"
                  size="sm"
                  :loading="downloading === order.id"
                  @click="printPDF(order.id, order.code, $event)"
                >
                  <FilePdf :size="14" weight="duotone" />
                  In PDF
                </Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-if="(data?.count ?? 0) > 25"
        class="flex items-center justify-between border-t border-line-soft px-6 py-4"
      >
        <p class="text-[12px] text-ink-60 tabular-nums">Trang {{ page }} / {{ totalPages }} · {{ data?.count }} đơn</p>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" :disabled="page <= 1" @click="page = page - 1">Trước</Button>
          <Button variant="outline" size="sm" :disabled="page >= totalPages" @click="page = page + 1">Sau</Button>
        </div>
      </div>
    </Card>
  </div>
</template>
