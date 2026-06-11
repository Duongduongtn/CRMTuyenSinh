<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import { cn } from '@/lib/utils'
import { NO_VALUE } from '@/lib/format'

defineOptions({ inheritAttrs: false })

interface Option {
  label: string
  value: string | number
}

const props = withDefaults(
  defineProps<{
    modelValue?: string | number | null
    label?: string
    error?: string
    hint?: string
    required?: boolean
    placeholder?: string
    options?: Option[]
  }>(),
  { placeholder: NO_VALUE },
)
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const attrs = useAttrs()

const inputId = computed(() => (attrs.id as string) || `sel-${Math.random().toString(36).slice(2, 8)}`)
</script>

<template>
  <div class="flex w-full flex-col gap-1.5">
    <label v-if="label" :for="inputId" class="text-[13px] font-medium text-ink-60 tracking-tight">
      {{ label }}
      <span v-if="required" class="text-danger" aria-hidden="true">*</span>
    </label>
    <div
      :class="
        cn(
          'relative rounded-md border bg-paper transition-colors',
          error ? 'border-danger' : 'border-line-base focus-within:border-brand-600',
        )
      "
    >
      <select
        :id="inputId"
        :value="modelValue ?? ''"
        v-bind="attrs"
        class="h-10 w-full appearance-none bg-transparent px-3 pr-9 text-sm text-ink outline-none"
        @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
      >
        <option v-if="placeholder" value="">{{ placeholder }}</option>
        <option v-for="opt in options" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        <slot />
      </select>
      <svg
        class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-40"
        viewBox="0 0 20 20"
        fill="none"
        aria-hidden="true"
      >
        <path d="M6 8l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </div>
    <p v-if="error" class="text-[12px] font-medium text-danger">{{ error }}</p>
    <p v-else-if="hint" class="text-[12px] text-ink-40">{{ hint }}</p>
  </div>
</template>
