<script setup lang="ts">
withDefaults(
  defineProps<{ title?: string; description?: string }>(),
  { title: 'Chưa có dữ liệu', description: 'Khi có dữ liệu mới, mục này sẽ hiển thị.' },
)
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3 py-16 text-center">
    <div class="flex h-14 w-14 items-center justify-center rounded-full bg-paper-tint">
      <slot name="icon" />
    </div>
    <div class="space-y-1">
      <p class="text-[15px] font-semibold text-ink tracking-tight">{{ title }}</p>
      <p class="text-[13px] text-ink-60 max-w-sm">{{ description }}</p>
    </div>
    <slot name="action" />
  </div>
</template>
