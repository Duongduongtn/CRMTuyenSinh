<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { toast } from 'vue-sonner'
import {
  Phone,
  EnvelopeSimple,
  ChatCircle,
  Hash,
  Clock,
  CheckCircle,
  XCircle,
  ArrowsClockwise,
} from '@/lib/icons'
import Modal from '@/components/ui/Modal.vue'
import Button from '@/components/ui/Button.vue'
import Select from '@/components/ui/Select.vue'
import Input from '@/components/ui/Input.vue'
import Textarea from '@/components/ui/Textarea.vue'
import Spinner from '@/components/ui/Spinner.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { fetchLead, fetchLeadReasons, recordContact, type ContactPayload } from '@/api/leads'
import { formatDateTime, formatPhone, timeAgo } from '@/lib/format'

const props = defineProps<{ open: boolean; leadId: number | null }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const queryClient = useQueryClient()

const lead = useQuery({
  queryKey: ['lead', () => props.leadId],
  queryFn: () => fetchLead(props.leadId as number),
  enabled: computed(() => props.open && props.leadId !== null),
})

const followingReasons = useQuery({
  queryKey: ['lead-reasons', 'following'],
  queryFn: () => fetchLeadReasons('following'),
  staleTime: 5 * 60_000,
})

const failedReasons = useQuery({
  queryKey: ['lead-reasons', 'failed'],
  queryFn: () => fetchLeadReasons('failed'),
  staleTime: 5 * 60_000,
})

const schema = toTypedSchema(
  z
    .object({
      contact_type: z.enum(['call', 'zalo', 'sms', 'email', 'other']),
      status_after: z.enum(['following', 'success', 'failed']),
      priority_after: z.enum(['hot', 'warm', 'cold', '']).optional().default(''),
      reason: z.coerce.number().int().positive().optional().nullable(),
      reason_text: z.string().max(255).optional().default(''),
      note: z.string().max(2000).optional().default(''),
      next_contact_date: z.string().optional().nullable(),
    })
    .superRefine((data, ctx) => {
      if (data.status_after === 'following' && !data.priority_after) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['priority_after'],
          message: 'Chọn độ nóng khi để trạng thái "Đang theo dõi".',
        })
      }
    }),
)

const { defineField, handleSubmit, errors, values, resetForm, setFieldValue } = useForm({
  validationSchema: schema,
  initialValues: {
    contact_type: 'call',
    status_after: 'following',
    priority_after: '',
    reason: null,
    reason_text: '',
    note: '',
    next_contact_date: '',
  },
})

const [contactType, contactTypeAttrs] = defineField('contact_type')
const [statusAfter, statusAfterAttrs] = defineField('status_after')
const [priorityAfter, priorityAfterAttrs] = defineField('priority_after')
const [reason, reasonAttrs] = defineField('reason')
const [reasonText, reasonTextAttrs] = defineField('reason_text')
const [note, noteAttrs] = defineField('note')
const [nextContactDate, nextContactDateAttrs] = defineField('next_contact_date')

watch(
  () => props.open,
  (v) => {
    if (v) {
      resetForm({
        values: {
          contact_type: 'call',
          status_after: 'following',
          priority_after: 'warm',
          reason: null,
          reason_text: '',
          note: '',
          next_contact_date: '',
        },
      })
    }
  },
)

const reasonsForStatus = computed(() => {
  if (values.status_after === 'following') return followingReasons.data.value ?? []
  if (values.status_after === 'failed') return failedReasons.data.value ?? []
  return []
})

watch(
  () => values.status_after,
  () => {
    setFieldValue('reason', null)
    if (values.status_after !== 'following') {
      setFieldValue('priority_after', '')
    } else if (!values.priority_after) {
      setFieldValue('priority_after', 'warm')
    }
  },
)

const submit = useMutation({
  mutationFn: (payload: ContactPayload) => recordContact(props.leadId as number, payload),
  onSuccess: () => {
    toast.success('Đã ghi nhận liên hệ. Lịch sử khách được cập nhật.')
    queryClient.invalidateQueries({ queryKey: ['leads'] })
    queryClient.invalidateQueries({ queryKey: ['lead'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    emit('update:open', false)
  },
  onError: () => {
    toast.error('Không lưu được lần liên hệ. Thử lại.')
  },
})

const onSubmit = handleSubmit(async (v) => {
  if (props.leadId === null) return
  await submit.mutateAsync({
    contact_type: v.contact_type,
    status_after: v.status_after,
    priority_after: v.priority_after || undefined,
    reason: v.reason ?? null,
    reason_text: v.reason_text,
    note: v.note,
    next_contact_date: v.next_contact_date || undefined,
  })
})

const contactTypeOptions = [
  { label: 'Gọi điện', value: 'call' },
  { label: 'Zalo', value: 'zalo' },
  { label: 'SMS', value: 'sms' },
  { label: 'Email', value: 'email' },
  { label: 'Khác', value: 'other' },
]
const statusAfterOptions = [
  { label: 'Đang theo dõi', value: 'following' },
  { label: 'Thành công (đã chốt)', value: 'success' },
  { label: 'Thất bại', value: 'failed' },
]
const priorityOptions = [
  { label: 'Nóng', value: 'hot' },
  { label: 'Ấm', value: 'warm' },
  { label: 'Lạnh', value: 'cold' },
]

const contactTypeIcon = (t: string) => {
  switch (t) {
    case 'call':
      return Phone
    case 'zalo':
      return ChatCircle
    case 'sms':
      return ChatCircle
    case 'email':
      return EnvelopeSimple
    default:
      return Hash
  }
}

const statusIcon = (s: string) => {
  switch (s) {
    case 'success':
      return CheckCircle
    case 'failed':
      return XCircle
    case 'following':
      return ArrowsClockwise
    default:
      return Clock
  }
}

const reasonOptions = computed(() =>
  reasonsForStatus.value.map((r) => ({ label: r.name, value: r.id })),
)
</script>

<template>
  <Modal :open="open" size="wide" title="Ghi nhận liên hệ" @update:open="emit('update:open', $event)">
    <template #header>
      <p class="mt-1 text-[13px] text-ink-60">
        Cập nhật trạng thái, lý do và ghi chú sau khi liên hệ khách. Mỗi lần lưu là 1 dòng audit trail.
      </p>
    </template>

    <div v-if="lead.isLoading.value" class="flex items-center justify-center py-20">
      <Spinner label="Đang tải thông tin khách..." />
    </div>

    <div v-else-if="lead.data.value" class="grid lg:grid-cols-[1.05fr_1fr] divide-x divide-line-soft">
      <!-- Cột trái: form -->
      <form class="p-6 space-y-5" @submit.prevent="onSubmit">
        <!-- Tóm tắt khách -->
        <div class="rounded-xl bg-paper-alt border border-line-soft px-4 py-3 flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-full bg-paper-tint text-brand-700 text-[13px] font-semibold tracking-tight">
            {{ lead.data.value.name.split(' ').pop()?.[0] || 'L' }}
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-[14px] font-semibold text-ink truncate">{{ lead.data.value.name }}</p>
            <p class="text-[12px] text-ink-60 tabular-nums">
              {{ formatPhone(lead.data.value.phone) }}
              <span v-if="lead.data.value.vehicle_class"> · {{ lead.data.value.vehicle_class }}</span>
            </p>
          </div>
          <StatusBadge :status="lead.data.value.status" kind="lead" />
        </div>

        <!-- Hình thức + trạng thái -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Select
            v-model="contactType"
            v-bind="contactTypeAttrs"
            label="Hình thức liên hệ"
            :options="contactTypeOptions"
            :placeholder="''"
            required
            :error="errors.contact_type"
          />
          <Select
            v-model="statusAfter"
            v-bind="statusAfterAttrs"
            label="Trạng thái sau khi liên hệ"
            :options="statusAfterOptions"
            :placeholder="''"
            required
            :error="errors.status_after"
          />
        </div>

        <Select
          v-if="values.status_after === 'following'"
          v-model="priorityAfter"
          v-bind="priorityAfterAttrs"
          label="Độ nóng"
          :options="priorityOptions"
          placeholder="—"
          :error="errors.priority_after"
        />

        <!-- Lý do dropdown -->
        <Select
          v-if="values.status_after !== 'success'"
          v-model="reason"
          v-bind="reasonAttrs"
          label="Lý do (chọn nhanh)"
          :options="reasonOptions"
          placeholder="— Chọn lý do —"
          :error="errors.reason"
          :hint="reasonOptions.length === 0 ? 'Chưa có lý do cấu hình cho trạng thái này.' : ''"
        />

        <Input
          v-if="values.status_after !== 'success'"
          v-model="reasonText"
          v-bind="reasonTextAttrs"
          label="Lý do khác (text tự do, không bắt buộc)"
          placeholder="Ví dụ: khách đang đi nước ngoài, hẹn tháng sau."
          :error="errors.reason_text"
        />

        <Textarea
          v-model="note"
          v-bind="noteAttrs"
          label="Ghi chú nội bộ"
          :rows="3"
          placeholder="Ghi lại tóm tắt cuộc gọi: khách quan tâm gì, đối thủ nào, giá so sánh…"
          :error="errors.note"
        />

        <Input
          v-if="values.status_after === 'following'"
          v-model="nextContactDate"
          v-bind="nextContactDateAttrs"
          type="date"
          label="Hẹn liên hệ tiếp theo"
          :error="errors.next_contact_date"
          hint="Hệ thống sẽ nhắc khi đến ngày."
        />

        <div class="flex items-center justify-end gap-2 pt-2">
          <Button variant="ghost" type="button" @click="emit('update:open', false)">Đóng</Button>
          <Button variant="accent" type="submit" :loading="submit.isPending.value">Lưu ghi nhận</Button>
        </div>
      </form>

      <!-- Cột phải: timeline -->
      <aside class="bg-paper-alt/40 p-6 max-h-[70vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h4 class="text-[13px] font-semibold text-ink tracking-tight">Lịch sử tiếp xúc</h4>
          <span class="text-[11px] text-ink-40 tabular-nums">
            {{ lead.data.value.contact_count }} lần
          </span>
        </div>

        <div v-if="lead.data.value.contacts.length === 0" class="text-center py-8 text-[13px] text-ink-60">
          Chưa có lần liên hệ nào.<br />
          Hãy ghi nhận lần đầu để tạo audit trail.
        </div>

        <ol v-else class="relative space-y-5 border-l border-line-base ml-3">
          <li
            v-for="contact in lead.data.value.contacts"
            :key="contact.id"
            class="relative pl-6"
          >
            <span
              class="absolute -left-[7px] top-1.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-paper border-2 border-brand-500"
              aria-hidden="true"
            />
            <div class="flex items-center gap-2 flex-wrap">
              <component
                :is="contactTypeIcon(contact.contact_type)"
                :size="13"
                class="text-ink-40"
                weight="duotone"
              />
              <span class="text-[11px] uppercase tracking-wider text-ink-40 font-semibold">
                {{ contact.contact_type }}
              </span>
              <component :is="statusIcon(contact.status_after)" :size="12" class="text-ink-40" weight="duotone" />
              <StatusBadge :status="contact.status_after" kind="lead" size="sm" />
              <StatusBadge v-if="contact.priority_after" :status="contact.priority_after" kind="priority" size="sm" />
            </div>
            <p v-if="contact.reason_name || contact.reason_text" class="mt-1.5 text-[13px] text-ink">
              <span class="font-medium">{{ contact.reason_name || contact.reason_text }}</span>
            </p>
            <p v-if="contact.note" class="mt-1 text-[12.5px] text-ink-60 leading-relaxed whitespace-pre-line">
              {{ contact.note }}
            </p>
            <div class="mt-1.5 flex items-center gap-2 text-[11px] text-ink-40">
              <span>{{ contact.user_name }}</span>
              <span aria-hidden="true">·</span>
              <span :title="formatDateTime(contact.created_at)">{{ timeAgo(contact.created_at) }}</span>
              <span v-if="contact.next_contact_date" aria-hidden="true">·</span>
              <span v-if="contact.next_contact_date">hẹn {{ contact.next_contact_date }}</span>
            </div>
          </li>
        </ol>
      </aside>
    </div>
  </Modal>
</template>
