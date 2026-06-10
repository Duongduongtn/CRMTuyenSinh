<script setup lang="ts">
import { PhArrowLeft, PhArrowRight, PhGraduationCap, PhShieldCheck, PhSpinnerGap } from '@phosphor-icons/vue'

definePageMeta({ layout: false })

const { requestOtp, verifyOtp, isAuthenticated } = useAuth()
const route = useRoute()

onMounted(() => {
  if (isAuthenticated.value) navigateTo(getNextPath())
})

const getNextPath = () => {
  const next = route.query.next
  if (typeof next === 'string' && next.startsWith('/')) return next
  return '/dashboard'
}

type Step = 'phone' | 'otp'
const step = ref<Step>('phone')

const phone = ref('')
const otp = ref('')
const loading = ref(false)
const errorMsg = ref('')
const countdown = ref(0)

let timerId: ReturnType<typeof setInterval> | null = null
const startCountdown = (secs: number) => {
  countdown.value = secs
  if (timerId) clearInterval(timerId)
  timerId = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0 && timerId) {
      clearInterval(timerId)
      timerId = null
    }
  }, 1000)
}

onBeforeUnmount(() => {
  if (timerId) clearInterval(timerId)
})

const normalizePhoneLocal = (raw: string): string => {
  const s = raw.replace(/[\s.\-()]/g, '')
  if (s.startsWith('+84')) return '0' + s.slice(3)
  if (/^84\d{9,10}$/.test(s)) return '0' + s.slice(2)
  return s
}

const isValidPhone = computed(() => /^0\d{9}$/.test(normalizePhoneLocal(phone.value)))
const isValidOtp = computed(() => /^\d{6}$/.test(otp.value))

const submitPhone = async () => {
  errorMsg.value = ''
  if (!isValidPhone.value) {
    errorMsg.value = 'Số điện thoại không hợp lệ. Định dạng đúng: 10 số, bắt đầu bằng 0.'
    return
  }
  loading.value = true
  try {
    const resp = await requestOtp(normalizePhoneLocal(phone.value))
    step.value = 'otp'
    startCountdown(resp.expires_in_seconds || 300)
    nextTick(() => {
      const el = document.getElementById('otp-input')
      el?.focus()
    })
  } catch (err: any) {
    errorMsg.value = parseError(err) || 'Không gửi được mã. Vui lòng thử lại.'
  } finally {
    loading.value = false
  }
}

const submitOtp = async () => {
  errorMsg.value = ''
  if (!isValidOtp.value) {
    errorMsg.value = 'Vui lòng nhập đủ 6 chữ số.'
    return
  }
  loading.value = true
  try {
    await verifyOtp(normalizePhoneLocal(phone.value), otp.value)
    navigateTo(getNextPath())
  } catch (err: any) {
    errorMsg.value = parseError(err) || 'Mã không đúng hoặc đã hết hạn.'
  } finally {
    loading.value = false
  }
}

const parseError = (err: any): string => {
  const data = err?.response?._data || err?.data
  if (data?.detail) return data.detail
  if (data?.phone?.[0]) return data.phone[0]
  if (data?.code?.[0]) return data.code[0]
  return ''
}

const goBack = () => {
  step.value = 'phone'
  otp.value = ''
  errorMsg.value = ''
}

const resendOtp = async () => {
  if (countdown.value > 240) return
  await submitPhone()
}

useHead({
  title: 'Đăng nhập · Học viên',
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-paper">
    <div class="flex-1 flex items-center justify-center px-4 py-8">
      <div class="w-full max-w-narrow">
        <div class="text-center mb-8">
          <div class="inline-flex size-14 bg-brand-700 text-white rounded-xl items-center justify-center mb-4">
            <PhGraduationCap class="size-7" weight="bold" />
          </div>
          <h1 class="text-2xl font-bold tracking-tight">Đăng nhập học viên</h1>
          <p class="text-ink-60 mt-2 text-sm leading-relaxed">
            Đăng nhập bằng số điện thoại đã đăng ký khóa học.
            <br>Không cần mật khẩu.
          </p>
        </div>

        <div class="card-base">
          <form v-if="step === 'phone'" @submit.prevent="submitPhone">
            <label for="phone" class="block text-sm font-semibold mb-2">Số điện thoại</label>
            <input
              id="phone"
              v-model="phone"
              type="tel"
              inputmode="tel"
              autocomplete="tel"
              class="input-base num-display"
              placeholder="0903456789"
              maxlength="15"
              :disabled="loading"
              autofocus
            >
            <p v-if="errorMsg" class="mt-2 text-sm text-danger">{{ errorMsg }}</p>
            <button
              type="submit"
              class="btn-primary w-full mt-4"
              :disabled="loading || !isValidPhone"
            >
              <PhSpinnerGap v-if="loading" class="size-5 animate-spin" />
              <span v-else>Gửi mã xác thực</span>
              <PhArrowRight v-if="!loading" class="size-5" />
            </button>
          </form>

          <form v-else @submit.prevent="submitOtp">
            <button
              type="button"
              class="text-ink-60 hover:text-ink text-sm inline-flex items-center gap-1 mb-3"
              @click="goBack"
            >
              <PhArrowLeft class="size-4" />
              Đổi số điện thoại
            </button>
            <label for="otp-input" class="block text-sm font-semibold mb-2">Mã xác thực</label>
            <p class="text-xs text-ink-60 mb-3">
              Đã gửi mã 6 số tới Zalo của
              <span class="font-semibold text-ink num-display">{{ normalizePhoneLocal(phone) }}</span>.
              <span v-if="countdown > 0">Hết hạn sau <span class="num-display">{{ Math.floor(countdown / 60) }}:{{ String(countdown % 60).padStart(2, '0') }}</span>.</span>
            </p>
            <input
              id="otp-input"
              v-model="otp"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              class="input-base num-display text-center text-2xl tracking-[0.4em] font-bold"
              placeholder="------"
              maxlength="6"
              pattern="\d{6}"
              :disabled="loading"
            >
            <p v-if="errorMsg" class="mt-2 text-sm text-danger">{{ errorMsg }}</p>
            <button
              type="submit"
              class="btn-primary w-full mt-4"
              :disabled="loading || !isValidOtp"
            >
              <PhSpinnerGap v-if="loading" class="size-5 animate-spin" />
              <span v-else>Xác nhận đăng nhập</span>
            </button>
            <button
              type="button"
              class="block w-full mt-3 text-sm text-ink-60 hover:text-brand-700 transition py-2"
              :disabled="loading || countdown > 240"
              @click="resendOtp"
            >
              <span v-if="countdown > 240">
                Gửi lại mã sau <span class="num-display">{{ countdown - 240 }}s</span>
              </span>
              <span v-else>Gửi lại mã</span>
            </button>
          </form>
        </div>

        <div class="mt-6 flex items-center justify-center gap-2 text-xs text-ink-60">
          <PhShieldCheck class="size-4 text-brand-700" />
          Bảo mật bằng OTP · không lưu mật khẩu
        </div>
      </div>
    </div>
  </div>
</template>
