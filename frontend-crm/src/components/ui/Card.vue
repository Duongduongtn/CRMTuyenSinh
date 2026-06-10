<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    padded?: boolean
    interactive?: boolean
    tone?: 'default' | 'alt' | 'tint'
  }>(),
  { padded: true, interactive: false, tone: 'default' },
)

const classes = computed(() =>
  cn(
    'rounded-xl border transition-colors duration-200',
    props.tone === 'alt' && 'bg-paper-alt border-line-soft',
    props.tone === 'tint' && 'bg-paper-tint border-brand-100',
    props.tone === 'default' && 'bg-paper border-line-soft',
    props.padded && 'p-6',
    props.interactive && 'hover:border-line-base cursor-pointer',
  ),
)
</script>

<template>
  <div :class="classes">
    <slot />
  </div>
</template>
