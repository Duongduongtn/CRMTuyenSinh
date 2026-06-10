<script setup lang="ts">
withDefaults(defineProps<{ size?: number; label?: string }>(), { size: 20 })
</script>

<template>
  <span class="inline-flex items-center gap-2 text-ink-60" role="status">
    <svg
      class="animate-spin text-brand-600"
      :width="size"
      :height="size"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" opacity="0.2" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    </svg>
    <span v-if="label" class="text-[13px]">{{ label }}</span>
  </span>
</template>
