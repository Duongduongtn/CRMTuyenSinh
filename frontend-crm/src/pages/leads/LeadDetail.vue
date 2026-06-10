<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import {
  ArrowLeft,
  Phone,
  EnvelopeSimple,
  MapPin,
  Calendar,
  ChatCircleDots,
  Globe,
  Tag,
} from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Spinner from '@/components/ui/Spinner.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import LeadContactModal from '@/components/LeadContactModal.vue'
import { fetchLead } from '@/api/leads'
import { formatDate, formatDateTime, formatPhone, timeAgo } from '@/lib/format'

const route = useRoute()
const router = useRouter()
const leadId = computed(() => Number(route.params.id))

const { data, isLoading } = useQuery({
  queryKey: ['lead', leadId],
  queryFn: () => fetchLead(leadId.value),
})

const modalOpen = ref(false)
</script>

<template>
  <div>
    <Button variant="ghost" size="sm" class="mb-4" @click="router.back()">
      <ArrowLeft :size="14" weight="bold" />
      Quay lại
    </Button>

    <div v-if="isLoading" class="py-20 flex justify-center">
      <Spinner label="Đang tải chi tiết lead..." />
    </div>

    <div v-else-if="data" class="grid lg:grid-cols-3 gap-5">
      <!-- Cột chính -->
      <div class="lg:col-span-2 space-y-5">
        <Card>
          <div class="flex items-start justify-between gap-4">
            <div class="flex items-center gap-4 min-w-0">
              <div class="flex h-14 w-14 items-center justify-center rounded-full bg-paper-tint text-brand-700 text-[18px] font-semibold tracking-tight shrink-0">
                {{ data.name.split(' ').pop()?.[0] || 'L' }}
              </div>
              <div class="min-w-0">
                <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">Lead #{{ data.id }}</p>
                <h2 class="text-2xl font-semibold tracking-tighter text-ink truncate">{{ data.name }}</h2>
                <p class="text-[13px] text-ink-60 tabular-nums">{{ formatPhone(data.phone) }}</p>
              </div>
            </div>
            <div class="flex flex-col items-end gap-2 shrink-0">
              <StatusBadge :status="data.status" kind="lead" />
              <StatusBadge v-if="data.priority" :status="data.priority" kind="priority" />
            </div>
          </div>

          <div class="grid grid-cols-2 lg:grid-cols-4 gap-y-4 mt-6 pt-6 border-t border-line-soft text-[13px]">
            <div class="space-y-0.5">
              <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">Email</p>
              <p class="text-ink truncate">{{ data.email || '—' }}</p>
            </div>
            <div class="space-y-0.5">
              <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">Khu vực</p>
              <p class="text-ink">{{ data.district || '—' }}</p>
            </div>
            <div class="space-y-0.5">
              <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">Hạng quan tâm</p>
              <p class="text-ink">{{ data.vehicle_class || '—' }}</p>
            </div>
            <div class="space-y-0.5">
              <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">Phụ trách</p>
              <p class="text-ink truncate">{{ data.assigned_to_name || 'Chưa phân' }}</p>
            </div>
          </div>

          <div v-if="data.notes" class="mt-4 pt-4 border-t border-line-soft">
            <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold mb-1.5">Khách ghi chú</p>
            <p class="text-[13.5px] text-ink leading-relaxed whitespace-pre-line">{{ data.notes }}</p>
          </div>

          <div class="mt-5 pt-5 border-t border-line-soft flex flex-wrap gap-2">
            <Button variant="accent" @click="modalOpen = true">
              <ChatCircleDots :size="14" weight="duotone" />
              Ghi nhận liên hệ
            </Button>
            <Button variant="secondary" :as="'a'" :href="`tel:${data.phone}`">
              <Phone :size="14" weight="duotone" />
              Gọi
            </Button>
            <Button variant="secondary" :as="'a'" :href="`mailto:${data.email}`" :disabled="!data.email">
              <EnvelopeSimple :size="14" weight="duotone" />
              Email
            </Button>
          </div>
        </Card>

        <!-- Timeline đầy đủ -->
        <Card :padded="false">
          <div class="px-6 py-5 border-b border-line-soft flex items-center justify-between">
            <div>
              <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">Audit trail</p>
              <h3 class="text-base font-semibold text-ink tracking-tight">Lịch sử tiếp xúc</h3>
            </div>
            <span class="text-[12px] text-ink-60 tabular-nums">{{ data.contact_count }} lần</span>
          </div>

          <div v-if="data.contacts.length === 0" class="px-6 py-12 text-center text-[13px] text-ink-60">
            Chưa có lần liên hệ nào. Click "Ghi nhận liên hệ" để bắt đầu.
          </div>
          <ol v-else class="p-6 space-y-5 relative border-l border-line-base ml-3">
            <li
              v-for="contact in data.contacts"
              :key="contact.id"
              class="relative pl-6"
            >
              <span
                class="absolute -left-[7px] top-1.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-paper border-2 border-brand-500"
                aria-hidden="true"
              />
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">{{ contact.contact_type }}</span>
                <StatusBadge :status="contact.status_after" kind="lead" size="sm" />
                <StatusBadge v-if="contact.priority_after" :status="contact.priority_after" kind="priority" size="sm" />
              </div>
              <p v-if="contact.reason_name || contact.reason_text" class="mt-1.5 text-[13.5px] text-ink font-medium">
                {{ contact.reason_name || contact.reason_text }}
              </p>
              <p v-if="contact.note" class="mt-1 text-[13px] text-ink-60 leading-relaxed whitespace-pre-line">
                {{ contact.note }}
              </p>
              <div class="mt-1.5 flex items-center gap-2 text-[11px] text-ink-40">
                <span>{{ contact.user_name }}</span>
                <span aria-hidden="true">·</span>
                <span :title="formatDateTime(contact.created_at)">{{ timeAgo(contact.created_at) }}</span>
                <span v-if="contact.next_contact_date" aria-hidden="true">·</span>
                <span v-if="contact.next_contact_date">hẹn {{ formatDate(contact.next_contact_date) }}</span>
              </div>
            </li>
          </ol>
        </Card>
      </div>

      <!-- Cột phải: meta + tracking -->
      <aside class="space-y-5">
        <Card>
          <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold mb-3">Nguồn</p>
          <ul class="space-y-2.5 text-[13px]">
            <li class="flex items-center gap-2.5">
              <Tag :size="14" class="text-ink-40" weight="duotone" />
              <span class="text-ink-60">Nguồn:</span>
              <span class="text-ink font-medium">{{ data.source }}</span>
            </li>
            <li v-if="data.source_page" class="flex items-start gap-2.5 break-all">
              <Globe :size="14" class="text-ink-40 mt-0.5" weight="duotone" />
              <span class="text-ink-60">URL:</span>
              <span class="text-ink text-[12px] font-mono">{{ data.source_page }}</span>
            </li>
            <li v-if="data.utm_campaign" class="flex items-center gap-2.5">
              <Tag :size="14" class="text-ink-40" weight="duotone" />
              <span class="text-ink-60">Campaign:</span>
              <span class="text-ink font-medium">{{ data.utm_campaign }}</span>
            </li>
            <li v-if="data.district" class="flex items-center gap-2.5">
              <MapPin :size="14" class="text-ink-40" weight="duotone" />
              <span class="text-ink-60">Khu vực:</span>
              <span class="text-ink">{{ data.district }}</span>
            </li>
            <li class="flex items-center gap-2.5">
              <Calendar :size="14" class="text-ink-40" weight="duotone" />
              <span class="text-ink-60">Tạo lúc:</span>
              <span class="text-ink">{{ formatDateTime(data.created_at) }}</span>
            </li>
          </ul>
        </Card>

        <Card tone="alt">
          <p class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold mb-2">Thiết bị</p>
          <p class="text-[12px] text-ink-60 leading-relaxed">
            {{ data.device_browser || '—' }} · {{ data.device_os || '—' }}
            <span v-if="data.screen_size"> · {{ data.screen_size }}</span>
          </p>
          <p v-if="data.ip_address" class="text-[11px] text-ink-40 mt-1 font-mono">IP {{ data.ip_address }}</p>
        </Card>
      </aside>
    </div>

    <LeadContactModal v-model:open="modalOpen" :lead-id="leadId" />
  </div>
</template>
