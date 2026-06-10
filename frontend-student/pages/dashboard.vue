<script setup lang="ts">
import {
  PhFolderOpen,
  PhWarning,
  PhArrowRight,
  PhCalendarDots,
  PhCar,
  PhSpinnerGap,
} from '@phosphor-icons/vue'

const { enrollments, loading, error, load } = useEnrollments()
const { account } = useAuth()

onMounted(() => load())

useHead({ title: 'Tổng quan' })

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 11) return 'Chào buổi sáng'
  if (h < 14) return 'Chào buổi trưa'
  if (h < 18) return 'Chào buổi chiều'
  return 'Chào buổi tối'
})
</script>

<template>
  <div class="container-base pt-4">
    <section class="mb-5">
      <p class="text-xs uppercase tracking-wider text-brand-700 font-semibold mb-1">{{ greeting }}</p>
      <h1 class="text-2xl font-bold tracking-tight">
        {{ account?.display_name || 'Học viên' }}
      </h1>
    </section>

    <div v-if="loading && !enrollments.length" class="card-base flex items-center gap-3 text-ink-60">
      <PhSpinnerGap class="size-5 animate-spin" />
      Đang tải dữ liệu…
    </div>

    <div v-else-if="error" class="card-base border-danger/30 bg-danger-soft text-danger">
      <PhWarning class="size-5 inline mr-2" />
      {{ error }}
      <button class="block mt-2 text-sm underline" @click="load">Thử lại</button>
    </div>

    <div v-else-if="!enrollments.length" class="card-base text-center py-10">
      <div class="inline-flex size-12 bg-paper-alt rounded-xl items-center justify-center mb-3">
        <PhFolderOpen class="size-6 text-ink-40" />
      </div>
      <h3 class="font-semibold mb-1">Chưa có khóa học nào</h3>
      <p class="text-sm text-ink-60">
        Khi tư vấn viên chốt đơn cho bạn, đơn sẽ xuất hiện ở đây.
      </p>
    </div>

    <ul v-else class="space-y-3">
      <li v-for="enr in enrollments" :key="enr.id">
        <NuxtLink
          :to="`/enrollment/${enr.id}`"
          class="card-base block hover:border-brand-300 active:bg-paper-alt transition group"
        >
          <div class="flex items-start justify-between gap-3 mb-3">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 text-xs text-ink-40 mb-1">
                <span class="num-display font-mono">{{ enr.code }}</span>
              </div>
              <h3 class="font-semibold text-base leading-tight mb-1">{{ enr.course_title }}</h3>
              <p class="text-xs text-ink-60 inline-flex items-center gap-1">
                <PhCar class="size-3.5" />
                Hạng {{ enr.vehicle_class_display.split(' - ')[0] }}
              </p>
            </div>
            <StatusBadge :status="enr.status" :label="enr.status_display" />
          </div>

          <div class="border-t border-line-soft pt-3 flex items-center justify-between text-sm">
            <div>
              <p class="text-xs text-ink-40">Còn phải đóng</p>
              <p class="font-bold num-display text-brand-700">
                {{ formatVND(enr.remaining_amount) }}
              </p>
            </div>
            <div v-if="enr.docs_missing > 0" class="badge badge-warning">
              Thiếu {{ enr.docs_missing }} hồ sơ
            </div>
            <PhArrowRight v-else class="size-5 text-ink-40 group-hover:text-brand-700 group-hover:translate-x-0.5 transition" />
          </div>

          <div v-if="enr.deposit_paid_at" class="mt-3 pt-3 border-t border-line-soft inline-flex items-center gap-1.5 text-xs text-ink-60">
            <PhCalendarDots class="size-3.5" />
            Đặt cọc <span class="num-display">{{ formatDate(enr.deposit_paid_at) }}</span>
          </div>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
