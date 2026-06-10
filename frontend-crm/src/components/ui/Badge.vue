<script setup lang="ts">
import { computed } from 'vue'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badge = cva(
  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-tight uppercase letter-spacing-wider',
  {
    variants: {
      tone: {
        neutral: 'bg-paper-alt text-ink-60 border border-line-soft',
        success: 'bg-success-soft text-success border border-success/20',
        warning: 'bg-warning-soft text-warning border border-warning/20',
        danger: 'bg-danger-soft text-danger border border-danger/20',
        info: 'bg-info-soft text-info border border-info/20',
        brand: 'bg-brand-50 text-brand-700 border border-brand-100',
      },
      size: {
        sm: 'h-5 text-[10px]',
        md: 'h-6 text-[11px]',
      },
    },
    defaultVariants: { tone: 'neutral', size: 'md' },
  },
)

export type BadgeTone = VariantProps<typeof badge>['tone']

const props = withDefaults(
  defineProps<{ tone?: BadgeTone; size?: 'sm' | 'md'; dot?: boolean }>(),
  { tone: 'neutral', size: 'md' },
)

const dotColor = computed(() => {
  switch (props.tone) {
    case 'success':
      return 'bg-success'
    case 'warning':
      return 'bg-warning'
    case 'danger':
      return 'bg-danger'
    case 'info':
      return 'bg-info'
    case 'brand':
      return 'bg-brand-600'
    default:
      return 'bg-ink-40'
  }
})
</script>

<template>
  <span :class="cn(badge({ tone, size }))">
    <span v-if="dot" :class="['h-1.5 w-1.5 rounded-full', dotColor]" />
    <slot />
  </span>
</template>
