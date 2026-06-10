<script setup lang="ts">
import {
  PhArrowLeft,
  PhSpinnerGap,
  PhQrCode,
  PhCheckCircle,
  PhCalendar,
  PhInfo,
} from '@phosphor-icons/vue'

const route = useRoute()
const id = computed(() => Number(route.params.id))

const { data: enrollment, loading, error, load } = useEnrollment(id)

onMounted(() => load())

useHead({ title: () => enrollment.value ? `Đơn ${enrollment.value.code}` : 'Chi tiết đơn' })

const { public: { publicUrl } } = useRuntimeConfig()
const depositLink = computed(() =>
  enrollment.value ? `${publicUrl}/dh/${enrollment.value.deposit_link_token}` : ''
)
</script>

<template>
  <div class="container-base pt-2">
    <button
      type="button"
      class="text-ink-60 hover:text-ink inline-flex items-center gap-1 text-sm mb-3 min-h-11"
      @click="$router.back()"
    >
      <PhArrowLeft class="size-4" />
      Quay lại
    </button>

    <div v-if="loading" class="card-base flex items-center gap-3 text-ink-60">
      <PhSpinnerGap class="size-5 animate-spin" />
      Đang tải…
    </div>

    <div v-else-if="error" class="card-base bg-danger-soft text-danger">{{ error }}</div>

    <template v-else-if="enrollment">
      <section class="card-base mb-3">
        <div class="flex items-start justify-between gap-2 mb-3">
          <div>
            <p class="text-xs text-ink-40 num-display font-mono">{{ enrollment.code }}</p>
            <h1 class="text-xl font-bold tracking-tight">{{ enrollment.course_title }}</h1>
            <p class="text-sm text-ink-60 mt-0.5">{{ enrollment.vehicle_class_display }}</p>
          </div>
          <StatusBadge :status="enrollment.status" :label="enrollment.status_display" />
        </div>

        <dl class="grid grid-cols-2 gap-3 pt-3 border-t border-line-soft text-sm">
          <div>
            <dt class="text-xs text-ink-40">Học phí</dt>
            <dd class="font-semibold num-display">{{ formatVND(enrollment.tuition_fee) }}</dd>
          </div>
          <div>
            <dt class="text-xs text-ink-40">Đã đóng</dt>
            <dd class="font-semibold num-display">{{ formatVND(enrollment.paid_amount) }}</dd>
          </div>
          <div>
            <dt class="text-xs text-ink-40">Cọc giữ chỗ</dt>
            <dd class="font-semibold num-display">{{ formatVND(enrollment.deposit_amount) }}</dd>
          </div>
          <div>
            <dt class="text-xs text-ink-40">Còn phải đóng</dt>
            <dd class="font-bold num-display text-brand-700">{{ formatVND(enrollment.remaining_amount) }}</dd>
          </div>
        </dl>
      </section>

      <a
        v-if="enrollment.status === 'pending' && depositLink"
        :href="depositLink"
        target="_blank"
        rel="noopener"
        class="btn-primary w-full mb-3"
      >
        <PhQrCode class="size-5" />
        Mở trang đặt cọc QR
      </a>

      <section v-if="enrollment.person" class="card-base mb-3">
        <h2 class="text-sm font-semibold mb-3 flex items-center gap-1.5">
          <PhInfo class="size-4 text-brand-700" />
          Người học
        </h2>
        <dl class="text-sm space-y-2">
          <div class="flex justify-between gap-2">
            <dt class="text-ink-60">Họ tên</dt>
            <dd class="font-medium text-right">{{ enrollment.person.full_name }}</dd>
          </div>
          <div v-if="enrollment.person.id_number_last4" class="flex justify-between gap-2">
            <dt class="text-ink-60">CCCD</dt>
            <dd class="font-medium text-right num-display">••••{{ enrollment.person.id_number_last4 }}</dd>
          </div>
          <div v-if="enrollment.person.date_of_birth" class="flex justify-between gap-2">
            <dt class="text-ink-60">Ngày sinh</dt>
            <dd class="font-medium text-right num-display">{{ formatDate(enrollment.person.date_of_birth) }}</dd>
          </div>
        </dl>
      </section>

      <NuxtLink
        v-if="enrollment.person"
        :to="`/ho-so/${enrollment.person.id}`"
        class="card-base flex items-center justify-between hover:border-brand-300 transition group"
      >
        <div>
          <h3 class="font-semibold text-sm">Quản lý hồ sơ</h3>
          <p class="text-xs text-ink-60 mt-0.5">CCCD, ảnh chân dung, giấy khám sức khỏe</p>
        </div>
        <span class="text-brand-700">
          <PhArrowLeft class="size-5 rotate-180 group-hover:translate-x-0.5 transition" />
        </span>
      </NuxtLink>

      <div class="mt-4 text-xs text-ink-40 flex items-center gap-1.5">
        <PhCalendar class="size-3.5" />
        Tạo đơn <span class="num-display">{{ formatDateTime(enrollment.created_at) }}</span>
      </div>
    </template>
  </div>
</template>
