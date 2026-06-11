<script setup lang="ts">
import { computed } from 'vue'
import { ShieldCheck } from '@/lib/icons'
import { useSiteStore } from '@/stores/site'

const props = withDefaults(
  defineProps<{
    variant?: 'paper' | 'dark'
    size?: 'sm' | 'md'
    caption?: string
    fallback?: string
  }>(),
  {
    variant: 'paper',
    size: 'sm',
    caption: 'CRM nội bộ',
    fallback: 'CRM nội bộ',
  },
)

const site = useSiteStore()

const brandName = computed(() => site.resolveBrandName(props.fallback))

const tileClasses = computed(() => {
  const base = 'flex items-center justify-center rounded-lg shrink-0'
  const sizeCls = props.size === 'md' ? 'h-10 w-10' : 'h-9 w-9'
  const variantCls =
    props.variant === 'dark'
      ? 'bg-brand-600/20 ring-1 ring-brand-400/30'
      : 'bg-ink text-paper'
  return `${base} ${sizeCls} ${variantCls}`
})

const iconSize = computed(() => (props.size === 'md' ? 22 : 18))

const captionClasses = computed(() =>
  props.variant === 'dark'
    ? 'text-[12px] uppercase tracking-wider text-paper/60'
    : 'text-[10px] uppercase tracking-wider text-ink-40 font-semibold',
)

const nameClasses = computed(() =>
  props.variant === 'dark'
    ? 'text-sm font-medium text-paper'
    : 'text-sm font-semibold text-ink tracking-tight',
)
</script>

<template>
  <div class="flex items-center gap-3">
    <div :class="tileClasses">
      <ShieldCheck :size="iconSize" weight="duotone" class="text-brand-300" />
    </div>
    <div class="min-w-0">
      <p :class="captionClasses">{{ caption }}</p>
      <p :class="[nameClasses, 'truncate']">{{ brandName }}</p>
    </div>
  </div>
</template>
