<script setup lang="ts">
import { PhCircleDashed, PhCheckCircle, PhClock, PhXCircle, PhCurrencyCircleDollar } from '@phosphor-icons/vue'

const props = defineProps<{
  status: string
  label?: string
}>()

const config = computed(() => {
  const map: Record<string, { cls: string; icon: any; default: string }> = {
    pending: { cls: 'badge-warning', icon: PhClock, default: 'Chờ cọc' },
    deposited: { cls: 'badge-success', icon: PhCheckCircle, default: 'Đã cọc' },
    partial: { cls: 'badge-warning', icon: PhCurrencyCircleDollar, default: 'Đóng một phần' },
    completed: { cls: 'badge-success', icon: PhCheckCircle, default: 'Đóng đủ' },
    cancelled: { cls: 'badge-danger', icon: PhXCircle, default: 'Đã hủy' },
    refunded: { cls: 'badge-neutral', icon: PhCircleDashed, default: 'Đã hoàn tiền' },
    approved: { cls: 'badge-success', icon: PhCheckCircle, default: 'Đã duyệt' },
    rejected: { cls: 'badge-danger', icon: PhXCircle, default: 'Từ chối' },
    expired: { cls: 'badge-neutral', icon: PhCircleDashed, default: 'Hết hạn' },
    purged: { cls: 'badge-neutral', icon: PhCircleDashed, default: 'Đã xóa' },
  }
  return map[props.status] || { cls: 'badge-neutral', icon: PhCircleDashed, default: props.status }
})
</script>

<template>
  <span class="badge" :class="config.cls">
    <component :is="config.icon" class="size-3.5" weight="fill" />
    {{ label || config.default }}
  </span>
</template>
