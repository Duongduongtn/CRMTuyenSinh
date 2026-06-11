<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'
import { useDebounce } from '@vueuse/core'
import { MagnifyingGlass, FunnelSimple, ChatCircleDots, Plus } from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Select from '@/components/ui/Select.vue'
import Button from '@/components/ui/Button.vue'
import Spinner from '@/components/ui/Spinner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import LeadContactModal from '@/components/LeadContactModal.vue'
import { fetchLeads } from '@/api/leads'
import { formatDate, formatNumber, formatPhone, timeAgo, NO_VALUE } from '@/lib/format'

const router = useRouter()

const search = ref('')
const debouncedSearch = useDebounce(search, 300)
const status = ref('')
const priority = ref('')
const source = ref('')
const page = ref(1)

const queryParams = computed(() => ({
  page: page.value,
  search: debouncedSearch.value || undefined,
  status: status.value || undefined,
  priority: priority.value || undefined,
  source: source.value || undefined,
}))

const { data, isLoading, isFetching, isError, error, refetch } = useQuery({
  queryKey: ['leads', queryParams],
  queryFn: () => fetchLeads(queryParams.value),
  placeholderData: (prev) => prev,
})

const hasActiveFilter = computed(
  () => !!(debouncedSearch.value || status.value || priority.value || source.value),
)

function clearFilters() {
  search.value = ''
  status.value = ''
  priority.value = ''
  source.value = ''
  page.value = 1
}

const totalPages = computed(() => {
  const count = data.value?.count ?? 0
  return Math.max(1, Math.ceil(count / 25))
})

watch([debouncedSearch, status, priority, source], () => {
  page.value = 1
})

const statusOptions = [
  { label: 'Tất cả', value: '' },
  { label: 'Chưa liên hệ', value: 'new' },
  { label: 'Đang theo dõi', value: 'following' },
  { label: 'Thành công', value: 'success' },
  { label: 'Thất bại', value: 'failed' },
]

const priorityOptions = [
  { label: 'Tất cả', value: '' },
  { label: 'Nóng', value: 'hot' },
  { label: 'Ấm', value: 'warm' },
  { label: 'Lạnh', value: 'cold' },
]

const sourceOptions = [
  { label: 'Tất cả', value: '' },
  { label: 'Website', value: 'website' },
  { label: 'Landing', value: 'landing' },
  { label: 'Hotline', value: 'hotline' },
  { label: 'Zalo', value: 'zalo' },
  { label: 'FB Ads', value: 'fb_ads' },
  { label: 'Giới thiệu', value: 'referral' },
]

// Modal Ghi nhận liên hệ
const modalLeadId = ref<number | null>(null)
const modalOpen = ref(false)

function openContactModal(id: number, e: MouseEvent) {
  e.stopPropagation()
  e.preventDefault()
  modalLeadId.value = id
  modalOpen.value = true
}

function goDetail(id: number) {
  router.push(`/leads/${id}`)
}

function vehicleClassLabel(code: string): string {
  if (!code) return NO_VALUE
  // Hiển thị mã hạng raw (B-MT, A1, C…) không Việt hoá ngắn
  return code
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <header class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p class="text-[12px] uppercase tracking-wider text-brand-700 font-semibold">Pipeline</p>
        <h2 class="text-3xl font-semibold tracking-tighter text-ink mt-1">Khách tiềm năng</h2>
        <p class="text-[13px] text-ink-60 mt-1">
          {{ formatNumber(data?.count ?? null) }} lead trong hệ thống. Lọc theo trạng thái để theo dõi pipeline.
        </p>
      </div>
      <Button variant="primary" size="md" disabled>
        <Plus :size="16" weight="bold" />
        Tạo lead thủ công
      </Button>
    </header>

    <!-- Filter bar -->
    <Card :padded="false">
      <div class="grid grid-cols-1 gap-3 p-4 lg:grid-cols-[1.5fr_repeat(3,1fr)_auto] lg:items-end">
        <Input v-model="search" placeholder="Tìm theo tên, SĐT, email…" icon-left>
          <template #iconLeft><MagnifyingGlass :size="16" /></template>
        </Input>
        <Select v-model="status" placeholder="Trạng thái" :options="statusOptions" />
        <Select v-model="priority" placeholder="Độ nóng" :options="priorityOptions" />
        <Select v-model="source" placeholder="Nguồn" :options="sourceOptions" />
        <Button variant="ghost" size="md" disabled class="hidden lg:inline-flex">
          <FunnelSimple :size="16" />
          Bộ lọc nâng cao
        </Button>
      </div>
    </Card>

    <!-- Table -->
    <Card :padded="false">
      <div v-if="isLoading" class="flex justify-center py-20">
        <Spinner label="Đang tải danh sách lead..." />
      </div>
      <div v-else-if="isError" class="py-12">
        <ErrorState
          title="Không tải được danh sách lead"
          :error="error"
          :on-retry="() => refetch()"
        />
      </div>
      <div v-else-if="(data?.results.length ?? 0) === 0" class="py-12">
        <EmptyState
          v-if="hasActiveFilter"
          title="Không có lead nào khớp bộ lọc"
          description="Thử mở rộng bộ lọc hoặc bỏ lọc để xem toàn bộ lead."
        >
          <template #action>
            <Button variant="secondary" size="sm" @click="clearFilters">Bỏ tất cả bộ lọc</Button>
          </template>
        </EmptyState>
        <EmptyState
          v-else
          title="Chưa có lead nào trong hệ thống"
          description="Lead xuất hiện khi học viên đăng ký qua form public, gọi hotline, hoặc bật webhook FB Lead Ads. Bạn cũng có thể tạo lead thủ công."
        />
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-[13.5px]">
          <thead class="bg-paper-alt/70 text-[11px] uppercase tracking-wider text-ink-60 font-semibold">
            <tr>
              <th scope="col" class="px-6 py-3 text-left">Khách hàng</th>
              <th scope="col" class="px-3 py-3 text-left">Liên hệ</th>
              <th scope="col" class="px-3 py-3 text-left">Hạng</th>
              <th scope="col" class="px-3 py-3 text-left">Trạng thái</th>
              <th scope="col" class="px-3 py-3 text-left">Độ nóng</th>
              <th scope="col" class="px-3 py-3 text-left">Phụ trách</th>
              <th scope="col" class="px-3 py-3 text-left">Liên hệ gần nhất</th>
              <th scope="col" class="px-3 py-3 text-left">Hẹn lại</th>
              <th scope="col" class="px-3 py-3 text-right pr-6"><span class="sr-only">Hành động</span></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-line-soft">
            <tr
              v-for="lead in data?.results"
              :key="lead.id"
              class="cursor-pointer transition-colors hover:bg-paper-alt/60"
              @click="goDetail(lead.id)"
            >
              <td class="px-6 py-3.5">
                <div class="flex items-center gap-3">
                  <div class="flex h-9 w-9 items-center justify-center rounded-full bg-paper-tint text-brand-700 text-[12px] font-semibold tracking-tight shrink-0">
                    {{ lead.name.split(' ').pop()?.[0] || 'L' }}
                  </div>
                  <div class="min-w-0">
                    <p class="font-medium text-ink truncate">{{ lead.name }}</p>
                    <p class="text-[11px] text-ink-40">#{{ lead.id }} · {{ lead.source }}</p>
                  </div>
                </div>
              </td>
              <td class="px-3 py-3.5 tabular-nums text-ink-60">{{ formatPhone(lead.phone) }}</td>
              <td class="px-3 py-3.5 text-ink-60">{{ vehicleClassLabel(lead.vehicle_class) }}</td>
              <td class="px-3 py-3.5"><StatusBadge :status="lead.status" kind="lead" /></td>
              <td class="px-3 py-3.5">
                <StatusBadge v-if="lead.priority" :status="lead.priority" kind="priority" />
                <span v-else class="text-ink-40">{{ NO_VALUE }}</span>
              </td>
              <td class="px-3 py-3.5 text-ink-60">{{ lead.assigned_to_name || 'Chưa phân' }}</td>
              <td class="px-3 py-3.5 text-ink-60">{{ timeAgo(lead.last_contact_at) }}</td>
              <td class="px-3 py-3.5 text-ink-60">{{ formatDate(lead.next_contact_date) }}</td>
              <td class="px-3 py-3.5 pr-6 text-right">
                <Button
                  variant="secondary"
                  size="sm"
                  @click="openContactModal(lead.id, $event)"
                >
                  <ChatCircleDots :size="14" weight="duotone" />
                  Ghi nhận
                </Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div
        v-if="(data?.count ?? 0) > 25"
        class="flex items-center justify-between border-t border-line-soft px-6 py-4"
      >
        <p class="text-[12px] text-ink-60 tabular-nums">
          Trang {{ page }} / {{ totalPages }} · {{ data?.count }} lead
        </p>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" :disabled="page <= 1" @click="page = page - 1">Trước</Button>
          <Button variant="outline" size="sm" :disabled="page >= totalPages" @click="page = page + 1">Sau</Button>
        </div>
      </div>

      <p
        v-if="isFetching && !isLoading"
        class="sr-only"
        aria-live="polite"
      >Đang tải lại danh sách lead…</p>
    </Card>

    <LeadContactModal
      v-model:open="modalOpen"
      :lead-id="modalLeadId"
    />
  </div>
</template>
