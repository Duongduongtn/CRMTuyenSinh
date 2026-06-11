<script setup lang="ts">
import { computed } from 'vue'
import { XCircle, ArrowsClockwise } from '@/lib/icons'
import Button from './Button.vue'

const props = withDefaults(
  defineProps<{
    title?: string
    description?: string
    error?: unknown
    onRetry?: () => void
    retryLabel?: string
  }>(),
  {
    title: 'Không tải được dữ liệu',
    retryLabel: 'Thử lại',
  },
)

function extractStatus(err: unknown): number | null {
  if (!err || typeof err !== 'object') return null
  const e = err as { response?: { status?: number }; status?: number }
  return e.response?.status ?? e.status ?? null
}

const defaultDescription = computed(() => {
  if (props.description) return props.description
  const status = extractStatus(props.error)
  if (status === null) return 'Kiểm tra kết nối mạng rồi bấm Thử lại.'
  if (status === 401) return 'Phiên đăng nhập hết hạn. Tải lại trang để đăng nhập.'
  if (status === 403) return 'Tài khoản không có quyền xem mục này.'
  if (status === 404) return 'Không tìm thấy dữ liệu yêu cầu.'
  if (status === 429) return 'Bạn thao tác quá nhanh. Chờ một phút rồi thử lại.'
  if (status >= 500) return 'Máy chủ đang gặp sự cố. Thử lại sau vài phút.'
  return 'Lỗi không xác định. Kiểm tra kết nối rồi thử lại.'
})
</script>

<template>
  <div
    role="alert"
    aria-live="assertive"
    class="flex flex-col items-center justify-center gap-3 py-16 text-center"
  >
    <div class="flex h-14 w-14 items-center justify-center rounded-full bg-danger/10 text-danger">
      <slot name="icon">
        <XCircle :size="28" weight="duotone" />
      </slot>
    </div>
    <div class="space-y-1">
      <p class="text-[15px] font-semibold text-ink tracking-tight">{{ title }}</p>
      <p class="text-[13px] text-ink-60 max-w-sm">{{ defaultDescription }}</p>
    </div>
    <div v-if="onRetry || $slots.action" class="flex items-center gap-2 mt-1">
      <Button
        v-if="onRetry"
        variant="secondary"
        size="sm"
        @click="onRetry"
      >
        <ArrowsClockwise :size="14" weight="bold" />
        {{ retryLabel }}
      </Button>
      <slot name="action" />
    </div>
  </div>
</template>
