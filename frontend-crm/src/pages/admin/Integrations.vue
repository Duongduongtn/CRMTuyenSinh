<script setup lang="ts">
/**
 * Tab quản lý khóa tích hợp ngoài.
 *
 * Scope chốt 2026-06-11: chỉ Casso + FB Lead Ads. ZNS + SMTP đã bỏ.
 * User paste key qua form, BE encrypt Fernet lưu DB. Cache TTL 60s.
 * Audit log mỗi PUT, KHÔNG log plaintext.
 */
import { computed, ref, watch } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import {
  PlugsConnected,
  Bank,
  FacebookLogo,
  Key,
  Eye,
  EyeSlash,
  FloppyDisk,
  ShieldCheck,
  Info,
  Check,
  Warning,
  ArrowsClockwise,
} from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Spinner from '@/components/ui/Spinner.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import {
  fetchIntegrations,
  updateIntegration,
  type IntegrationItem,
  type IntegrationSource,
} from '@/api/integrations'

type ProviderKey = 'casso' | 'fb'

interface ProviderMeta {
  key: ProviderKey
  label: string
  icon: typeof Bank
  description: string
}

const PROVIDERS: ProviderMeta[] = [
  {
    key: 'casso',
    label: 'Casso',
    icon: Bank,
    description: 'Đối soát QR đặt cọc: verify HMAC webhook + gọi API kiểm tra giao dịch.',
  },
  {
    key: 'fb',
    label: 'Facebook Lead Ads',
    icon: FacebookLogo,
    description: 'Pull lead tự động từ Meta Ads Manager. Defer tới khi chạy quảng cáo Facebook.',
  },
]

const queryClient = useQueryClient()
const activeProvider = ref<ProviderKey>('casso')

// Map local: per-key edit value. Khác masked = đã sửa.
const drafts = ref<Record<string, Record<string, string>>>({ casso: {}, fb: {} })
const reveal = ref<Record<string, boolean>>({})

const integrationsQuery = useQuery({
  queryKey: ['integrations'],
  queryFn: fetchIntegrations,
  staleTime: 30_000,
})

const currentProvider = computed(() =>
  PROVIDERS.find((p) => p.key === activeProvider.value) ?? PROVIDERS[0],
)

const items = computed<IntegrationItem[]>(() => {
  const data = integrationsQuery.data.value
  if (!data) return []
  return data[activeProvider.value] ?? []
})

// Save thành công thì reset draft CHỈ của provider vừa save, tránh mất gõ
// đang dở ở tab khác khi user chuyển qua chuyển lại.
const lastSavedProvider = ref<ProviderKey | null>(null)
watch(
  () => integrationsQuery.data.value,
  () => {
    const p = lastSavedProvider.value
    if (p && drafts.value[p]) {
      drafts.value[p] = {}
      lastSavedProvider.value = null
    }
  },
)

const hasUnsaved = computed(() => {
  const draft = drafts.value[activeProvider.value] ?? {}
  return Object.keys(draft).length > 0
})

const changedCount = computed(() => Object.keys(drafts.value[activeProvider.value] ?? {}).length)

function getDraftValue(key: string): string {
  return drafts.value[activeProvider.value]?.[key] ?? ''
}

function setDraftValue(key: string, value: string) {
  const provider = activeProvider.value
  if (!drafts.value[provider]) drafts.value[provider] = {}
  drafts.value[provider][key] = value
}

function clearDraft(key: string) {
  delete drafts.value[activeProvider.value][key]
}

function toggleReveal(key: string) {
  const cacheKey = `${activeProvider.value}.${key}`
  reveal.value[cacheKey] = !reveal.value[cacheKey]
}

function isRevealed(key: string): boolean {
  return !!reveal.value[`${activeProvider.value}.${key}`]
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
  mutationFn: async (payload: { provider: ProviderKey; data: Record<string, string> }) =>
    updateIntegration(payload.provider, payload.data),
  onSuccess: async (_data, variables) => {
    lastSavedProvider.value = variables.provider
    await queryClient.invalidateQueries({ queryKey: ['integrations'] })
  },
})

function onSave() {
  const provider = activeProvider.value
  const payload = drafts.value[provider]
  if (!payload || Object.keys(payload).length === 0) return
  saveMutation.mutate({ provider, data: { ...payload } })
}

function onRefresh() {
  integrationsQuery.refetch()
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 pb-12 sm:px-6">
    <!-- HEADER -->
    <header class="flex flex-col gap-6 pt-6 sm:flex-row sm:items-start sm:justify-between">
      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-2 text-overline uppercase text-brand-700 font-semibold">
          <ShieldCheck :size="14" weight="duotone" />
          Cấu hình hệ thống
        </div>
        <h1 class="text-display font-semibold tracking-tight text-ink">
          Khóa tích hợp ngoài
        </h1>
        <p class="max-w-2xl text-body text-ink-60">
          Quản lý webhook secret và API key cho dịch vụ bên ngoài. Khóa được mã hóa Fernet
          trước khi lưu cơ sở dữ liệu, runtime đọc qua cache TTL 60 giây, không cần
          khởi động lại dịch vụ sau khi cập nhật.
        </p>
      </div>
      <div class="flex flex-col items-start gap-2 sm:items-end">
        <span class="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-caption font-medium text-brand-800">
          <PlugsConnected :size="14" weight="duotone" />
          {{ PROVIDERS.length }} dịch vụ đang dùng
        </span>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 text-caption text-ink-60 hover:text-ink transition-colors"
          @click="onRefresh"
        >
          <ArrowsClockwise :size="14" />
          Tải lại
        </button>
      </div>
    </header>

    <!-- NOTICE: scope thay đổi 2026-06-11 -->
    <Card class="border-warning/40 bg-warning-soft/60 px-5 py-4">
      <div class="flex items-start gap-3">
        <Info :size="20" weight="duotone" class="mt-0.5 shrink-0 text-warning" />
        <div class="text-body leading-relaxed text-ink-60">
          <p class="font-medium text-ink">Thay đổi phạm vi cấu hình tháng 06/2026</p>
          <p class="mt-1">
            Tạm ngưng tích hợp <span class="font-medium text-ink">Zalo ZNS</span> và
            <span class="font-medium text-ink">Email SMTP</span>. Đăng nhập học viên dùng
            số điện thoại kết hợp 6 ký tự cuối CCCD. Đổi mật khẩu nhân viên thực hiện
            trực tiếp trong CRM, không gửi email tự động.
          </p>
        </div>
      </div>
    </Card>

    <!-- TAB SWITCHER -->
    <nav role="tablist" aria-label="Chọn dịch vụ tích hợp" class="-mb-px flex gap-1 border-b border-line-soft">
      <button
        v-for="prov in PROVIDERS"
        :key="prov.key"
        type="button"
        :role="'tab'"
        :aria-selected="activeProvider === prov.key"
        :class="[
          'inline-flex items-center gap-2 px-4 py-3 text-body font-medium transition-colors duration-200',
          activeProvider === prov.key
            ? 'text-brand-800 border-b-2 border-brand-700'
            : 'text-ink-60 hover:text-ink border-b-2 border-transparent',
        ]"
        @click="activeProvider = prov.key"
      >
        <component :is="prov.icon" :size="18" :weight="activeProvider === prov.key ? 'duotone' : 'regular'" />
        {{ prov.label }}
      </button>
    </nav>

    <!-- LOADING / ERROR / CONTENT -->
    <div v-if="integrationsQuery.isLoading.value" class="flex items-center justify-center py-16">
      <Spinner />
    </div>

    <ErrorState
      v-else-if="integrationsQuery.isError.value"
      title="Không tải được khóa tích hợp"
      :description="(integrationsQuery.error.value as Error)?.message ?? 'Vui lòng thử lại.'"
      @retry="onRefresh"
    />

    <section v-else class="flex flex-col gap-6 animate-fade-in motion-reduce:animate-none">
      <!-- Provider intro -->
      <div class="flex flex-col gap-1">
        <div class="flex items-center gap-2 text-headline font-semibold text-ink">
          <component :is="currentProvider.icon" :size="22" weight="duotone" class="text-brand-700" />
          {{ currentProvider.label }}
        </div>
        <p class="text-body text-ink-60">{{ currentProvider.description }}</p>
      </div>

      <!-- KEYS LIST -->
      <div class="flex flex-col gap-3">
        <article
          v-for="item in items"
          :key="item.key"
          class="rounded-xl border border-line-base bg-paper px-5 py-4 transition-colors duration-200 hover:border-line-strong/30"
        >
          <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div class="flex flex-col gap-1">
              <label
                :for="`int-${activeProvider}-${item.key}`"
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
                :id="`int-${activeProvider}-${item.key}`"
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
      </div>

      <!-- SAVE BAR -->
      <div
        v-if="hasUnsaved || saveMutation.isError.value"
        class="sticky bottom-0 flex flex-col gap-3 rounded-xl border border-brand-200 bg-paper px-5 py-4 shadow-[0_4px_24px_-12px_rgba(20,83,45,0.15)] sm:flex-row sm:items-center sm:justify-between animate-slide-up motion-reduce:animate-none"
      >
        <div class="flex flex-col gap-0.5">
          <p class="text-body font-medium text-ink">
            <span class="text-brand-800">{{ changedCount }}</span>
            khóa chưa lưu cho {{ currentProvider.label }}
          </p>
          <p v-if="saveMutation.isError.value" class="text-caption text-danger">
            {{ (saveMutation.error.value as Error)?.message ?? 'Lưu thất bại, vui lòng thử lại.' }}
          </p>
          <p v-else class="text-caption text-ink-60">
            Sau khi lưu, dịch vụ pickup giá trị mới trong vòng 60 giây.
          </p>
        </div>
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

      <transition
        enter-active-class="transition-opacity duration-300"
        leave-active-class="transition-opacity duration-300"
        enter-from-class="opacity-0"
        leave-to-class="opacity-0"
      >
        <div
          v-if="saveMutation.isSuccess.value && !hasUnsaved"
          class="inline-flex items-center gap-2 self-start rounded-full border border-success/30 bg-success-soft px-3 py-1.5 text-caption font-medium text-success"
        >
          <Check :size="14" weight="bold" />
          Đã lưu thành công
        </div>
      </transition>
    </section>
  </div>
</template>
