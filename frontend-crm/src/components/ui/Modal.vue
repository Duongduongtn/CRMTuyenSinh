<script setup lang="ts">
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from 'radix-vue'
import { X } from '@/lib/icons'
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    open: boolean
    title?: string
    description?: string
    size?: 'sm' | 'md' | 'lg' | 'xl' | 'wide'
    closeOnOverlay?: boolean
  }>(),
  { size: 'md', closeOnOverlay: true },
)
const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const sizeMap = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-3xl',
  wide: 'max-w-5xl',
}
</script>

<template>
  <DialogRoot :open="open" @update:open="(v) => emit('update:open', v)">
    <DialogPortal>
      <DialogOverlay
        class="fixed inset-0 z-50 bg-ink/40 backdrop-blur-[2px] data-[state=open]:animate-fade-in"
      />
      <DialogContent
        :class="
          cn(
            'fixed left-1/2 top-1/2 z-50 flex w-[calc(100%-2rem)] max-h-[calc(100vh-2rem)] sm:max-h-[85vh] -translate-x-1/2 -translate-y-1/2 flex-col',
            'rounded-2xl border border-line-soft bg-paper shadow-[0_24px_48px_-12px_rgba(15,31,26,0.18)]',
            'data-[state=open]:animate-slide-up',
            sizeMap[props.size],
          )
        "
      >
        <div
          v-if="title || $slots.header"
          class="shrink-0 flex items-start justify-between gap-4 border-b border-line-soft px-6 py-5"
        >
          <div class="flex-1 min-w-0">
            <DialogTitle v-if="title" class="text-base font-semibold text-ink tracking-tight">{{ title }}</DialogTitle>
            <DialogDescription v-if="description" class="mt-1 text-[13px] text-ink-60">{{ description }}</DialogDescription>
            <slot name="header" />
          </div>
          <DialogClose
            class="-mr-2 -mt-1 flex h-9 w-9 items-center justify-center rounded-md text-ink-40 transition-colors hover:bg-paper-alt hover:text-ink"
            aria-label="Đóng"
          >
            <X :size="18" weight="regular" />
          </DialogClose>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto">
          <slot />
        </div>
        <div
          v-if="$slots.footer"
          class="shrink-0 flex items-center justify-end gap-3 border-t border-line-soft px-6 py-4"
        >
          <slot name="footer" />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
