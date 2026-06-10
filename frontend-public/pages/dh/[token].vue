<script setup lang="ts">
import {
  PhCheckCircle,
  PhCopy,
  PhBank,
  PhWallet,
  PhInfo,
  PhSpinnerGap,
  PhArrowClockwise,
} from '@phosphor-icons/vue'
import { useDepositQR, useEnrollmentByToken } from '~/composables/useEnrollment'
import { formatVND } from '~/composables/useCourses'
import { useSiteSettings } from '~/composables/useSiteSettings'

definePageMeta({
  layout: 'default',
})

const route = useRoute()
const token = computed(() => String(route.params.token))

const { data: site } = await useSiteSettings()
const { data: enrollment, refresh, error } = await useEnrollmentByToken(token.value)
const { data: qr } = await useDepositQR(token.value)

if (error.value || !enrollment.value) {
  throw createError({ statusCode: 404, statusMessage: 'Liên kết đặt cọc không hợp lệ hoặc đã hết hạn.', fatal: true })
}

// Polling 3s cho đến khi is_deposit_paid = true. Dừng poll khi paid hoặc unmount.
const POLL_MS = 3000
let timer: ReturnType<typeof setInterval> | null = null

const stopPolling = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

const startPolling = () => {
  if (process.server) return
  stopPolling()
  timer = setInterval(async () => {
    try {
      await refresh()
      if (enrollment.value?.is_deposit_paid) {
        stopPolling()
      }
    } catch {
      // network hiccup — giữ poll, sẽ retry lần sau
    }
  }, POLL_MS)
}

onMounted(() => {
  if (!enrollment.value?.is_deposit_paid) startPolling()
})
onBeforeUnmount(stopPolling)

const copied = ref('')
const copy = async (label: string, value: string) => {
  try {
    await navigator.clipboard.writeText(value)
    copied.value = label
    setTimeout(() => { copied.value = '' }, 1500)
  } catch {
    copied.value = ''
  }
}

const remaining = computed(() => {
  if (!enrollment.value) return 0
  return Math.max(0, Number(enrollment.value.deposit_amount) - Number(enrollment.value.paid_amount))
})

useSeoMeta({
  title: enrollment.value
    ? `Đặt cọc giữ chỗ · ${enrollment.value.code}`
    : 'Đặt cọc giữ chỗ',
  description:
    'Trang đặt cọc giữ chỗ. Quét QR hoặc chuyển khoản theo thông tin hiển thị. Hệ thống tự xác nhận trong 2 phút.',
  robots: 'noindex, nofollow',
})
</script>

<template>
  <section class="bg-paper-alt min-h-[80vh] py-10 md:py-16">
    <div class="max-w-[1080px] mx-auto px-5 md:px-8">

      <!-- Đã nhận cọc -->
      <div
        v-if="enrollment?.is_deposit_paid"
        class="bg-paper border border-brand-600 rounded-2xl p-8 md:p-12 text-center shadow-[var(--shadow-md)]"
      >
        <div class="size-16 mx-auto bg-brand-50 rounded-full flex items-center justify-center mb-6">
          <PhCheckCircle weight="fill" class="size-10 text-brand-700" />
        </div>
        <h1 class="text-3xl md:text-5xl font-bold tracking-tight">Đã nhận cọc</h1>
        <p class="mt-4 text-lg text-ink-60 max-w-[50ch] mx-auto">
          Cảm ơn anh/chị <span class="font-semibold text-ink">{{ enrollment.student_name }}</span>.
          Hệ thống đã xác nhận khoản đặt cọc cho đơn <span class="num-display font-mono text-ink">{{ enrollment.code }}</span>.
          Tư vấn viên sẽ liên hệ trong thời gian sớm nhất để hướng dẫn bước tiếp theo.
        </p>

        <div class="mt-10 grid grid-cols-2 gap-4 max-w-md mx-auto text-left">
          <div class="border-l-2 border-brand-600 pl-4">
            <div class="text-xs text-ink-40 uppercase tracking-wider">Khóa học</div>
            <div class="font-semibold text-ink mt-1">{{ enrollment.course_title }}</div>
          </div>
          <div class="border-l-2 border-brand-600 pl-4">
            <div class="text-xs text-ink-40 uppercase tracking-wider">Đã đóng</div>
            <div class="font-semibold text-ink num-display mt-1">{{ formatVND(enrollment.paid_amount) }}</div>
          </div>
        </div>

        <div v-if="site?.hotline" class="mt-10">
          <a :href="`tel:${site.hotline}`" class="btn-secondary">
            Gọi tư vấn viên: {{ site.hotline_display || site.hotline }}
          </a>
        </div>
      </div>

      <!-- Chưa cọc → hiển thị QR + polling -->
      <div v-else class="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <!-- Bên trái: QR + bank info -->
        <div class="lg:col-span-7">
          <div class="bg-paper border border-line-base rounded-2xl p-6 md:p-10 shadow-[var(--shadow-soft)]">
            <div class="eyebrow mb-3">Đặt cọc giữ chỗ</div>
            <h1 class="text-3xl md:text-4xl font-bold tracking-tight leading-[1.1]">
              Quét QR để chuyển khoản
            </h1>
            <p class="mt-3 text-ink-60 leading-relaxed max-w-[55ch]">
              Mở app ngân hàng, chọn quét QR. Hệ thống tự xác nhận trong vòng 2 phút.
              Trang này tự cập nhật khi cọc thành công.
            </p>

            <div class="mt-8 flex flex-col md:flex-row gap-6 md:gap-8 items-start">
              <div v-if="qr?.qr_url" class="shrink-0">
                <div class="bg-paper border border-line-base p-3 rounded-xl">
                  <NuxtImg
                    :src="qr.qr_url" alt="Mã QR chuyển khoản đặt cọc"
                    width="280" height="280" loading="eager"
                    class="size-[220px] md:size-[260px] object-contain"
                  />
                </div>
              </div>

              <div class="flex-1 min-w-0">
                <h2 class="text-sm font-semibold uppercase tracking-wider text-ink-40 mb-4">Thông tin chuyển khoản</h2>
                <dl class="space-y-3">
                  <div class="flex items-start justify-between gap-3 pb-3 border-b border-line-soft">
                    <div>
                      <dt class="text-sm text-ink-60">Ngân hàng</dt>
                      <dd class="font-medium mt-0.5 flex items-center gap-2">
                        <PhBank class="size-4 text-brand-700" />
                        {{ qr?.bank_code }}
                      </dd>
                    </div>
                  </div>
                  <div class="flex items-start justify-between gap-3 pb-3 border-b border-line-soft">
                    <div class="min-w-0">
                      <dt class="text-sm text-ink-60">Số tài khoản</dt>
                      <dd class="font-mono text-lg mt-0.5 break-all">{{ qr?.account_number }}</dd>
                    </div>
                    <button @click="copy('Số tài khoản', qr!.account_number)" class="text-ink-60 hover:text-brand-700 p-2 shrink-0" aria-label="Sao chép số tài khoản">
                      <PhCopy class="size-5" />
                    </button>
                  </div>
                  <div class="flex items-start justify-between gap-3 pb-3 border-b border-line-soft">
                    <div class="min-w-0">
                      <dt class="text-sm text-ink-60">Chủ tài khoản</dt>
                      <dd class="font-medium mt-0.5">{{ qr?.account_name }}</dd>
                    </div>
                  </div>
                  <div class="flex items-start justify-between gap-3 pb-3 border-b border-line-soft">
                    <div>
                      <dt class="text-sm text-ink-60">Số tiền cọc</dt>
                      <dd class="font-bold text-2xl num-display mt-0.5 text-brand-700">{{ formatVND(qr?.amount || 0) }}</dd>
                    </div>
                  </div>
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <dt class="text-sm text-ink-60">Nội dung chuyển khoản <span class="text-red-700">*</span></dt>
                      <dd class="font-mono font-semibold text-lg mt-0.5 text-ink break-all">{{ qr?.add_info }}</dd>
                      <p class="text-xs text-ink-60 mt-2 leading-relaxed">
                        Bắt buộc giữ nguyên nội dung để hệ thống tự nhận diện đơn của anh/chị.
                      </p>
                    </div>
                    <button @click="copy('Nội dung', qr!.add_info)" class="text-ink-60 hover:text-brand-700 p-2 shrink-0" aria-label="Sao chép nội dung chuyển khoản">
                      <PhCopy class="size-5" />
                    </button>
                  </div>
                </dl>
                <p v-if="copied" class="mt-4 text-sm text-brand-700">Đã sao chép {{ copied }}.</p>
              </div>
            </div>

            <div class="mt-8 flex items-center gap-2 text-sm text-ink-60 bg-paper-alt rounded-lg p-4 border border-line-soft">
              <PhSpinnerGap class="size-4 animate-spin text-brand-700" weight="bold" />
              <span>Đang theo dõi giao dịch tự động (cập nhật mỗi 3 giây)…</span>
              <button @click="refresh()" class="ml-auto inline-flex items-center gap-1 text-brand-700 hover:text-brand-800 font-medium">
                <PhArrowClockwise class="size-4" weight="bold" />
                Kiểm tra ngay
              </button>
            </div>
          </div>
        </div>

        <!-- Bên phải: thông tin đơn + tiến độ -->
        <aside class="lg:col-span-5">
          <div class="bg-paper border border-line-base rounded-2xl p-6 md:p-8 shadow-[var(--shadow-soft)]">
            <div class="eyebrow mb-3">Đơn ghi danh</div>
            <h3 class="text-2xl font-bold tracking-tight mb-1 font-mono">{{ enrollment.code }}</h3>
            <p class="text-ink-60">{{ enrollment.course_title }}</p>

            <dl class="mt-6 space-y-4 text-sm">
              <div class="flex justify-between gap-3">
                <dt class="text-ink-60">Học viên</dt>
                <dd class="font-medium text-ink text-right">{{ enrollment.student_name }}</dd>
              </div>
              <div class="flex justify-between gap-3">
                <dt class="text-ink-60">Học phí trọn khóa</dt>
                <dd class="font-medium num-display text-right">{{ formatVND(enrollment.tuition_fee) }}</dd>
              </div>
              <div class="flex justify-between gap-3">
                <dt class="text-ink-60">Đã đóng</dt>
                <dd class="font-medium num-display text-right">{{ formatVND(enrollment.paid_amount) }}</dd>
              </div>
              <div class="flex justify-between gap-3 pt-4 border-t border-line-soft">
                <dt class="text-ink-60 font-medium">Cọc còn thiếu</dt>
                <dd class="font-bold num-display text-right text-brand-700">{{ formatVND(remaining) }}</dd>
              </div>
            </dl>

            <div class="mt-6 inline-flex items-center gap-2 bg-paper-alt rounded-full px-3 py-1.5 text-xs font-medium">
              <PhWallet class="size-3.5 text-brand-700" />
              {{ enrollment.status_display }}
            </div>
          </div>

          <div class="mt-5 bg-paper border border-line-base rounded-2xl p-6 md:p-8">
            <div class="flex gap-3 items-start">
              <PhInfo class="size-5 text-brand-700 shrink-0 mt-0.5" />
              <div class="text-sm text-ink-60 leading-relaxed">
                Nếu chuyển khoản hơn 5 phút mà chưa được xác nhận, vui lòng gọi
                <span v-if="site?.hotline" class="font-medium text-ink">{{ site.hotline_display || site.hotline }}</span>
                <span v-else class="font-medium text-ink">hotline trung tâm</span>
                để được hỗ trợ.
              </div>
            </div>
          </div>
        </aside>
      </div>

    </div>
  </section>
</template>
