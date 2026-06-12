<script setup lang="ts">
/**
 * Component upload ảnh brand (logo / favicon / og_image) cho tab Thương hiệu.
 *
 * Drag-drop zone + click-to-browse. Validate client-side trước khi gọi BE để
 * fail fast (size, type, dimension), BE vẫn validate lại độc lập.
 *
 * Props:
 * - field: 1 trong 3 BrandImageField.
 * - currentUrl: URL ảnh hiện tại (rỗng = chưa upload).
 *
 * Emit:
 * - uploaded(SiteSettingsAdmin): server trả lại full state mới sau upload/delete.
 */
import { computed, ref } from 'vue'
import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { toast } from 'vue-sonner'
import {
  CloudArrowUp,
  Image as ImageIcon,
  Trash,
  Warning,
} from '@/lib/icons'
import Button from '@/components/ui/Button.vue'
import Spinner from '@/components/ui/Spinner.vue'
import {
  BRAND_IMAGE_SPEC,
  deleteBrandImage,
  uploadBrandImage,
  type BrandImageField,
  type SiteSettingsAdmin,
} from '@/api/siteSettings'

const props = defineProps<{
  field: BrandImageField
  currentUrl: string
}>()

const emit = defineEmits<{
  uploaded: [data: SiteSettingsAdmin]
}>()

const spec = computed(() => BRAND_IMAGE_SPEC[props.field])
const inputRef = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const validationError = ref<string | null>(null)
const queryClient = useQueryClient()

const uploadMutation = useMutation({
  mutationFn: (file: File) => uploadBrandImage(props.field, file),
  onSuccess: async (data) => {
    await queryClient.invalidateQueries({ queryKey: ['site-settings-admin'] })
    await queryClient.invalidateQueries({ queryKey: ['site-public'] })
    emit('uploaded', data)
    toast.success(`Đã cập nhật ${spec.value.label.toLowerCase()}.`)
    validationError.value = null
  },
  onError: (err: unknown) => {
    const message =
      err instanceof Error
        ? err.message
        : 'Tải lên thất bại, vui lòng thử lại.'
    toast.error(message)
  },
})

const deleteMutation = useMutation({
  mutationFn: () => deleteBrandImage(props.field),
  onSuccess: async (data) => {
    await queryClient.invalidateQueries({ queryKey: ['site-settings-admin'] })
    await queryClient.invalidateQueries({ queryKey: ['site-public'] })
    emit('uploaded', data)
    toast.success(`Đã xóa ${spec.value.label.toLowerCase()}.`)
  },
  onError: () => {
    toast.error('Xóa thất bại, vui lòng thử lại.')
  },
})

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function readImageDimension(
  file: File,
): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight })
      URL.revokeObjectURL(url)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Không đọc được kích thước ảnh.'))
    }
    img.src = url
  })
}

async function validateAndUpload(file: File) {
  validationError.value = null
  const s = spec.value

  if (file.size > s.maxBytes) {
    validationError.value = `File ${formatBytes(file.size)} vượt quá ${formatBytes(s.maxBytes)}.`
    return
  }

  const accepted = s.accept.split(',').map((t) => t.trim())
  if (!accepted.includes(file.type)) {
    validationError.value = `Định dạng ${file.type || 'không xác định'} không hợp lệ. ${s.hint}`
    return
  }

  try {
    const { width, height } = await readImageDimension(file)
    if (width < s.minWidth || height < s.minHeight) {
      validationError.value = `Kích thước ${width}x${height} nhỏ hơn tối thiểu ${s.minWidth}x${s.minHeight}.`
      return
    }
    if (width > s.maxWidth || height > s.maxHeight) {
      validationError.value = `Kích thước ${width}x${height} vượt tối đa ${s.maxWidth}x${s.maxHeight}.`
      return
    }
  } catch (err) {
    validationError.value =
      err instanceof Error
        ? err.message
        : 'Không kiểm tra được kích thước ảnh.'
    return
  }

  uploadMutation.mutate(file)
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    validateAndUpload(file)
  }
  // Reset input để cùng file có thể chọn lại sau khi xóa.
  target.value = ''
}

function onDrop(event: DragEvent) {
  event.preventDefault()
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) {
    validateAndUpload(file)
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

function openFilePicker() {
  inputRef.value?.click()
}

function onDelete() {
  if (confirm(`Xóa ${spec.value.label.toLowerCase()} hiện tại?`)) {
    deleteMutation.mutate()
  }
}

const isBusy = computed(
  () => uploadMutation.isPending.value || deleteMutation.isPending.value,
)
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-col gap-1">
      <label class="text-body font-medium text-ink">{{ spec.label }}</label>
      <p class="text-caption text-ink-60">{{ spec.hint }}</p>
    </div>

    <div class="flex flex-col gap-3 sm:flex-row sm:items-start">
      <!-- Preview thumb -->
      <div
        role="img"
        :aria-label="currentUrl ? `Xem trước ${spec.label.toLowerCase()}` : `Chưa có ${spec.label.toLowerCase()}`"
        class="flex h-32 w-32 shrink-0 flex-col items-center justify-center overflow-hidden rounded-md border border-line-base bg-paper-alt"
      >
        <img
          v-if="currentUrl"
          :src="currentUrl"
          :alt="`Xem trước ${spec.label.toLowerCase()}`"
          class="max-h-full max-w-full object-contain"
        />
        <template v-else>
          <ImageIcon :size="32" class="text-ink-40" aria-hidden="true" />
          <span class="mt-1.5 text-caption text-ink-40">Chưa có ảnh</span>
        </template>
      </div>

      <!-- Drop zone -->
      <div
        class="flex-1"
        :class="[
          'rounded-md border-2 border-dashed transition-colors duration-200',
          isDragging
            ? 'border-brand-500 bg-brand-50'
            : 'border-line-base hover:border-line-strong/50',
        ]"
        @drop="onDrop"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
      >
        <button
          type="button"
          class="flex w-full flex-col items-center justify-center gap-2 px-6 py-8 text-center outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 focus-visible:rounded-md"
          :disabled="isBusy"
          :aria-busy="isBusy"
          @click="openFilePicker"
        >
          <template v-if="isBusy">
            <Spinner />
            <span class="sr-only">Đang tải ảnh lên...</span>
          </template>
          <template v-else>
            <CloudArrowUp :size="28" weight="duotone" class="text-brand-700" />
            <span class="block text-body font-medium text-ink">
              Kéo thả ảnh vào đây hoặc bấm để chọn
            </span>
            <span class="block text-caption text-ink-60">{{ spec.hint }}</span>
          </template>
        </button>
        <input
          ref="inputRef"
          type="file"
          class="sr-only"
          :accept="spec.accept"
          :aria-label="`Chọn ${spec.label.toLowerCase()}`"
          @change="onFileChange"
        />
      </div>
    </div>

    <!-- Error inline -->
    <div
      v-if="validationError"
      role="alert"
      class="flex items-start gap-2 rounded-md border border-danger/30 bg-danger-soft px-4 py-3 text-caption text-danger"
    >
      <Warning :size="16" weight="duotone" class="mt-0.5 shrink-0" />
      <span>{{ validationError }}</span>
    </div>

    <!-- Action delete -->
    <div v-if="currentUrl" class="flex items-center justify-end">
      <Button
        variant="ghost"
        size="sm"
        :disabled="isBusy"
        @click="onDelete"
      >
        <Trash :size="14" />
        Xóa ảnh hiện tại
      </Button>
    </div>
  </div>
</template>
