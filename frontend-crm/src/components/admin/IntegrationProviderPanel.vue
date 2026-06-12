<script setup lang="ts">
/**
 * Panel quản lý khóa tích hợp cho 1 provider (Casso / FB Lead Ads).
 *
 * Self-contained: load fetchIntegrations, lọc theo prop `provider`, render form
 * key + save bar nội bộ. Reuse được trong Settings.vue (gom 1 entry sidebar duy
 * nhất) hoặc bất kỳ page nào khác.
 */
import { computed, ref } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import {
  Key,
  Eye,
  EyeSlash,
  FloppyDisk,
  Check,
  Warning,
  ArrowsClockwise,
} from '@/lib/icons'
import Button from '@/components/ui/Button.vue'
import Spinner from '@/components/ui/Spinner.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import {
  fetchIntegrations,
  updateIntegration,
  type IntegrationItem,
  type IntegrationSource,
} from '@/api/integrations'

const props = defineProps<{
  provider: 'casso' | 'fb'
}>()

const queryClient = useQueryClient()
const drafts = ref<Record<string, string>>({})
const reveal = ref<Record<string, boolean>>({})

const integrationsQuery = useQuery({
  queryKey: ['integrations'],
  queryFn: fetchIntegrations,
  staleTime: 30_000,
})

const items = computed<IntegrationItem[]>(() => {
  const data = integrationsQuery.data.value
  if (!data) return []
  return data[props.provider] ?? []
})

const hasUnsaved = computed(() => Object.keys(drafts.value).length > 0)
const changedCount = computed(() => Object.keys(drafts.value).length)

function getDraftValue(key: string): string {
  return drafts.value[key] ?? ''
}

function setDraftValue(key: string, value: string) {
  drafts.value = { ...drafts.value, [key]: value }
}

function clearDraft(key: string) {
  const next = { ...drafts.value }
  delete next[key]
  drafts.value = next
}

function toggleReveal(key: string) {
  reveal.value[key] = !reveal.value[key]
}

function isRevealed(key: string): boolean {
  return !!reveal.value[key]
}

function sourceLabel(source: IntegrationSource): { text: string; tone: string } {
  switch (source) {
    case 'db':
      return { text: 'Đã lưu DB', tone: 'success' }
    case 'env':
      return { text: 'Đang chạy bằng ENV', tone: 'info' }
    default:
      return { text: 'Chưa có giá trị', tone: 'muted' }
  }
}

function formatUpdatedAt(value: string | null): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const saveMutation = useMutation({
  mutationFn: (payload: Record<string, string>) =>
    updateIntegration(props.provider, payload),
  onSuccess: async () => {
    drafts.value = {}
    await queryClient.invalidateQueries({ queryKey: ['integrations'] })
    toast.success('Đã lưu khóa tích hợp.')
  },
  onError: () => {
    toast.error('Lưu thất bại, vui lòng thử lại.')
  },
})

function onSave() {
  if (!hasUnsaved.value) return
  saveMutation.mutate({ ...drafts.value })
}

function onRefresh() {
  integrationsQuery.refetch()
}

function onDiscard() {
  drafts.value = {}
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <div v-if="integrationsQuery.isLoading.value" class="flex items-center justify-center py-12">
      <Spinner />
    </div>

    <ErrorState
      v-else-if="integrationsQuery.isError.value"
      title="Không tải được khóa tích hợp"
      :description="(integrationsQuery.error.value as Error)?.message ?? 'Vui lòng thử lại.'"
      @retry="onRefresh"
    />

    <template v-else>
      <div class="flex items-center justify-end">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 text-caption text-ink-60 hover:text-ink transition-colors"
          @click="onRefresh"
        >
          <ArrowsClockwise :size="14" />
          Tải lại
        </button>
      </div>

      <article
        v-for="item in items"
        :key="item.key"
        class="rounded-xl border border-line-base bg-paper px-5 py-4 transition-colors duration-200 hover:border-line-strong/30"
      >
        <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div class="flex flex-col gap-1">
            <label
              :for="`int-${provider}-${item.key}`"
              class="flex items-center gap-2 text-body font-medium text-ink"
            >
              <Key :size="14" class="text-ink-40" />
              {{ item.label }}
              <span v-if="item.sensitive" class="text-caption text-ink-40 font-normal">(bí mật)</span>
            </label>
            <p class="text-caption text-ink-60 leading-snug">{{ item.help_text }}</p>
          </div>
          <div class="flex flex-col items-start gap-1 sm:items-end shrink-0">
            <span
              :class="[
                'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-caption font-medium',
                sourceLabel(item.source).tone === 'success' && 'bg-success-soft text-success',
                sourceLabel(item.source).tone === 'info' && 'bg-info-soft text-info',
                sourceLabel(item.source).tone === 'muted' && 'bg-paper-alt text-ink-60',
              ]"
            >
              <Check v-if="item.source === 'db'" :size="12" weight="bold" />
              <Warning v-else-if="item.source === 'empty'" :size="12" weight="duotone" />
              {{ sourceLabel(item.source).text }}
            </span>
            <span v-if="item.updated_at" class="text-caption text-ink-40">
              {{ item.updated_by_username || 'Hệ thống' }} · {{ formatUpdatedAt(item.updated_at) }}
            </span>
          </div>
        </div>

        <div class="mt-3 flex items-stretch gap-2">
          <div
            :class="[
              'flex flex-1 items-center rounded-md border bg-paper transition-colors duration-200',
              getDraftValue(item.key) !== ''
                ? 'border-brand-400 ring-1 ring-brand-100'
                : 'border-line-base focus-within:border-brand-600',
            ]"
          >
            <input
              :id="`int-${provider}-${item.key}`"
              :type="!item.sensitive || isRevealed(item.key) ? 'text' : 'password'"
              :value="getDraftValue(item.key)"
              :placeholder="item.has_value ? item.masked : 'Nhập giá trị mới'"
              spellcheck="false"
              autocomplete="off"
              autocapitalize="off"
              class="h-10 w-full bg-transparent px-3 font-mono text-body text-ink placeholder:text-ink-40 placeholder:font-sans outline-none"
              @input="setDraftValue(item.key, ($event.target as HTMLInputElement).value)"
            />
            <button
              v-if="item.sensitive"
              type="button"
              :aria-label="isRevealed(item.key) ? 'Ẩn giá trị' : 'Hiện giá trị'"
              class="flex h-10 w-10 items-center justify-center text-ink-40 hover:text-ink transition-colors"
              @click="toggleReveal(item.key)"
            >
              <component :is="isRevealed(item.key) ? EyeSlash : Eye" :size="16" />
            </button>
          </div>
          <button
            v-if="getDraftValue(item.key) !== ''"
            type="button"
            class="inline-flex items-center px-3 text-caption font-medium text-ink-60 hover:text-ink transition-colors"
            @click="clearDraft(item.key)"
          >
            Hủy sửa
          </button>
        </div>

        <p v-if="!item.has_value && getDraftValue(item.key) === ''" class="mt-2 text-caption text-ink-40 italic">
          Để trống nếu chưa có khóa từ nhà cung cấp.
        </p>
      </article>

      <div v-if="items.length === 0" class="rounded-md border border-dashed border-line-base px-5 py-8 text-center text-body text-ink-40">
        Không có khóa cấu hình cho dịch vụ này.
      </div>

      <!-- SAVE BAR (sticky bottom in panel context) -->
      <div
        v-if="hasUnsaved || saveMutation.isError.value"
        class="sticky bottom-0 flex flex-col gap-3 rounded-xl border border-brand-200 bg-paper px-5 py-4 shadow-[0_4px_24px_-12px_rgba(20,83,45,0.15)] sm:flex-row sm:items-center sm:justify-between animate-slide-up motion-reduce:animate-none"
      >
        <div class="flex flex-col gap-0.5">
          <p class="text-body font-medium text-ink">
            <span class="text-brand-800">{{ changedCount }}</span>
            khóa chưa lưu
          </p>
          <p v-if="saveMutation.isError.value" class="text-caption text-danger">
            {{ (saveMutation.error.value as Error)?.message ?? 'Lưu thất bại, vui lòng thử lại.' }}
          </p>
          <p v-else class="text-caption text-ink-60">
            Sau khi lưu, dịch vụ pickup giá trị mới trong vòng 60 giây.
          </p>
        </div>
        <div class="flex gap-2">
          <Button variant="ghost" size="md" @click="onDiscard">
            Hủy
          </Button>
          <Button
            :loading="saveMutation.isPending.value"
            :disabled="!hasUnsaved"
            variant="accent"
            @click="onSave"
          >
            <FloppyDisk :size="16" weight="duotone" />
            Lưu thay đổi
          </Button>
        </div>
      </div>
    </template>
  </div>
</template>
