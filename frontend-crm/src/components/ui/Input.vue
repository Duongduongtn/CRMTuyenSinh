<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import { cn } from '@/lib/utils'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    modelValue?: string | number | null
    label?: string
    hint?: string
    error?: string
    required?: boolean
    type?: string
    iconLeft?: boolean
    iconRight?: boolean
  }>(),
  { type: 'text' },
)
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const attrs = useAttrs()

const inputId = computed(() => (attrs.id as string) || `inp-${Math.random().toString(36).slice(2, 8)}`)

const wrapperClasses = computed(() =>
  cn(
    'group relative flex items-center rounded-md border bg-paper transition-colors duration-200',
    props.error
      ? 'border-danger focus-within:border-danger'
      : 'border-line-base focus-within:border-brand-600',
  ),
)
</script>

<template>
  <div class="flex w-full flex-col gap-1.5">
    <label v-if="label" :for="inputId" class="text-[13px] font-medium text-ink-60 tracking-tight">
      {{ label }}
      <span v-if="required" class="text-danger" aria-hidden="true">*</span>
    </label>
    <div :class="wrapperClasses">
      <span v-if="iconLeft" class="absolute left-3 flex h-full items-center text-ink-40">
        <slot name="iconLeft" />
      </span>
      <input
        :id="inputId"
        :type="type"
        :value="modelValue ?? ''"
        v-bind="attrs"
        :class="
          cn(
            'h-10 w-full bg-transparent px-3 text-sm text-ink placeholder:text-ink-40 outline-none',
            iconLeft && 'pl-10',
            iconRight && 'pr-10',
          )
        "
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
      <span v-if="iconRight" class="absolute right-3 flex h-full items-center text-ink-40">
        <slot name="iconRight" />
      </span>
    </div>
    <p v-if="error" class="text-[12px] font-medium text-danger">{{ error }}</p>
    <p v-else-if="hint" class="text-[12px] text-ink-40">{{ hint }}</p>
  </div>
</template>
