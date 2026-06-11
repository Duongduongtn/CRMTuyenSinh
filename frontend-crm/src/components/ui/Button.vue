<script setup lang="ts">
import { computed } from 'vue'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const button = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium tracking-tight transition-all duration-200 ease-out-expo focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-paper disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary:
          'bg-ink text-paper hover:bg-ink/90 active:translate-y-px shadow-[0_1px_0_0_rgba(15,31,26,0.04)]',
        accent:
          'bg-brand-600 text-paper hover:bg-brand-700 active:translate-y-px',
        secondary:
          'bg-paper-alt text-ink border border-line-base hover:bg-paper-tint hover:border-brand-200',
        ghost: 'text-ink-60 hover:text-ink hover:bg-paper-alt',
        outline:
          'border border-line-base text-ink bg-paper hover:border-ink-60 hover:bg-paper-alt',
        danger:
          'bg-danger text-paper hover:bg-danger/90 active:translate-y-px',
        link: 'text-brand-700 underline-offset-4 hover:underline px-0',
      },
      size: {
        sm: 'h-8 px-3 text-[13px] rounded-md',
        md: 'h-10 px-4 text-sm rounded-md',
        lg: 'h-11 px-5 text-[15px] rounded-md',
        icon: 'h-9 w-9 rounded-md',
        'icon-sm': 'h-8 w-8 rounded-md',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
)

export type ButtonVariant = VariantProps<typeof button>['variant']
export type ButtonSize = VariantProps<typeof button>['size']

const props = withDefaults(
  defineProps<{
    variant?: ButtonVariant
    size?: ButtonSize
    type?: 'button' | 'submit' | 'reset'
    disabled?: boolean
    loading?: boolean
    as?: 'button' | 'a'
    href?: string
  }>(),
  { type: 'button', as: 'button' },
)

const classes = computed(() => cn(button({ variant: props.variant, size: props.size })))
</script>

<template>
  <component
    :is="as"
    :type="as === 'button' ? type : undefined"
    :href="as === 'a' ? href : undefined"
    :disabled="disabled || loading"
    :class="classes"
  >
    <svg
      v-if="loading"
      class="h-4 w-4 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" opacity="0.25" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
      />
    </svg>
    <slot />
  </component>
</template>
