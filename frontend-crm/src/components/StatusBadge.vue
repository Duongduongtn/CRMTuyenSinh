<script setup lang="ts">
import Badge, { type BadgeTone } from '@/components/ui/Badge.vue'

const props = defineProps<{ status: string; kind?: 'lead' | 'order' | 'payment' | 'priority' }>()

const map: Record<string, Record<string, { label: string; tone: BadgeTone }>> = {
  lead: {
    new: { label: 'Chưa liên hệ', tone: 'info' },
    following: { label: 'Đang theo dõi', tone: 'warning' },
    success: { label: 'Thành công', tone: 'success' },
    failed: { label: 'Thất bại', tone: 'danger' },
  },
  order: {
    pending_deposit: { label: 'Chờ cọc', tone: 'warning' },
    deposit_paid: { label: 'Đã cọc', tone: 'brand' },
    partial_paid: { label: 'Cọc 1 phần', tone: 'brand' },
    fully_paid: { label: 'Đã đóng đủ', tone: 'success' },
    completed: { label: 'Hoàn tất', tone: 'success' },
    cancelled: { label: 'Đã huỷ', tone: 'neutral' },
  },
  payment: {
    pending: { label: 'Chờ xác nhận', tone: 'warning' },
    confirmed: { label: 'Đã xác nhận', tone: 'success' },
    failed: { label: 'Thất bại', tone: 'danger' },
    refunded: { label: 'Hoàn tiền', tone: 'neutral' },
  },
  priority: {
    hot: { label: 'Nóng', tone: 'danger' },
    warm: { label: 'Ấm', tone: 'warning' },
    cold: { label: 'Lạnh', tone: 'info' },
  },
}

const entry = map[props.kind ?? 'lead']?.[props.status]
</script>

<template>
  <Badge v-if="entry" :tone="entry.tone" dot size="sm">{{ entry.label }}</Badge>
  <Badge v-else tone="neutral" size="sm">{{ status }}</Badge>
</template>
