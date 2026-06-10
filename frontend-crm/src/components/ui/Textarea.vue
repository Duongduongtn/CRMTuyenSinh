<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import { cn } from '@/lib/utils'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    modelValue?: string | null
    label?: string
    error?: string
    hint?: string
    rows?: number
    required?: boolean
  }>(),
  { rows: 3 },
)
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const attrs = useAttrs()

const inputId = computed(() => (attrs.id as string) || `txt-${Math.random().toString(36).slice(2, 8)}`)
</script>

<template>
  <div class="flex w-full flex-col gap-1.5">
    <label v-if="label" :for="inputId" class="text-[13px] font-medium text-ink-60 tracking-tight">
      {{ label }}
      <span v-if="required" class="text-danger" aria-hidden="true">*</span>
    </label>
    <textarea
      :id="inputId"
      :rows="rows"
      :value="modelValue ?? ''"
      v-bind="attrs"
      :class="
        cn(
          'w-full rounded-md border bg-paper px-3 py-2 text-sm text-ink placeholder:text-ink-40 outline-none transition-colors',
          error
            ? 'border-danger focus:border-danger'
            : 'border-line-base focus:border-brand-600',
        )
      "
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
    ></textarea>
    <p v-if="error" class="text-[12px] font-medium text-danger">{{ error }}</p>
    <p v-else-if="hint" class="text-[12px] text-ink-40">{{ hint }}</p>
  </div>
</template>
