<script setup lang="ts">
import { PhArrowRight, PhGraduationCap, PhIdentificationCard, PhPhoneCall, PhShieldCheck, PhSpinnerGap } from '@phosphor-icons/vue'

definePageMeta({ layout: false })

const { login, isAuthenticated } = useAuth()
const route = useRoute()

onMounted(() => {
  if (isAuthenticated.value) navigateTo(getNextPath())
})

const getNextPath = () => {
  const next = route.query.next
  if (typeof next === 'string' && next.startsWith('/')) return next
  return '/dashboard'
}

const phone = ref('')
const last6 = ref('')
const loading = ref(false)
const errorMsg = ref('')
const lockSeconds = ref(0)

let lockTimerId: ReturnType<typeof setInterval> | null = null

const startLockCountdown = (secs: number) => {
  lockSeconds.value = secs
  if (lockTimerId) clearInterval(lockTimerId)
  lockTimerId = setInterval(() => {
    lockSeconds.value -= 1
    if (lockSeconds.value <= 0 && lockTimerId) {
      clearInterval(lockTimerId)
      lockTimerId = null
    }
  }, 1000)
}

onBeforeUnmount(() => {
  if (lockTimerId) clearInterval(lockTimerId)
})

const normalizePhoneLocal = (raw: string): string => {
  const s = raw.replace(/[\s.\-()]/g, '')
  if (s.startsWith('+84')) return '0' + s.slice(3)
  if (/^84\d{9,10}$/.test(s)) return '0' + s.slice(2)
  return s
}

const isValidPhone = computed(() => /^0\d{9}$/.test(normalizePhoneLocal(phone.value)))
const isValidLast6 = computed(() => /^\d{6}$/.test(last6.value))
const isLocked = computed(() => lockSeconds.value > 0)
const canSubmit = computed(() => isValidPhone.value && isValidLast6.value && !isLocked.value)

const lockCountdownLabel = computed(() => {
  const s = lockSeconds.value
  if (s <= 0) return ''
  if (s >= 3600) {
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    return `${h} giờ ${m.toString().padStart(2, '0')} phút`
  }
  if (s >= 60) {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m} phút ${sec.toString().padStart(2, '0')} giây`
  }
  return `${s} giây`
})

const handleLast6Input = (event: Event) => {
  const target = event.target as HTMLInputElement
  last6.value = target.value.replace(/\D/g, '').slice(0, 6)
}

const submit = async () => {
  errorMsg.value = ''
  if (!isValidPhone.value) {
    errorMsg.value = 'Số điện thoại không hợp lệ. Vui lòng nhập 10 số, bắt đầu bằng 0.'
    return
  }
  if (!isValidLast6.value) {
    errorMsg.value = 'Vui lòng nhập đủ 6 số cuối CCCD.'
    return
  }

  loading.value = true
  try {
    await login(normalizePhoneLocal(phone.value), last6.value)
    navigateTo(getNextPath())
  }
  catch (err: any) {
    const data = err?.response?._data || err?.data
    const status = err?.response?.status
    if (status === 423 && data?.remaining_seconds) {
      startLockCountdown(data.remaining_seconds)
      errorMsg.value = data.detail || 'Tài khoản đang tạm khóa. Vui lòng thử lại sau.'
    }
    else if (status === 429) {
      errorMsg.value = 'Bạn đã thử quá nhiều lần. Vui lòng đợi một lúc rồi đăng nhập lại.'
    }
    else if (data?.detail) {
      errorMsg.value = data.detail
    }
    else {
      errorMsg.value = 'Đăng nhập không thành công. Vui lòng kiểm tra mạng và thử lại.'
    }
  }
  finally {
    loading.value = false
  }
}

useHead({
  title: 'Đăng nhập học viên',
  meta: [
    { name: 'description', content: 'Đăng nhập khu vực học viên bằng số điện thoại và 6 số cuối CCCD đã đăng ký.' },
  ],
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-paper">
    <div class="flex-1 flex items-center justify-center px-4 py-10">
      <div class="w-full max-w-narrow">
        <div class="text-center mb-8">
          <div class="inline-flex size-14 bg-brand-700 text-white rounded-xl items-center justify-center mb-4">
            <PhGraduationCap class="size-7" weight="bold" />
          </div>
          <h1 class="text-2xl font-bold tracking-tight">
            Đăng nhập học viên
          </h1>
          <p class="text-ink-60 mt-2 text-sm leading-relaxed">
            Đăng nhập bằng số điện thoại đã đăng ký khóa học và 6 số cuối CCCD.
          </p>
        </div>

        <div class="card-base">
          <form @submit.prevent="submit">
            <label for="phone" class="block text-sm font-semibold mb-2">
              Số điện thoại
            </label>
            <div class="relative">
              <PhPhoneCall class="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-ink-40" />
              <input
                id="phone"
                v-model="phone"
                type="tel"
                inputmode="tel"
                autocomplete="tel"
                class="input-base num-display pl-10"
                placeholder="0903456789"
                maxlength="15"
                :disabled="loading || isLocked"
                autofocus
              >
            </div>

            <label for="last6" class="block text-sm font-semibold mt-5 mb-2">
              6 số cuối CCCD
            </label>
            <div class="relative">
              <PhIdentificationCard class="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-ink-40" />
              <input
                id="last6"
                :value="last6"
                type="text"
                inputmode="numeric"
                autocomplete="off"
                class="input-base num-display px-10 text-xl tracking-[0.4em] font-bold text-center"
                placeholder=""
                maxlength="6"
                pattern="\d{6}"
                :disabled="loading || isLocked"
                @input="handleLast6Input"
              >
            </div>
            <p class="mt-2 text-xs text-ink-60 leading-relaxed">
              Lấy 6 số cuối trên thẻ căn cước công dân hoặc CMND đã nộp cho trung tâm.
            </p>

            <div
              v-if="errorMsg"
              class="mt-4 px-3 py-2 rounded-md text-sm text-danger bg-danger-soft border border-danger/10"
              role="alert"
            >
              {{ errorMsg }}
              <div v-if="isLocked" class="mt-1 text-xs text-danger/80 num-display">
                Mở lại sau {{ lockCountdownLabel }}.
              </div>
            </div>

            <button
              type="submit"
              class="btn-primary w-full mt-5"
              :disabled="loading || !canSubmit"
            >
              <PhSpinnerGap v-if="loading" class="size-5 animate-spin" />
              <span v-else>Đăng nhập</span>
              <PhArrowRight v-if="!loading" class="size-5" />
            </button>
          </form>
        </div>

        <div class="mt-6 flex flex-col items-center gap-3 text-xs text-ink-60">
          <div class="flex items-center gap-2">
            <PhShieldCheck class="size-4 text-brand-700" />
            Bảo mật bằng định danh SĐT và CCCD
          </div>
          <p class="text-center leading-relaxed">
            Chưa đăng nhập được? Vui lòng liên hệ trung tâm để cập nhật CCCD trong hồ sơ.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
