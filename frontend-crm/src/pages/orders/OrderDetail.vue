<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import { ArrowLeft, Check, ClockCountdown, Copy, FilePdf, Link, Receipt } from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Spinner from '@/components/ui/Spinner.vue'
import Modal from '@/components/ui/Modal.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { fetchEnrollment, downloadEnrollmentPDF } from '@/api/orders'
import { generateStudentQuickToken } from '@/api/students'
import { formatVND, formatDateTime } from '@/lib/format'

const route = useRoute()
const router = useRouter()
const id = computed(() => Number(route.params.id))

const { data, isLoading } = useQuery({
  queryKey: ['order', id],
  queryFn: () => fetchEnrollment(id.value),
})

const downloading = ref(false)
async function print() {
  if (!data.value) return
  downloading.value = true
  try {
    await downloadEnrollmentPDF(id.value, String(data.value.code))
    toast.success('Đã tải PDF đơn.')
  }
  catch {
    toast.error('Không tạo được PDF. Kiểm tra dữ liệu đơn rồi thử lại.')
  }
  finally {
    downloading.value = false
  }
}

const quickLinkOpen = ref(false)
const generatingLink = ref(false)
const quickUrl = ref('')
const quickExpiresHours = ref(24)
const copied = ref(false)

async function openQuickLink() {
  if (!data.value) return
  generatingLink.value = true
  copied.value = false
  try {
    const resp = await generateStudentQuickToken(id.value)
    quickUrl.value = resp.url
    quickExpiresHours.value = Math.round(resp.expires_in_seconds / 3600)
    quickLinkOpen.value = true
  }
  catch (err: any) {
    const detail = err?.response?.data?.detail
    const code = err?.response?.data?.code
    if (code === 'missing_phone') {
      toast.error('Đơn chưa có số điện thoại. Bổ sung trong CRM rồi tạo lại.')
    }
    else if (code === 'account_missing') {
      toast.error('Chưa có tài khoản học viên cho số điện thoại này.')
    }
    else if (err?.response?.status === 403) {
      toast.error('Bạn không có quyền tạo link xem nhanh. Liên hệ quản trị viên.')
    }
    else {
      toast.error(detail || 'Không tạo được link. Vui lòng thử lại.')
    }
  }
  finally {
    generatingLink.value = false
  }
}

async function copyUrl() {
  try {
    await navigator.clipboard.writeText(quickUrl.value)
    copied.value = true
    toast.success('Đã chép link vào bộ nhớ tạm.')
    setTimeout(() => { copied.value = false }, 2500)
  }
  catch {
    toast.error('Không chép được. Vui lòng chọn link và Ctrl+C thủ công.')
  }
}
</script>

<template>
  <div>
    <Button variant="ghost" size="sm" class="mb-4" @click="router.back()">
      <ArrowLeft :size="14" weight="bold" />
      Quay lại
    </Button>

    <div v-if="isLoading" class="py-20 flex justify-center">
      <Spinner label="Đang tải chi tiết đơn" />
    </div>

    <div v-else-if="data" class="space-y-5">
      <Card>
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">Mã đơn</p>
            <h2 class="text-3xl font-mono font-semibold tracking-tight text-ink">
              {{ data.code }}
            </h2>
            <p class="text-[13px] text-ink-60 mt-1">
              {{ data.course_title }}
            </p>
          </div>
          <div class="flex flex-col items-end gap-2">
            <StatusBadge :status="data.status" kind="order" />
            <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
              <Button
                variant="secondary"
                :loading="generatingLink"
                @click="openQuickLink"
              >
                <Link :size="14" weight="bold" />
                Tạo link xem nhanh
              </Button>
              <Button variant="primary" :loading="downloading" @click="print">
                <FilePdf :size="14" weight="duotone" />
                In PDF
              </Button>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 lg:grid-cols-4 gap-y-4 mt-6 pt-6 border-t border-line-soft text-[13px]">
          <div class="space-y-0.5">
            <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">Học viên</p>
            <p class="text-ink font-medium truncate">{{ data.person_name }}</p>
          </div>
          <div class="space-y-0.5">
            <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">SĐT</p>
            <p class="text-ink tabular-nums">{{ data.person_phone }}</p>
          </div>
          <div class="space-y-0.5">
            <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">Tạo lúc</p>
            <p class="text-ink">{{ formatDateTime(data.created_at) }}</p>
          </div>
          <div class="space-y-0.5">
            <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">Hạng GPLX</p>
            <p class="text-ink">{{ data.vehicle_class }}</p>
          </div>
        </div>
      </Card>

      <Card>
        <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold mb-3">Tài chính</p>
        <div class="grid grid-cols-3 gap-6">
          <div>
            <p class="text-[12px] text-ink-60">Tổng học phí</p>
            <p class="text-2xl font-semibold text-ink tabular-nums tracking-tighter">
              {{ formatVND(data.total_amount) }}
            </p>
          </div>
          <div>
            <p class="text-[12px] text-ink-60">Đã đóng</p>
            <p class="text-2xl font-semibold text-success tabular-nums tracking-tighter">
              {{ formatVND(data.paid_amount) }}
            </p>
          </div>
          <div>
            <p class="text-[12px] text-ink-60">Cọc yêu cầu</p>
            <p class="text-2xl font-semibold text-ink tabular-nums tracking-tighter">
              {{ formatVND(data.deposit_amount) }}
            </p>
          </div>
        </div>

        <div class="mt-4 pt-4 border-t border-line-soft flex items-center gap-2 text-[12px] text-ink-60">
          <Receipt :size="14" class="text-ink-40" weight="duotone" />
          Lịch sử thanh toán chi tiết xem ở trang
          <RouterLink to="/payments" class="text-brand-700 hover:underline underline-offset-2">
            Thanh toán
          </RouterLink>.
        </div>
      </Card>
    </div>

    <Modal
      v-model:open="quickLinkOpen"
      title="Link xem nhanh cho học viên"
      description="Gửi link cho học viên qua Zalo, tin nhắn, hoặc đọc trực tiếp qua điện thoại."
      size="md"
    >
      <div class="px-6 py-5 space-y-4">
        <div class="rounded-lg bg-paper-alt p-3">
          <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold mb-2">
            URL xem nhanh
          </p>
          <p class="text-[13px] text-ink break-all font-mono num-display leading-relaxed">
            {{ quickUrl }}
          </p>
        </div>

        <div class="flex items-start gap-2 text-[12px] text-ink-60 leading-relaxed">
          <ClockCountdown :size="14" class="text-ink-40 mt-0.5 shrink-0" weight="duotone" />
          <p>
            Link có hiệu lực <span class="num-display font-semibold text-ink">{{ quickExpiresHours }} giờ</span>.
            Chỉ học viên đúng số điện thoại của đơn này mới đọc được nội dung. Học viên không cần đăng nhập.
          </p>
        </div>
      </div>

      <template #footer>
        <Button variant="ghost" @click="quickLinkOpen = false">Đóng</Button>
        <Button variant="accent" @click="copyUrl">
          <Check v-if="copied" :size="14" weight="bold" />
          <Copy v-else :size="14" weight="bold" />
          {{ copied ? 'Đã chép' : 'Chép link' }}
        </Button>
      </template>
    </Modal>
  </div>
</template>
