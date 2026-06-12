<script setup lang="ts">
/**
 * Trang Cài đặt — chỉnh full SiteSettings (brand, contact, social, bank, SEO, stats).
 *
 * 6 section ngang dạng tab, mỗi section là 1 nhóm field. Edit local draft → save
 * bulk qua PATCH /api/admin/site-settings/. Sticky save bar hiện khi có thay đổi.
 *
 * Ảnh (logo/favicon/og_image) tạm thời chỉnh trong Django admin tới khi build
 * upload UI — page hiển thị note rõ ràng.
 */
import { computed, ref } from 'vue'
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
  Info,
  ArrowsClockwise,
  Check,
} from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Textarea from '@/components/ui/Textarea.vue'
import Select from '@/components/ui/Select.vue'
import Spinner from '@/components/ui/Spinner.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import {
  fetchSiteSettingsAdmin,
  updateSiteSettingsAdmin,
  type SiteSettingsAdmin,
  type SiteSettingsAdminPatch,
} from '@/api/siteSettings'

type SectionKey = 'bank' | 'brand' | 'contact' | 'social' | 'seo' | 'stats'

interface SectionMeta {
  key: SectionKey
  label: string
  icon: typeof Bank
  description: string
}

const SECTIONS: SectionMeta[] = [
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
]

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
const SECTION_FIELDS: Record<SectionKey, (keyof SiteSettingsAdminPatch)[]> = {
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
  const fields = SECTION_FIELDS[activeSection.value]
  return fields.filter((f) => draft.value[f] !== undefined).length
})

const currentSection = computed(
  () => SECTIONS.find((s) => s.key === activeSection.value) ?? SECTIONS[0],
)
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
          Cập nhật thương hiệu, liên hệ, mạng xã hội, tài khoản ngân hàng nhận đặt cọc
          và số liệu hiển thị. Thay đổi áp dụng tức thì cho website công khai và CRM
          nội bộ, không cần khởi động lại dịch vụ.
        </p>
      </div>
      <div class="flex flex-col items-start gap-2 sm:items-end">
        <span class="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-caption font-medium text-brand-800">
          <Gear :size="14" weight="duotone" />
          {{ SECTIONS.length }} nhóm cấu hình
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

    <!-- NOTE: image upload tạm chỉnh Django admin -->
    <Card class="border-info/30 bg-info-soft/40 px-5 py-4">
      <div class="flex items-start gap-3">
        <Info :size="20" weight="duotone" class="mt-0.5 shrink-0 text-info" />
        <div class="text-body leading-relaxed text-ink-60">
          <p class="font-medium text-ink">Tải lên hình ảnh thương hiệu</p>
          <p class="mt-1">
            Logo, favicon và ảnh chia sẻ mạng xã hội tạm thời cập nhật trong
            <a
              href="/django-admin/core/sitesettings/"
              target="_blank"
              rel="noopener"
              class="font-medium text-brand-700 underline-offset-4 hover:underline"
            >Django admin · Thông tin trung tâm</a>.
            Giao diện tải lên trực tiếp trong CRM sẽ bổ sung ở phiên bản kế tiếp.
          </p>
        </div>
      </div>
    </Card>

    <!-- TAB SWITCHER -->
    <nav role="tablist" aria-label="Chọn nhóm cấu hình" class="-mb-px flex flex-wrap gap-1 border-b border-line-soft">
      <button
        v-for="sec in SECTIONS"
        :key="sec.key"
        type="button"
        :role="'tab'"
        :aria-selected="activeSection === sec.key"
        :class="[
          'inline-flex items-center gap-2 px-4 py-3 text-body font-medium transition-colors duration-200',
          activeSection === sec.key
            ? 'text-brand-800 border-b-2 border-brand-700'
            : 'text-ink-60 hover:text-ink border-b-2 border-transparent',
        ]"
        @click="activeSection = sec.key"
      >
        <component :is="sec.icon" :size="18" :weight="activeSection === sec.key ? 'duotone' : 'regular'" />
        {{ sec.label }}
        <span
          v-if="SECTION_FIELDS[sec.key].some((f) => draft[f] !== undefined)"
          class="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-brand-600"
          aria-hidden="true"
        />
      </button>
    </nav>

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
      <Card v-else-if="activeSection === 'brand'" class="space-y-5">
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

      <!-- SAVE BAR -->
      <div
        v-if="hasUnsaved || saveMutation.isError.value"
        class="sticky bottom-0 flex flex-col gap-3 rounded-xl border border-brand-200 bg-paper px-5 py-4 shadow-[0_4px_24px_-12px_rgba(20,83,45,0.15)] sm:flex-row sm:items-center sm:justify-between animate-slide-up motion-reduce:animate-none"
      >
        <div class="flex flex-col gap-0.5">
          <p class="text-body font-medium text-ink">
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
