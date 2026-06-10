<script setup lang="ts">
import {
  PhArrowLeft,
  PhSpinnerGap,
  PhUploadSimple,
  PhCheckCircle,
  PhClock,
  PhXCircle,
  PhWarning,
  PhFile,
  PhImage,
} from '@phosphor-icons/vue'

const route = useRoute()
const personId = computed(() => Number(route.params.id))

const { items, loading, uploading, error, load, upload } = usePersonDocuments(personId.value)
const docTypes = ref<DocumentType[]>([])
const docTypesLoading = ref(true)

const loadTypes = async () => {
  docTypesLoading.value = true
  try {
    const resp = await useDocumentTypes().list('person')
    docTypes.value = resp.results
  } catch {
    docTypes.value = []
  } finally {
    docTypesLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([load(), loadTypes()])
})

useHead({ title: 'Hồ sơ cá nhân' })

const itemsByType = computed(() => {
  const map: Record<number, typeof items.value[number]> = {}
  // Lấy bản mới nhất cho mỗi loại
  for (const it of items.value) {
    const existing = map[it.document_type.id]
    if (!existing || new Date(it.created_at) > new Date(existing.created_at)) {
      map[it.document_type.id] = it
    }
  }
  return map
})

const uploadingTypeId = ref<number | null>(null)
const lastError = ref<string | null>(null)

const onFileSelected = async (event: Event, typeId: number) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  lastError.value = null
  uploadingTypeId.value = typeId
  const result = await upload(typeId, file)
  uploadingTypeId.value = null
  if (!result) lastError.value = error.value
  target.value = ''
}

import type { DocumentType } from '~/composables/useDocuments'
</script>

<template>
  <div class="container-base pt-2">
    <button
      type="button"
      class="text-ink-60 hover:text-ink inline-flex items-center gap-1 text-sm mb-3 min-h-11"
      @click="$router.back()"
    >
      <PhArrowLeft class="size-4" /> Quay lại
    </button>

    <h1 class="text-xl font-bold tracking-tight mb-1">Giấy tờ cá nhân</h1>
    <p class="text-sm text-ink-60 mb-4">
      Chụp rõ, không chói sáng. Hệ thống chấp nhận JPG, PNG, WEBP, PDF tối đa 5MB.
    </p>

    <div v-if="lastError" class="card-base bg-danger-soft text-danger text-sm mb-3">
      <PhWarning class="size-4 inline mr-1.5" /> {{ lastError }}
    </div>

    <div v-if="loading || docTypesLoading" class="card-base flex items-center gap-3 text-ink-60">
      <PhSpinnerGap class="size-5 animate-spin" /> Đang tải…
    </div>

    <ul v-else class="space-y-3">
      <li
        v-for="dt in docTypes"
        :key="dt.id"
        class="card-base"
      >
        <div class="flex items-start justify-between gap-2 mb-2">
          <div class="min-w-0">
            <h3 class="font-semibold text-base flex items-center gap-1.5">
              {{ dt.name }}
              <span v-if="dt.is_required" class="text-danger text-xs" aria-label="Bắt buộc">*</span>
            </h3>
            <p class="text-xs text-ink-60 mt-0.5 leading-relaxed">{{ dt.description }}</p>
          </div>
          <StatusBadge
            v-if="itemsByType[dt.id]"
            :status="itemsByType[dt.id].status"
            :label="itemsByType[dt.id].status_display"
          />
        </div>

        <div
          v-if="itemsByType[dt.id]?.status === 'rejected' && itemsByType[dt.id].review_note"
          class="mb-2 px-3 py-2 bg-danger-soft rounded-md text-xs text-danger"
        >
          <PhWarning class="size-3.5 inline mr-1" />
          {{ itemsByType[dt.id].review_note }}
        </div>

        <div v-if="itemsByType[dt.id] && itemsByType[dt.id].status !== 'rejected'" class="mb-3 flex items-center gap-2 text-xs text-ink-60">
          <a
            :href="itemsByType[dt.id].file_url"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center gap-1 text-brand-700 hover:underline truncate"
          >
            <component
              :is="itemsByType[dt.id].mime_type.startsWith('image/') ? PhImage : PhFile"
              class="size-4 shrink-0"
            />
            <span class="truncate">Xem tệp đã upload</span>
          </a>
          <span class="num-display shrink-0">{{ formatBytes(itemsByType[dt.id].file_size) }}</span>
        </div>

        <label
          class="btn-secondary w-full cursor-pointer"
          :class="uploadingTypeId === dt.id ? 'opacity-60' : ''"
        >
          <input
            type="file"
            class="sr-only"
            accept="image/jpeg,image/png,image/webp,application/pdf"
            :disabled="uploadingTypeId === dt.id || uploading"
            @change="(e) => onFileSelected(e, dt.id)"
          >
          <PhSpinnerGap v-if="uploadingTypeId === dt.id" class="size-5 animate-spin" />
          <PhUploadSimple v-else class="size-5" />
          <span>{{ uploadingTypeId === dt.id ? 'Đang tải lên…' : (itemsByType[dt.id] ? 'Tải lại' : 'Tải lên') }}</span>
        </label>
      </li>
    </ul>
  </div>
</template>
