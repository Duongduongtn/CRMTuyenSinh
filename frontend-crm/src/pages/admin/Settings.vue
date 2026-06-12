<script setup lang="ts">
/**
 * Trang Cài đặt: chỉnh full SiteSettings (brand, contact, social, bank, SEO, stats).
 *
 * 6 section ngang dạng tab, mỗi section là 1 nhóm field. Edit local draft → save
 * bulk qua PATCH /api/admin/site-settings/. Sticky save bar hiện khi có thay đổi.
 *
 * Ảnh (logo/favicon/og_image) tạm thời chỉnh trong Django admin tới khi build
 * upload UI: page hiển thị note rõ ràng.
 */
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import {
  ShieldCheck,
  Gear,
  Bank,
  Storefront,
  Phone,
  ShareNetwork,
  Globe,
  ChartBar,
  FloppyDisk,
  ArrowsClockwise,
  Check,
  Warning,
  FacebookLogo,
  PlugsConnected,
} from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Textarea from '@/components/ui/Textarea.vue'
import Select from '@/components/ui/Select.vue'
import Spinner from '@/components/ui/Spinner.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import IntegrationProviderPanel from '@/components/admin/IntegrationProviderPanel.vue'
import BrandImageUpload from '@/components/admin/BrandImageUpload.vue'
import {
  fetchSiteSettingsAdmin,
  updateSiteSettingsAdmin,
  type SiteSettingsAdmin,
  type SiteSettingsAdminPatch,
} from '@/api/siteSettings'

type SectionKey =
  | 'bank'
  | 'brand'
  | 'contact'
  | 'social'
  | 'seo'
  | 'stats'
  | 'casso'
  | 'fb'

interface SectionMeta {
  key: SectionKey
  label: string
  icon: typeof Bank
  description: string
}

const SECTIONS: SectionMeta[] = [
  // Nhóm Trung tâm: chỉnh SiteSettings (PATCH /api/admin/site-settings/).
  {
    key: 'bank',
    label: 'Ngân hàng',
    icon: Bank,
    description: 'Tài khoản nhận đặt cọc, dùng để sinh mã QR VietQR và đối soát Casso.',
  },
  {
    key: 'brand',
    label: 'Thương hiệu',
    icon: Storefront,
    description: 'Tên trung tâm, slogan, mô tả ngắn hiển thị trên header, footer, hóa đơn.',
  },
  {
    key: 'contact',
    label: 'Liên hệ',
    icon: Phone,
    description: 'Hotline, email, địa chỉ và giờ làm việc hiển thị trên website.',
  },
  {
    key: 'social',
    label: 'Mạng xã hội',
    icon: ShareNetwork,
    description: 'Đường dẫn Facebook, Zalo, YouTube, TikTok của trung tâm.',
  },
  {
    key: 'seo',
    label: 'SEO và pháp lý',
    icon: Globe,
    description: 'Meta tag mặc định cho FE public và thông tin pháp lý hiển thị footer.',
  },
  {
    key: 'stats',
    label: 'Số liệu hiển thị',
    icon: ChartBar,
    description: 'Số liệu trust strip hiển thị trên trang chủ. Cập nhật định kỳ thủ công.',
  },
  // Nhóm Tích hợp ngoài: chỉnh IntegrationCredential (PUT /api/admin/integrations/{provider}/).
  {
    key: 'casso',
    label: 'Casso',
    icon: PlugsConnected,
    description:
      'Đối soát QR đặt cọc tự động: verify HMAC webhook + gọi API Casso kiểm tra giao dịch.',
  },
  {
    key: 'fb',
    label: 'Facebook Lead Ads',
    icon: FacebookLogo,
    description:
      'Pull lead tự động từ Meta Ads Manager. Defer tới khi chạy quảng cáo Facebook.',
  },
]

const INTEGRATION_SECTIONS: ReadonlySet<SectionKey> = new Set(['casso', 'fb'])
const SITE_SETTINGS_SECTIONS_COUNT = SECTIONS.filter(
  (s) => !INTEGRATION_SECTIONS.has(s.key),
).length

// Danh sách ngân hàng VietQR phổ biến VN (NAPAS code).
const BANK_OPTIONS = [
  { value: 'BIDV', label: 'BIDV (Đầu tư và Phát triển)' },
  { value: 'VCB', label: 'VCB (Vietcombank)' },
  { value: 'VTB', label: 'VTB (Vietinbank)' },
  { value: 'TCB', label: 'TCB (Techcombank)' },
  { value: 'MB', label: 'MB (Quân đội)' },
  { value: 'ACB', label: 'ACB (Á Châu)' },
  { value: 'VPB', label: 'VPB (VPBank)' },
  { value: 'STB', label: 'STB (Sacombank)' },
  { value: 'TPB', label: 'TPB (TPBank)' },
  { value: 'HDB', label: 'HDB (HDBank)' },
  { value: 'OCB', label: 'OCB (Phương Đông)' },
  { value: 'AGRIBANK', label: 'AGRIBANK (Agribank)' },
  { value: 'SHB', label: 'SHB (Sài Gòn Hà Nội)' },
  { value: 'VIB', label: 'VIB (Quốc Tế)' },
  { value: 'EIB', label: 'EIB (Eximbank)' },
]

const queryClient = useQueryClient()
const activeSection = ref<SectionKey>('bank')
// focusedSection tách khỏi activeSection để hỗ trợ manual activation cho tab
// integration (Casso/FB). Khi user lướt Arrow qua tab integration, chỉ focus
// chứ KHÔNG render panel: tránh fire fetchIntegrations cho tới khi user thực
// sự muốn vào tab đó (Enter/Space hoặc click).
const focusedSection = ref<SectionKey>('bank')
// Invariant: focusedSection follow activeSection khi activeSection đổi từ
// nguồn programmatic (click "Quay lại để lưu", deep-link, mutation reset...).
// Khi user Arrow trên integration tab thì focusedSection lệch activeSection
// có chủ đích: watch không fire vì activeSection KHÔNG đổi.
watch(activeSection, (value) => {
  focusedSection.value = value
})
const draft = ref<SiteSettingsAdminPatch>({})

const settingsQuery = useQuery({
  queryKey: ['site-settings-admin'],
  queryFn: fetchSiteSettingsAdmin,
  staleTime: 30_000,
})

const current = computed<SiteSettingsAdmin | null>(
  () => settingsQuery.data.value ?? null,
)

// Helper: lấy giá trị hiển thị = draft (nếu đã sửa) > server.
function val<K extends keyof SiteSettingsAdminPatch>(key: K): string {
  const d = draft.value[key]
  if (d !== undefined) return String(d ?? '')
  const c = current.value
  if (!c) return ''
  return String(c[key] ?? '')
}

function setVal<K extends keyof SiteSettingsAdminPatch>(
  key: K,
  value: string,
) {
  draft.value = { ...draft.value, [key]: value }
}

function setNum<K extends keyof SiteSettingsAdminPatch>(
  key: K,
  value: string,
) {
  // Field stat_* là số nguyên dương. Empty → 0 để BE chấp nhận.
  const n = Number(value)
  draft.value = { ...draft.value, [key]: Number.isFinite(n) ? n : 0 }
}

const hasUnsaved = computed(() => Object.keys(draft.value).length > 0)
const changedCount = computed(() => Object.keys(draft.value).length)

const saveMutation = useMutation({
  mutationFn: (payload: SiteSettingsAdminPatch) =>
    updateSiteSettingsAdmin(payload),
  onSuccess: async () => {
    draft.value = {}
    await queryClient.invalidateQueries({ queryKey: ['site-settings-admin'] })
    toast.success('Đã lưu cấu hình.')
  },
  onError: () => {
    toast.error('Lưu thất bại, vui lòng thử lại.')
  },
})

function onSave() {
  if (!hasUnsaved.value) return
  saveMutation.mutate({ ...draft.value })
}

function onRefresh() {
  settingsQuery.refetch()
}

function onDiscard() {
  draft.value = {}
}

// Field nào trong draft thuộc section hiện tại?
// Nhóm Integration (casso/fb) KHÔNG có entry: save bar riêng nằm trong panel.
const SECTION_FIELDS: Partial<
  Record<SectionKey, (keyof SiteSettingsAdminPatch)[]>
> = {
  bank: ['bank_code', 'bank_account_number', 'bank_account_name'],
  brand: ['brand_name', 'brand_short_name', 'slogan', 'description'],
  contact: [
    'hotline',
    'hotline_display',
    'email',
    'address_line',
    'ward',
    'district',
    'city',
    'working_hours_text',
    'map_lat',
    'map_lng',
    'map_embed_url',
  ],
  social: [
    'facebook_url',
    'zalo_oa_id',
    'zalo_url',
    'youtube_url',
    'tiktok_url',
  ],
  seo: [
    'meta_title_default',
    'meta_description_default',
    'license_info',
    'company_full_name',
    'tax_code',
  ],
  stats: [
    'stat_students_count',
    'stat_pass_rate_percent',
    'stat_years_experience',
    'stat_practice_area_m2',
  ],
}

const sectionChangedCount = computed(() => {
  const fields = SECTION_FIELDS[activeSection.value] ?? []
  return fields.filter((f) => draft.value[f] !== undefined).length
})

const isIntegrationTab = computed(() =>
  INTEGRATION_SECTIONS.has(activeSection.value),
)

// Khi user nhảy sang tab integration với draft SiteSettings còn dirty, tìm tab
// site-settings ĐẦU TIÊN có thay đổi để jump back qua nút "Quay lại để lưu".
const firstDirtySiteSettingsSection = computed<SectionKey | null>(() => {
  for (const sec of SECTIONS) {
    if (INTEGRATION_SECTIONS.has(sec.key)) continue
    const fields = SECTION_FIELDS[sec.key] ?? []
    if (fields.some((f) => draft.value[f] !== undefined)) {
      return sec.key
    }
  }
  return null
})

const currentSection = computed(
  () => SECTIONS.find((s) => s.key === activeSection.value) ?? SECTIONS[0],
)

function isSectionDirty(key: SectionKey): boolean {
  const fields = SECTION_FIELDS[key] ?? []
  return fields.some((f) => draft.value[f] !== undefined)
}

// Chặn drop file ngoài drop-zone trong toàn page Settings: tránh browser
// navigate đi xem ảnh (mất state draft + tab). preventDefault dragover bắt
// buộc để event drop fire (nếu không default behavior là "cancel drop").
function preventGlobalDrop(event: DragEvent) {
  event.preventDefault()
}
onMounted(() => {
  window.addEventListener('dragover', preventGlobalDrop)
  window.addEventListener('drop', preventGlobalDrop)
})
onUnmounted(() => {
  window.removeEventListener('dragover', preventGlobalDrop)
  window.removeEventListener('drop', preventGlobalDrop)
})

function onTabClick(key: SectionKey) {
  focusedSection.value = key
  activeSection.value = key
}

// Keyboard nav theo WAI-ARIA APG Tabs pattern, hybrid automatic/manual:
// - Left Right Home End di chuyển focus.
// - Tab SiteSettings (render rẻ, no network): auto-activate khi focus.
// - Tab integration Casso/FB (mount IntegrationProviderPanel + fetch API): chỉ
//   focus, KHÔNG activate. User phải Enter / Space để activate.
// - Hành vi tránh: fire 1 request fetchIntegrations mỗi lần Arrow Right qua tab
//   integration (lãng phí + nháy UI loading).
function onTabKeydown(event: KeyboardEvent, currentIndex: number) {
  if (event.key === 'Enter' || event.key === ' ') {
    // Luôn preventDefault để Space không scroll page khi tab đang focus, dù
    // focused === active (no-op activation). Khớp pattern button native.
    event.preventDefault()
    if (focusedSection.value !== activeSection.value) {
      activeSection.value = focusedSection.value
    }
    return
  }
  const total = SECTIONS.length
  let nextIndex = -1
  if (event.key === 'ArrowRight') {
    nextIndex = (currentIndex + 1) % total
  } else if (event.key === 'ArrowLeft') {
    nextIndex = (currentIndex - 1 + total) % total
  } else if (event.key === 'Home') {
    nextIndex = 0
  } else if (event.key === 'End') {
    nextIndex = total - 1
  } else {
    return
  }
  event.preventDefault()
  const nextKey = SECTIONS[nextIndex].key
  focusedSection.value = nextKey
  if (!INTEGRATION_SECTIONS.has(nextKey)) {
    activeSection.value = nextKey
  }
  nextTick(() => {
    const el = document.getElementById(`tab-${nextKey}`)
    el?.focus()
  })
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
          Cài đặt trung tâm
        </h1>
        <p class="max-w-2xl text-body text-ink-60">
          Cập nhật thương hiệu, liên hệ, mạng xã hội, tài khoản ngân hàng nhận đặt cọc,
          số liệu hiển thị và khóa tích hợp Casso/Facebook Lead Ads. Thay đổi áp dụng
          tức thì cho website công khai và CRM nội bộ, không cần khởi động lại dịch vụ.
        </p>
      </div>
      <div class="flex flex-col items-start gap-2 sm:items-end">
        <span class="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-caption font-medium text-brand-800">
          <Gear :size="14" weight="duotone" />
          {{ SITE_SETTINGS_SECTIONS_COUNT }} cấu hình · {{ INTEGRATION_SECTIONS.size }} tích hợp
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

    <!-- TAB SWITCHER (WAI-ARIA APG Tabs pattern) -->
    <!-- Hint ẩn cho screen reader: tab integration cần Enter/Space để activate. -->
    <span id="manual-tab-hint" class="sr-only">Nhấn Enter hoặc phím cách để tải khóa tích hợp</span>
    <div role="tablist" aria-label="Chọn nhóm cấu hình" class="-mb-px flex flex-wrap items-center gap-1 border-b border-line-soft">
      <template v-for="(sec, index) in SECTIONS" :key="sec.key">
        <!-- Divider phân nhóm Cấu hình và Tích hợp (trước tab integration đầu tiên). -->
        <span
          v-if="index > 0 && INTEGRATION_SECTIONS.has(sec.key) && !INTEGRATION_SECTIONS.has(SECTIONS[index - 1].key)"
          class="mx-2 h-6 w-px self-center bg-line-base"
          aria-hidden="true"
        />
        <button
          type="button"
          role="tab"
          :id="`tab-${sec.key}`"
          :aria-selected="activeSection === sec.key"
          :aria-controls="`panel-${sec.key}`"
          :aria-describedby="INTEGRATION_SECTIONS.has(sec.key) ? 'manual-tab-hint' : undefined"
          :tabindex="focusedSection === sec.key ? 0 : -1"
          :class="[
            'inline-flex items-center gap-2 px-4 py-3 text-body font-medium transition-colors duration-200 outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 focus-visible:rounded-sm',
            activeSection === sec.key
              ? 'text-brand-800 border-b-2 border-brand-700'
              : focusedSection === sec.key && INTEGRATION_SECTIONS.has(sec.key)
                ? 'text-brand-700 border-b-2 border-dashed border-brand-400'
                : 'text-ink-60 hover:text-ink border-b-2 border-transparent',
          ]"
          @click="onTabClick(sec.key)"
          @keydown="onTabKeydown($event, index)"
        >
          <component :is="sec.icon" :size="18" :weight="activeSection === sec.key ? 'duotone' : 'regular'" />
          {{ sec.label }}
          <template v-if="isSectionDirty(sec.key)">
            <span
              class="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-brand-600"
              aria-hidden="true"
            />
            <span class="sr-only">, có thay đổi chưa lưu</span>
          </template>
        </button>
      </template>
    </div>

    <!-- LOADING / ERROR -->
    <div v-if="settingsQuery.isLoading.value" class="flex items-center justify-center py-16">
      <Spinner />
    </div>

    <ErrorState
      v-else-if="settingsQuery.isError.value"
      title="Không tải được cấu hình"
      :description="(settingsQuery.error.value as Error)?.message ?? 'Vui lòng thử lại.'"
      @retry="onRefresh"
    />

    <section v-else-if="current" class="flex flex-col gap-6 animate-fade-in motion-reduce:animate-none">
      <!-- TABPANEL: nội dung 1 tab. KHÔNG tabindex=0 vì panel chứa focusable
           children (Input/Select/Textarea): WAI-ARIA APG khuyến cáo bỏ tab
           stop thừa khi panel đã có focusable content. -->
      <div
        :id="`panel-${activeSection}`"
        role="tabpanel"
        :aria-labelledby="`tab-${activeSection}`"
        class="flex flex-col gap-6"
      >
      <!-- Section intro -->
      <div class="flex flex-col gap-1">
        <div class="flex items-center gap-2 text-headline font-semibold text-ink">
          <component :is="currentSection.icon" :size="22" weight="duotone" class="text-brand-700" />
          {{ currentSection.label }}
        </div>
        <p class="text-body text-ink-60">{{ currentSection.description }}</p>
      </div>

      <!-- SECTION: BANK -->
      <Card v-if="activeSection === 'bank'" class="space-y-5">
        <Select
          label="Ngân hàng"
          :model-value="val('bank_code')"
          :placeholder="'-- Chọn ngân hàng --'"
          :options="BANK_OPTIONS"
          @update:model-value="setVal('bank_code', $event)"
        />
        <Input
          label="Số tài khoản nhận"
          :model-value="val('bank_account_number')"
          placeholder="Ví dụ: 12345678901234"
          inputmode="numeric"
          hint="Số TK liên kết với Casso để webhook đối soát tự động."
          @update:model-value="setVal('bank_account_number', $event)"
        />
        <Input
          label="Tên chủ tài khoản"
          :model-value="val('bank_account_name')"
          placeholder="Ví dụ: TRUNG TAM DAO TAO LAI XE"
          hint="Viết hoa, không dấu, đúng tên trên CMND chủ tài khoản. QR sẽ hiển thị tên này."
          @update:model-value="setVal('bank_account_name', $event)"
        />
      </Card>

      <!-- SECTION: BRAND -->
      <div v-else-if="activeSection === 'brand'" class="space-y-5">
        <!-- 3 ảnh brand: logo + favicon + og_image. Mỗi ảnh 1 Card riêng để
             visual tách bạch (spec khác nhau). Upload qua API multipart, KHÔNG
             gộp PATCH JSON (file binary). -->
        <Card class="space-y-3">
          <BrandImageUpload
            field="logo"
            :current-url="current?.logo_url ?? ''"
            @uploaded="(d) => queryClient.setQueryData(['site-settings-admin'], d)"
          />
        </Card>
        <Card class="space-y-3">
          <BrandImageUpload
            field="favicon"
            :current-url="current?.favicon_url ?? ''"
            @uploaded="(d) => queryClient.setQueryData(['site-settings-admin'], d)"
          />
        </Card>
        <Card class="space-y-3">
          <BrandImageUpload
            field="og_image"
            :current-url="current?.og_image_url ?? ''"
            @uploaded="(d) => queryClient.setQueryData(['site-settings-admin'], d)"
          />
        </Card>
      </div>

      <Card v-if="activeSection === 'brand'" class="space-y-5">
        <Input
          label="Tên trung tâm"
          required
          :model-value="val('brand_name')"
          hint="Tên đầy đủ hiển thị header, footer, email, hóa đơn."
          @update:model-value="setVal('brand_name', $event)"
        />
        <Input
          label="Tên viết tắt"
          :model-value="val('brand_short_name')"
          placeholder="VD: ĐA, ABC"
          hint="2-3 ký tự, dùng cho logo text khi chưa có logo ảnh."
          @update:model-value="setVal('brand_short_name', $event)"
        />
        <Input
          label="Slogan"
          :model-value="val('slogan')"
          @update:model-value="setVal('slogan', $event)"
        />
        <Textarea
          label="Mô tả ngắn"
          :rows="3"
          :model-value="val('description')"
          hint="2-3 câu mô tả trung tâm, dùng làm meta description mặc định."
          @update:model-value="setVal('description', $event)"
        />
      </Card>

      <!-- SECTION: CONTACT -->
      <Card v-else-if="activeSection === 'contact'" class="space-y-5">
        <div class="grid gap-5 sm:grid-cols-2">
          <Input
            label="Hotline (định dạng máy)"
            :model-value="val('hotline')"
            placeholder="0900000000"
            inputmode="tel"
            hint="Không dấu chấm, không khoảng trắng."
            @update:model-value="setVal('hotline', $event)"
          />
          <Input
            label="Hotline (hiển thị)"
            :model-value="val('hotline_display')"
            placeholder="0900.000.000"
            @update:model-value="setVal('hotline_display', $event)"
          />
        </div>
        <Input
          label="Email"
          type="email"
          :model-value="val('email')"
          @update:model-value="setVal('email', $event)"
        />
        <Input
          label="Địa chỉ"
          :model-value="val('address_line')"
          @update:model-value="setVal('address_line', $event)"
        />
        <div class="grid gap-5 sm:grid-cols-3">
          <Input
            label="Phường / Xã"
            :model-value="val('ward')"
            @update:model-value="setVal('ward', $event)"
          />
          <Input
            label="Quận / Huyện"
            :model-value="val('district')"
            @update:model-value="setVal('district', $event)"
          />
          <Input
            label="Tỉnh / Thành phố"
            :model-value="val('city')"
            @update:model-value="setVal('city', $event)"
          />
        </div>
        <Input
          label="Giờ làm việc"
          :model-value="val('working_hours_text')"
          @update:model-value="setVal('working_hours_text', $event)"
        />
        <div class="grid gap-5 sm:grid-cols-2">
          <Input
            label="Vĩ độ (lat)"
            :model-value="val('map_lat')"
            placeholder="10.7626"
            inputmode="decimal"
            @update:model-value="setVal('map_lat', $event)"
          />
          <Input
            label="Kinh độ (lng)"
            :model-value="val('map_lng')"
            placeholder="106.6602"
            inputmode="decimal"
            @update:model-value="setVal('map_lng', $event)"
          />
        </div>
        <Input
          label="Google Maps embed URL"
          :model-value="val('map_embed_url')"
          placeholder="https://www.google.com/maps/embed?pb=..."
          hint="Vào Google Maps → Share → Embed a map → copy src của iframe."
          @update:model-value="setVal('map_embed_url', $event)"
        />
      </Card>

      <!-- SECTION: SOCIAL -->
      <Card v-else-if="activeSection === 'social'" class="space-y-5">
        <Input
          label="Facebook"
          type="url"
          :model-value="val('facebook_url')"
          placeholder="https://facebook.com/..."
          @update:model-value="setVal('facebook_url', $event)"
        />
        <div class="grid gap-5 sm:grid-cols-2">
          <Input
            label="Zalo OA ID"
            :model-value="val('zalo_oa_id')"
            placeholder="VD: 123456789"
            @update:model-value="setVal('zalo_oa_id', $event)"
          />
          <Input
            label="Zalo OA URL"
            type="url"
            :model-value="val('zalo_url')"
            placeholder="https://zalo.me/..."
            @update:model-value="setVal('zalo_url', $event)"
          />
        </div>
        <Input
          label="YouTube"
          type="url"
          :model-value="val('youtube_url')"
          placeholder="https://youtube.com/@..."
          @update:model-value="setVal('youtube_url', $event)"
        />
        <Input
          label="TikTok"
          type="url"
          :model-value="val('tiktok_url')"
          placeholder="https://tiktok.com/@..."
          @update:model-value="setVal('tiktok_url', $event)"
        />
      </Card>

      <!-- SECTION: SEO + LEGAL -->
      <Card v-else-if="activeSection === 'seo'" class="space-y-5">
        <Input
          label="Tiêu đề SEO mặc định"
          :model-value="val('meta_title_default')"
          hint="Tối đa 70 ký tự. Hiển thị trên tab trình duyệt và Google."
          @update:model-value="setVal('meta_title_default', $event)"
        />
        <Textarea
          label="Mô tả SEO mặc định"
          :rows="3"
          :model-value="val('meta_description_default')"
          hint="Tối đa 170 ký tự. Dùng làm meta description fallback."
          @update:model-value="setVal('meta_description_default', $event)"
        />
        <div class="my-2 border-t border-line-soft" />
        <Input
          label="Giấy phép kinh doanh"
          :model-value="val('license_info')"
          hint="Hiển thị ở footer FE public."
          @update:model-value="setVal('license_info', $event)"
        />
        <Input
          label="Tên pháp nhân đầy đủ"
          :model-value="val('company_full_name')"
          hint="Tên ghi trên hóa đơn, hợp đồng. Có thể khác tên trung tâm."
          @update:model-value="setVal('company_full_name', $event)"
        />
        <Input
          label="Mã số thuế"
          :model-value="val('tax_code')"
          inputmode="numeric"
          @update:model-value="setVal('tax_code', $event)"
        />
      </Card>

      <!-- SECTION: STATS -->
      <Card v-else-if="activeSection === 'stats'" class="space-y-5">
        <div class="grid gap-5 sm:grid-cols-2">
          <Input
            label="Số học viên đã đỗ"
            type="number"
            :model-value="val('stat_students_count')"
            min="0"
            @update:model-value="setNum('stat_students_count', $event)"
          />
          <Input
            label="Tỉ lệ đỗ lần đầu (%)"
            type="number"
            :model-value="val('stat_pass_rate_percent')"
            min="0"
            max="100"
            @update:model-value="setNum('stat_pass_rate_percent', $event)"
          />
          <Input
            label="Số năm kinh nghiệm"
            type="number"
            :model-value="val('stat_years_experience')"
            min="0"
            @update:model-value="setNum('stat_years_experience', $event)"
          />
          <Input
            label="Sân tập (m²)"
            type="number"
            :model-value="val('stat_practice_area_m2')"
            min="0"
            @update:model-value="setNum('stat_practice_area_m2', $event)"
          />
        </div>
        <p class="text-caption text-ink-40 leading-relaxed">
          Số liệu hiển thị trên trust strip trang chủ. Cập nhật định kỳ thủ công,
          KHÔNG tự đếm theo dữ liệu hệ thống.
        </p>
      </Card>

      <!-- SECTION: CASSO / FACEBOOK LEAD ADS: panel tự quản state + save bar riêng.
           Khi user còn draft SiteSettings chưa lưu ở các tab khác → hiện cảnh báo
           + nút quay lại để tránh mất data khi click discard hoặc rời trang. -->
      <template v-else-if="isIntegrationTab">
        <div
          v-if="hasUnsaved"
          role="status"
          aria-live="polite"
          aria-atomic="true"
          class="flex flex-col gap-1 rounded-md border border-warning/30 bg-warning-soft px-4 py-3 text-caption text-warning sm:flex-row sm:items-center sm:justify-between"
        >
          <span class="flex items-center gap-2">
            <Warning :size="14" weight="duotone" />
            Bạn còn <strong class="text-ink">{{ changedCount }} mục</strong> chưa lưu ở nhóm cấu hình trung tâm.
          </span>
          <button
            type="button"
            class="self-start font-medium text-warning hover:underline sm:self-auto"
            @click="activeSection = firstDirtySiteSettingsSection ?? 'bank'"
          >
            Quay lại để lưu →
          </button>
        </div>
        <IntegrationProviderPanel
          :key="activeSection"
          :provider="activeSection as 'casso' | 'fb'"
        />
      </template>
      </div>
      <!-- /TABPANEL -->

      <!-- SAVE BAR (chỉ cho SiteSettings tabs: integration panel có save bar nội bộ) -->
      <div
        v-if="!isIntegrationTab && (hasUnsaved || saveMutation.isError.value)"
        class="sticky bottom-0 flex flex-col gap-3 rounded-xl border border-brand-200 bg-paper px-5 py-4 shadow-[0_4px_24px_-12px_rgba(20,83,45,0.15)] sm:flex-row sm:items-center sm:justify-between animate-slide-up motion-reduce:animate-none"
      >
        <div class="flex flex-col gap-0.5">
          <p
            role="status"
            aria-live="polite"
            aria-atomic="true"
            class="text-body font-medium text-ink"
          >
            <span class="text-brand-800">{{ changedCount }}</span>
            mục chưa lưu
            <span v-if="sectionChangedCount > 0" class="text-ink-60">
              ({{ sectionChangedCount }} ở mục đang xem)
            </span>
          </p>
          <p v-if="saveMutation.isError.value" class="text-caption text-danger">
            {{ (saveMutation.error.value as Error)?.message ?? 'Lưu thất bại, vui lòng thử lại.' }}
          </p>
          <p v-else class="text-caption text-ink-60">
            Thay đổi áp dụng ngay sau khi lưu, không cần khởi động lại.
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

      <transition
        enter-active-class="transition-opacity duration-300"
        leave-active-class="transition-opacity duration-300"
        enter-from-class="opacity-0"
        leave-to-class="opacity-0"
      >
        <div
          v-if="!isIntegrationTab && saveMutation.isSuccess.value && !hasUnsaved"
          class="inline-flex items-center gap-2 self-start rounded-full border border-success/30 bg-success-soft px-3 py-1.5 text-caption font-medium text-success"
        >
          <Check :size="14" weight="bold" />
          Đã lưu thành công
        </div>
      </transition>
    </section>
  </div>
</template>
