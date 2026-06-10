<script setup lang="ts">
import {
  PhPhone,
  PhEnvelope,
  PhMapPin,
  PhClock,
  PhChatCircleText,
  PhFacebookLogo,
  PhPaperPlaneTilt,
  PhCheckCircle,
} from '@phosphor-icons/vue'

const { data: site } = await useSiteSettings()
const { data: courses } = await useCourses()
useReveal()

useSeoMeta({
  title: 'Liên hệ tư vấn',
  description: site.value?.description
    ? `Liên hệ ${site.value.brand_name} để được tư vấn miễn phí về khóa học lái xe.`
    : 'Liên hệ trung tâm để được tư vấn miễn phí về khóa học lái xe.',
})

const form = reactive({ name: '', phone: '', course: '', notes: '' })
const submitting = ref(false)
const submitted = ref(false)
const errorMsg = ref('')

const isValidPhone = (p: string) => /^0\d{9}$/.test(p.replace(/\s/g, ''))

const submitLead = async () => {
  errorMsg.value = ''
  if (!form.name.trim()) {
    errorMsg.value = 'Vui lòng nhập họ tên.'
    return
  }
  if (!isValidPhone(form.phone)) {
    errorMsg.value = 'Số điện thoại không hợp lệ. Định dạng đúng: 10 số bắt đầu bằng 0.'
    return
  }
  submitting.value = true
  try {
    const { public: { apiBase } } = useRuntimeConfig()
    await $fetch(`${apiBase}/leads/capture`, {
      method: 'POST',
      body: {
        name: form.name.trim(),
        phone: form.phone.trim(),
        source: 'web',
        vehicle_class: form.course || '',
        notes: form.notes.trim(),
      },
    })
    submitted.value = true
  } catch (err: any) {
    errorMsg.value = err?.data?.detail || 'Không gửi được. Vui lòng gọi hotline.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <!-- Hero -->
    <section class="container-base pt-14 md:pt-20 pb-10">
      <p class="eyebrow mb-3">Liên hệ tư vấn</p>
      <h1 class="text-3xl md:text-5xl font-bold tracking-tighter mb-4 max-w-3xl">
        Để lại số, tư vấn viên gọi lại trong 5 phút
      </h1>
      <p class="text-base md:text-lg text-ink-60 leading-relaxed max-w-2xl">
        Hoặc gọi hotline trực tiếp, nhắn Zalo. Trung tâm phục vụ
        {{ site?.working_hours_text || 'từ 7:30 đến 18:00 các ngày trong tuần' }}.
      </p>
    </section>

    <!-- Grid: form + contact info -->
    <section class="container-base pb-20">
      <div class="grid lg:grid-cols-12 gap-8 lg:gap-12">
        <!-- Form -->
        <div class="lg:col-span-7 reveal">
          <div class="card-base !p-6 md:!p-8 bg-paper border border-line-base rounded-xl">
            <h2 class="text-2xl font-bold tracking-tight mb-2">Đăng ký tư vấn</h2>
            <p class="text-sm text-ink-60 mb-6">
              Thông tin được bảo mật. Không SPAM, không gọi quảng cáo nhiều lần.
            </p>

            <div v-if="submitted" class="bg-brand-50 border border-brand-200 rounded-md p-5 text-center">
              <PhCheckCircle class="size-10 text-brand-700 mx-auto mb-3" weight="fill" />
              <h3 class="font-bold text-lg mb-1">Đã ghi nhận yêu cầu</h3>
              <p class="text-sm text-ink-60">
                Tư vấn viên sẽ gọi lại trong vòng 5 phút.
                <br>Cảm ơn bạn đã liên hệ.
              </p>
            </div>

            <form v-else class="space-y-4" @submit.prevent="submitLead">
              <div>
                <label for="name" class="block text-sm font-semibold mb-1.5">Họ và tên *</label>
                <input
                  id="name"
                  v-model="form.name"
                  type="text"
                  autocomplete="name"
                  required
                  class="w-full px-4 py-3 min-h-12 text-base border border-line-base rounded-md focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-700/20 transition"
                  placeholder="Nguyễn Văn A"
                  :disabled="submitting"
                >
              </div>

              <div>
                <label for="phone" class="block text-sm font-semibold mb-1.5">Số điện thoại *</label>
                <input
                  id="phone"
                  v-model="form.phone"
                  type="tel"
                  inputmode="tel"
                  autocomplete="tel"
                  required
                  class="w-full px-4 py-3 min-h-12 text-base num-display border border-line-base rounded-md focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-700/20 transition"
                  placeholder="0903456789"
                  :disabled="submitting"
                >
              </div>

              <div>
                <label for="course" class="block text-sm font-semibold mb-1.5">Hạng quan tâm</label>
                <select
                  id="course"
                  v-model="form.course"
                  class="w-full px-4 py-3 min-h-12 text-base border border-line-base rounded-md focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-700/20 transition bg-paper"
                  :disabled="submitting"
                >
                  <option value="">Chưa rõ — tư vấn giúp</option>
                  <option v-for="c in courses?.results || []" :key="c.id" :value="c.vehicle_class">
                    {{ c.vehicle_class_display }}
                  </option>
                </select>
              </div>

              <div>
                <label for="notes" class="block text-sm font-semibold mb-1.5">Ghi chú (tùy chọn)</label>
                <textarea
                  id="notes"
                  v-model="form.notes"
                  rows="3"
                  class="w-full px-4 py-3 text-base border border-line-base rounded-md focus:border-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-700/20 transition resize-none"
                  placeholder="Ví dụ: Muốn học buổi tối, đã có bằng A1 cần nâng hạng…"
                  :disabled="submitting"
                />
              </div>

              <p v-if="errorMsg" class="text-sm text-danger bg-danger/5 p-3 rounded-md">{{ errorMsg }}</p>

              <button type="submit" class="btn-emerald w-full" :disabled="submitting">
                <PhPaperPlaneTilt v-if="!submitting" class="size-5" />
                <span>{{ submitting ? 'Đang gửi…' : 'Gửi đăng ký' }}</span>
              </button>
            </form>
          </div>
        </div>

        <!-- Contact info -->
        <aside class="lg:col-span-5 reveal">
          <h2 class="text-xl font-bold tracking-tight mb-5">Cách khác để liên hệ</h2>

          <ul class="space-y-4 mb-8">
            <li v-if="site?.hotline" class="flex gap-3 items-start">
              <div class="size-10 bg-brand-50 text-brand-700 rounded-full flex items-center justify-center shrink-0">
                <PhPhone class="size-5" weight="bold" />
              </div>
              <div>
                <p class="text-xs text-ink-40 uppercase tracking-wider mb-0.5">Hotline 24/7</p>
                <a :href="`tel:${site.hotline}`" class="font-semibold text-lg num-display hover:text-brand-700 transition">
                  {{ site.hotline_display || site.hotline }}
                </a>
              </div>
            </li>
            <li v-if="site?.email" class="flex gap-3 items-start">
              <div class="size-10 bg-brand-50 text-brand-700 rounded-full flex items-center justify-center shrink-0">
                <PhEnvelope class="size-5" weight="bold" />
              </div>
              <div>
                <p class="text-xs text-ink-40 uppercase tracking-wider mb-0.5">Email</p>
                <a :href="`mailto:${site.email}`" class="font-semibold hover:text-brand-700 transition break-all">
                  {{ site.email }}
                </a>
              </div>
            </li>
            <li v-if="site?.zalo_url" class="flex gap-3 items-start">
              <div class="size-10 bg-brand-50 text-brand-700 rounded-full flex items-center justify-center shrink-0">
                <PhChatCircleText class="size-5" weight="bold" />
              </div>
              <div>
                <p class="text-xs text-ink-40 uppercase tracking-wider mb-0.5">Zalo OA</p>
                <a :href="site.zalo_url" target="_blank" rel="noopener" class="font-semibold hover:text-brand-700 transition">
                  Nhắn tin Zalo
                </a>
              </div>
            </li>
            <li v-if="site?.facebook_url" class="flex gap-3 items-start">
              <div class="size-10 bg-brand-50 text-brand-700 rounded-full flex items-center justify-center shrink-0">
                <PhFacebookLogo class="size-5" weight="bold" />
              </div>
              <div>
                <p class="text-xs text-ink-40 uppercase tracking-wider mb-0.5">Facebook</p>
                <a :href="site.facebook_url" target="_blank" rel="noopener" class="font-semibold hover:text-brand-700 transition">
                  Theo dõi Fanpage
                </a>
              </div>
            </li>
          </ul>

          <div v-if="site?.address_line || site?.address_full" class="card-base mb-4">
            <div class="flex gap-3 items-start mb-3">
              <PhMapPin class="size-5 text-brand-700 mt-0.5 shrink-0" />
              <div>
                <p class="text-xs text-ink-40 uppercase tracking-wider mb-1">Địa chỉ trung tâm</p>
                <p class="font-medium leading-relaxed">{{ site.address_full || site.address_line }}</p>
              </div>
            </div>
            <div v-if="site.working_hours_text" class="flex gap-3 items-start">
              <PhClock class="size-5 text-brand-700 mt-0.5 shrink-0" />
              <div>
                <p class="text-xs text-ink-40 uppercase tracking-wider mb-1">Giờ làm việc</p>
                <p class="font-medium leading-relaxed">{{ site.working_hours_text }}</p>
              </div>
            </div>
          </div>

          <div v-if="site?.map_embed_url" class="rounded-xl overflow-hidden border border-line-base">
            <iframe
              :src="site.map_embed_url"
              loading="lazy"
              title="Bản đồ trung tâm"
              referrerpolicy="no-referrer-when-downgrade"
              class="w-full h-64 border-0"
            />
          </div>
        </aside>
      </div>
    </section>
  </div>
</template>
