<script setup lang="ts">
import {
  PhArrowRight,
  PhShieldCheck,
  PhBookOpenText,
  PhGraduationCap,
  PhMapPinArea,
  PhCalendarCheck,
  PhDeviceMobile,
  PhCheckCircle,
  PhMapPin,
  PhPhone,
  PhChatCircleText,
  PhClock,
  PhQrCode,
  PhCoins,
  PhPlus,
} from '@phosphor-icons/vue'
import { useSiteSettings } from '~/composables/useSiteSettings'
import { useCourses } from '~/composables/useCourses'

const { data: site } = await useSiteSettings()
const { data: courses } = await useCourses()
useReveal()

const featured = computed(() => courses.value?.results ?? [])

const stats = computed(() => [
  { num: site.value?.stat_students_count ?? 0, suffix: '', label: 'học viên đã đỗ', format: 'number' },
  { num: site.value?.stat_pass_rate_percent ?? 0, suffix: '%', label: 'tỉ lệ đỗ lần đầu', format: 'plain' },
  { num: site.value?.stat_years_experience ?? 0, suffix: ' năm', label: 'kinh nghiệm đào tạo', format: 'plain' },
  { num: site.value?.stat_practice_area_m2 ?? 0, suffix: 'm²', label: 'sân tập riêng', format: 'number' },
])
const formatStat = (n: number, mode: string) =>
  mode === 'number' ? new Intl.NumberFormat('vi-VN').format(n) : String(n)

const advantages = [
  { icon: PhShieldCheck, title: 'Cam kết hoàn cọc trong 7 ngày', desc: 'Hủy đăng ký trước ngày khai giảng 7 ngày, hoàn cọc nguyên vẹn. Không cần lý do.' },
  { icon: PhBookOpenText, title: 'Tài liệu cập nhật Luật 2025', desc: '600 câu lý thuyết biên soạn sát đề thi sát hạch hiện hành.' },
  { icon: PhGraduationCap, title: 'Huấn luyện viên dày kinh nghiệm', desc: 'Trung bình hơn 10 năm dạy lái. Lý lịch nghiệp vụ minh bạch.' },
  { icon: PhMapPinArea, title: 'Sân tập riêng đủ 11 bài sa hình', desc: 'Không phải xếp lượt chờ chung với trung tâm khác.' },
  { icon: PhCalendarCheck, title: 'Lịch linh hoạt tối và cuối tuần', desc: 'Tự chọn ca trong ứng dụng học viên. Phù hợp người đi làm.' },
  { icon: PhDeviceMobile, title: 'Theo dõi tiến độ qua app', desc: 'Xem hồ sơ thiếu, công nợ và kết quả thi thử mọi lúc.' },
]

const process = [
  { n: '01', title: 'Tư vấn và đặt cọc', desc: 'Gọi hotline hoặc để lại số. Tư vấn viên gọi lại trong 5 phút. Cọc qua QR ngân hàng.' },
  { n: '02', title: 'Hoàn thiện hồ sơ', desc: 'Chụp CCCD, ảnh chân dung, giấy khám sức khỏe qua app. Văn thư duyệt trong 1 ngày.' },
  { n: '03', title: 'Học lý thuyết và thực hành', desc: 'Tự chọn ca trong app. Theo dõi tiến độ và công nợ ngay trên điện thoại.' },
  { n: '04', title: 'Thi sát hạch, nhận GPLX', desc: 'Trung tâm hỗ trợ làm hồ sơ thi. Nhận bằng sau 7 đến 10 ngày làm việc.' },
]

const faqs = [
  { q: 'Học bao lâu thì có bằng?', a: 'Tùy hạng. Hạng A1 khoảng 2 tuần. Hạng B số sàn và B số tự động khoảng 4 tháng tính từ ngày khai giảng tới khi nhận bằng. Hạng C và D dài hơn, 5 đến 6 tháng.', open: true },
  { q: 'Hồ sơ cần những gì?', a: 'CCCD 2 mặt, ảnh chân dung 4x6, giấy khám sức khỏe theo mẫu Bộ Y tế (khám tại bệnh viện liên kết của trung tâm). Khóa nâng hạng cần thêm bản photo bằng lái cũ.' },
  { q: 'Có thể đóng cọc trước rồi đóng phần còn lại sau không?', a: 'Có. Cọc giữ chỗ tối thiểu 200.000đ. Phần còn lại đóng theo nhiều đợt suốt khóa học. Lịch đóng cụ thể có trong hợp đồng và hiển thị trong ứng dụng học viên.' },
  { q: 'Có lớp buổi tối hoặc cuối tuần không?', a: 'Có. Lớp lý thuyết mở vào tối thứ Hai, Tư, Sáu và sáng Chủ nhật. Lịch thực hành chọn ca trong app.' },
  { q: 'Phí thi lại nếu trượt là bao nhiêu?', a: 'Phí thi lại do Sở Giao thông Vận tải quy định. Trung tâm hỗ trợ làm lại hồ sơ thi miễn phí.' },
]

const form = reactive({ name: '', phone: '', course: '' })
const submitting = ref(false)
const submitMessage = ref('')

const submitLead = async () => {
  submitMessage.value = ''
  if (!form.phone || !/^0\d{9}$/.test(form.phone)) {
    submitMessage.value = 'Số điện thoại không hợp lệ. Định dạng đúng: 10 số bắt đầu bằng 0.'
    return
  }
  submitting.value = true
  try {
    const { public: { apiBase } } = useRuntimeConfig()
    await $fetch(`${apiBase}/leads/capture`, {
      method: 'POST',
      body: {
        name: form.name || 'Học viên',
        phone: form.phone,
        source: 'web',
        notes: form.course ? `Quan tâm hạng: ${form.course}` : '',
      },
    })
    submitMessage.value = 'Đã ghi nhận. Tư vấn viên sẽ gọi lại trong 5 phút.'
    form.name = ''
    form.phone = ''
    form.course = ''
  } catch (e: any) {
    submitMessage.value = 'Có lỗi xảy ra. Vui lòng gọi hotline trực tiếp.'
  } finally {
    submitting.value = false
  }
}

// SEO + JSON-LD LocalBusiness + FAQPage
useSeoMeta({
  title: site.value?.meta_title_default || 'Học lái xe an toàn, đúng lộ trình',
  description:
    site.value?.meta_description_default ||
    site.value?.description ||
    'Trung tâm đào tạo lái xe chính quy. 9 hạng GPLX theo Luật 2025. Đặt cọc giữ chỗ chỉ 200.000đ.',
})

const siteUrl = useRuntimeConfig().public.siteUrl
const jsonLd = computed(() => ({
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'DrivingSchool',
      '@id': `${siteUrl}/#org`,
      name: site.value?.brand_name,
      description: site.value?.description,
      url: siteUrl,
      logo: site.value?.logo_url,
      image: site.value?.og_image_url || site.value?.logo_url,
      telephone: site.value?.hotline,
      email: site.value?.email,
      address: {
        '@type': 'PostalAddress',
        streetAddress: site.value?.address_line,
        addressLocality: site.value?.city,
        addressCountry: 'VN',
      },
      ...(site.value?.map_lat && site.value?.map_lng
        ? {
            geo: {
              '@type': 'GeoCoordinates',
              latitude: Number(site.value.map_lat),
              longitude: Number(site.value.map_lng),
            },
          }
        : {}),
      sameAs: [
        site.value?.facebook_url,
        site.value?.zalo_url,
        site.value?.youtube_url,
        site.value?.tiktok_url,
      ].filter(Boolean),
    },
    {
      '@type': 'FAQPage',
      mainEntity: faqs.map((f) => ({
        '@type': 'Question',
        name: f.q,
        acceptedAnswer: { '@type': 'Answer', text: f.a },
      })),
    },
  ],
}))

useHead({
  script: [
    {
      type: 'application/ld+json',
      innerHTML: () => JSON.stringify(jsonLd.value),
    },
  ],
})
</script>

<template>
  <!-- HERO -->
  <section class="border-b border-line-soft">
    <div class="container-base pt-16 md:pt-28 pb-16 md:pb-32">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
        <div class="lg:col-span-7 reveal">
          <div class="inline-flex items-center gap-2 eyebrow mb-7">
            <span class="size-1.5 bg-brand-600 rounded-full"></span>
            <span>Chính quy. Chuẩn Sở GTVT. {{ site?.stat_years_experience }} năm</span>
          </div>
          <h1 class="text-[40px] md:text-6xl lg:text-7xl font-bold tracking-tighter leading-[1.04]">
            Học lái xe<br>
            <span class="italic font-medium text-brand-700">đúng lộ trình,</span><br>
            không học vẹt.
          </h1>
          <p class="mt-7 md:mt-9 text-lg md:text-xl text-ink-60 leading-relaxed max-w-[58ch]">
            {{ site?.description || 'Trung tâm đào tạo trên 10.000 học viên trong 5 năm gần nhất. Huấn luyện viên trung bình hơn 10 năm kinh nghiệm.' }}
          </p>
          <div class="mt-9 md:mt-11 flex flex-wrap items-center gap-3">
            <NuxtLink to="/khoa-hoc" class="btn-primary">
              Xem khóa học
              <PhArrowRight class="size-4" weight="bold" />
            </NuxtLink>
            <a href="#lien-he" class="btn-secondary">Tư vấn miễn phí</a>
          </div>
        </div>
        <div class="lg:col-span-5 reveal">
          <div class="aspect-[4/5] overflow-hidden rounded-2xl bg-paper-tint">
            <NuxtImg
              src="https://images.unsplash.com/photo-1502877338535-766e1452684a?w=900&h=1125&fit=crop&q=85"
              alt="Huấn luyện viên hướng dẫn học viên trong xe tập tại sân tập của trung tâm"
              loading="eager"
              width="900"
              height="1125"
              class="size-full object-cover"
            />
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- TRUST STRIP -->
  <section class="border-b border-line-soft">
    <div class="container-base py-12 md:py-16">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-y-8 gap-x-4">
        <div v-for="s in stats" :key="s.label" class="border-l-2 border-brand-600 pl-5">
          <div class="text-4xl md:text-5xl font-bold num-display">
            {{ formatStat(s.num, s.format) }}<span class="text-2xl md:text-3xl text-ink-40">{{ s.suffix }}</span>
          </div>
          <div class="text-sm text-ink-60 mt-2">{{ s.label }}</div>
        </div>
      </div>
    </div>
  </section>

  <!-- KHÓA HỌC -->
  <section id="khoa-hoc" class="py-20 md:py-32 border-b border-line-soft">
    <div class="container-base">
      <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-14 reveal">
        <div class="max-w-2xl">
          <div class="eyebrow mb-4">Khóa học</div>
          <h2 class="text-4xl md:text-6xl font-bold tracking-tight leading-[1.05]">
            Chín hạng GPLX,<br>một trung tâm.
          </h2>
          <p class="mt-5 text-lg text-ink-60 leading-relaxed">
            Học phí công khai. Mở lớp liên tục. Không phụ phí phát sinh.
          </p>
        </div>
        <NuxtLink to="/khoa-hoc" class="btn-ghost whitespace-nowrap">
          Tất cả khóa học
          <PhArrowRight class="size-4" weight="bold" />
        </NuxtLink>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-7 reveal">
        <CourseCard v-for="c in featured" :key="c.id" :course="c" />
      </div>
    </div>
  </section>

  <!-- LỢI THẾ -->
  <section id="loi-the" class="py-20 md:py-32 bg-paper-tint border-b border-line-soft">
    <div class="container-base">
      <div class="max-w-3xl mb-14 reveal">
        <div class="eyebrow mb-4">Lợi thế</div>
        <h2 class="text-4xl md:text-6xl font-bold tracking-tight leading-[1.05]">
          Sáu điều bạn nhận được<br>khi học ở đây.
        </h2>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-line-base border border-line-base rounded-2xl overflow-hidden reveal">
        <div v-for="a in advantages" :key="a.title" class="bg-paper p-7 md:p-9">
          <div class="size-12 bg-brand-50 rounded-lg flex items-center justify-center mb-5">
            <component :is="a.icon" class="size-6 text-brand-700" />
          </div>
          <h3 class="text-lg font-bold mb-2">{{ a.title }}</h3>
          <p class="text-ink-60 leading-relaxed">{{ a.desc }}</p>
        </div>
      </div>
    </div>
  </section>

  <!-- QUY TRÌNH -->
  <section id="quy-trinh" class="py-20 md:py-32 border-b border-line-soft">
    <div class="container-base">
      <div class="max-w-3xl mb-14 reveal">
        <div class="eyebrow mb-4">Quy trình</div>
        <h2 class="text-4xl md:text-6xl font-bold tracking-tight leading-[1.05]">
          Bốn bước rõ ràng<br>từ đăng ký tới cầm bằng.
        </h2>
      </div>
      <div class="relative reveal">
        <div class="hidden lg:block absolute top-7 left-[12.5%] right-[12.5%] h-px bg-line-base"></div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10 md:gap-6 lg:gap-10">
          <div v-for="(step, i) in process" :key="step.n" class="relative">
            <div
              class="size-14 rounded-full flex items-center justify-center font-bold text-lg num-display relative z-10 border-2"
              :class="i === process.length - 1
                ? 'bg-brand-700 border-brand-700 text-white'
                : 'bg-paper border-ink text-ink'"
            >{{ step.n }}</div>
            <h3 class="font-bold text-lg mt-6 mb-2">{{ step.title }}</h3>
            <p class="text-ink-60 leading-relaxed">{{ step.desc }}</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- HỌC PHÍ MINH BẠCH -->
  <section class="py-20 md:py-32 bg-paper-alt border-b border-line-soft">
    <div class="container-base">
      <div class="max-w-3xl mb-14 reveal">
        <div class="eyebrow mb-4">Học phí minh bạch</div>
        <h2 class="text-4xl md:text-6xl font-bold tracking-tight leading-[1.05]">
          Đóng theo tiến độ,<br>không phụ phí.
        </h2>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5 md:gap-7 reveal">
        <div class="bg-paper border border-line-base rounded-2xl p-7 md:p-9">
          <div class="size-12 bg-brand-50 rounded-lg flex items-center justify-center mb-6">
            <PhQrCode class="size-6 text-brand-700" />
          </div>
          <h3 class="text-xl font-bold mb-3">Quét QR, tự động xác nhận</h3>
          <p class="text-ink-60 leading-relaxed">Tích hợp 7 ngân hàng lớn. Hệ thống xác nhận thanh toán trong 2 phút sau khi tiền vào.</p>
        </div>
        <div class="bg-paper border border-line-base rounded-2xl p-7 md:p-9">
          <div class="size-12 bg-brand-50 rounded-lg flex items-center justify-center mb-6">
            <PhCoins class="size-6 text-brand-700" />
          </div>
          <h3 class="text-xl font-bold mb-3">Đóng nhiều đợt</h3>
          <p class="text-ink-60 leading-relaxed">Cọc giữ chỗ chỉ 200.000đ. Phần còn lại đóng theo nhiều đợt suốt khóa, không áp lực tiền lúc đầu.</p>
        </div>
        <div class="bg-paper border border-line-base rounded-2xl p-7 md:p-9">
          <div class="size-12 bg-brand-50 rounded-lg flex items-center justify-center mb-6">
            <PhDeviceMobile class="size-6 text-brand-700" />
          </div>
          <h3 class="text-xl font-bold mb-3">Theo dõi công nợ trong app</h3>
          <p class="text-ink-60 leading-relaxed">Đăng nhập ứng dụng học viên bằng số điện thoại, xem ngay đã đóng bao nhiêu, còn lại bao nhiêu.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- MAP + CONTACT INFO -->
  <section class="py-20 md:py-32 border-b border-line-soft">
    <div class="container-base">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14">
        <div class="lg:col-span-5 reveal">
          <div class="eyebrow mb-4">Vị trí</div>
          <h2 class="text-4xl md:text-5xl font-bold tracking-tight leading-[1.05] mb-8">
            Trung tâm tại {{ site?.city || 'địa phương' }},<br>dễ tìm dễ đến.
          </h2>
          <div class="space-y-6">
            <div v-if="site?.address_full" class="flex gap-4">
              <div class="size-11 bg-brand-50 rounded-lg flex items-center justify-center shrink-0">
                <PhMapPin class="size-5 text-brand-700" />
              </div>
              <div>
                <div class="text-sm font-medium text-ink-40 uppercase tracking-wider mb-1">Địa chỉ</div>
                <div class="font-medium leading-relaxed">{{ site.address_full }}</div>
              </div>
            </div>
            <div v-if="site?.hotline" class="flex gap-4">
              <div class="size-11 bg-brand-50 rounded-lg flex items-center justify-center shrink-0">
                <PhPhone class="size-5 text-brand-700" />
              </div>
              <div>
                <div class="text-sm font-medium text-ink-40 uppercase tracking-wider mb-1">Hotline</div>
                <a :href="`tel:${site.hotline}`" class="font-medium leading-relaxed text-lg hover:text-brand-700 transition">{{ site.hotline_display || site.hotline }}</a>
                <div class="text-sm text-ink-60 mt-1">Hỗ trợ trong khóa đào tạo</div>
              </div>
            </div>
            <div v-if="site?.zalo_url" class="flex gap-4">
              <div class="size-11 bg-brand-50 rounded-lg flex items-center justify-center shrink-0">
                <PhChatCircleText class="size-5 text-brand-700" />
              </div>
              <div>
                <div class="text-sm font-medium text-ink-40 uppercase tracking-wider mb-1">Zalo OA</div>
                <a :href="site.zalo_url" target="_blank" rel="noopener" class="btn-ghost text-sm">
                  Nhắn tin Zalo
                  <PhArrowRight class="size-3.5" weight="bold" />
                </a>
              </div>
            </div>
            <div v-if="site?.working_hours_text" class="flex gap-4">
              <div class="size-11 bg-brand-50 rounded-lg flex items-center justify-center shrink-0">
                <PhClock class="size-5 text-brand-700" />
              </div>
              <div>
                <div class="text-sm font-medium text-ink-40 uppercase tracking-wider mb-1">Giờ làm việc</div>
                <div class="font-medium leading-relaxed">{{ site.working_hours_text }}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="lg:col-span-7 reveal">
          <div class="aspect-[4/3] lg:aspect-auto lg:h-full rounded-2xl overflow-hidden border border-line-base bg-paper-tint">
            <iframe
              v-if="site?.map_embed_url"
              :src="site.map_embed_url"
              width="100%"
              height="100%"
              style="border: 0; min-height: 480px"
              loading="lazy"
              referrerpolicy="no-referrer-when-downgrade"
              :title="`Bản đồ vị trí ${site.brand_name}`"
            ></iframe>
            <div v-else class="flex items-center justify-center h-full min-h-[480px] text-ink-40 text-sm p-8 text-center">
              Bản đồ sẽ hiển thị khi quản trị viên cập nhật URL embed Google Map trong CRM.
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- FAQ -->
  <section class="py-20 md:py-32 border-b border-line-soft">
    <div class="max-w-[900px] mx-auto px-5 md:px-8">
      <div class="mb-14 reveal">
        <div class="eyebrow mb-4">Hỏi đáp</div>
        <h2 class="text-4xl md:text-6xl font-bold tracking-tight leading-[1.05]">
          Câu hỏi thường gặp.
        </h2>
        <p v-if="site?.hotline_display" class="mt-5 text-lg text-ink-60 leading-relaxed">
          Không thấy câu trả lời bạn cần? Gọi {{ site.hotline_display }}.
        </p>
      </div>
      <div class="border-t border-line-base reveal">
        <details v-for="(f, i) in faqs" :key="i" :open="f.open" class="group border-b border-line-base">
          <summary class="flex items-center justify-between gap-6 py-6 md:py-7 cursor-pointer list-none">
            <span class="font-semibold text-lg md:text-xl">{{ f.q }}</span>
            <PhPlus
              weight="bold"
              class="size-5 text-ink-40 shrink-0 transition-transform duration-300 ease-out-expo group-open:rotate-45"
            />
          </summary>
          <div class="pb-6 md:pb-7 text-ink-60 leading-relaxed max-w-[70ch]">{{ f.a }}</div>
        </details>
      </div>
    </div>
  </section>

  <!-- CTA + FORM -->
  <section id="lien-he" class="py-20 md:py-28 bg-brand-950 text-white">
    <div class="container-base">
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16 items-start reveal">
        <div class="lg:col-span-6">
          <div class="text-xs font-semibold uppercase tracking-wider text-brand-300 mb-5">Bắt đầu hôm nay</div>
          <h2 class="text-4xl md:text-6xl font-bold tracking-tight leading-[1.05]">
            Sẵn sàng<br>cầm vô lăng?
          </h2>
          <p class="mt-6 text-lg text-brand-100/80 leading-relaxed max-w-xl">
            Để lại số điện thoại, đội tư vấn gọi lại trong 5 phút và hướng dẫn từng bước. Hoàn toàn miễn phí.
          </p>
          <div class="mt-10 space-y-4">
            <div class="flex gap-4 items-center">
              <PhCheckCircle weight="fill" class="size-6 text-brand-300" />
              <span class="text-brand-100/90">Tư vấn 1 đối 1 trong 5 phút</span>
            </div>
            <div class="flex gap-4 items-center">
              <PhCheckCircle weight="fill" class="size-6 text-brand-300" />
              <span class="text-brand-100/90">Không spam, không bán thông tin</span>
            </div>
            <div class="flex gap-4 items-center">
              <PhCheckCircle weight="fill" class="size-6 text-brand-300" />
              <span class="text-brand-100/90">Hoàn cọc 100% nếu hủy trong 7 ngày</span>
            </div>
          </div>
        </div>
        <div class="lg:col-span-6">
          <form class="bg-white text-ink rounded-2xl p-6 md:p-10" @submit.prevent="submitLead">
            <h3 class="font-bold text-xl mb-1">Tư vấn miễn phí</h3>
            <p class="text-sm text-ink-60 mb-6">Điền thông tin, tư vấn viên gọi lại trong 5 phút.</p>
            <div class="space-y-4 mb-6">
              <label class="flex flex-col gap-1.5">
                <span class="text-sm font-medium">Họ và tên</span>
                <input
                  v-model="form.name" type="text" placeholder="Nguyễn Văn A"
                  class="h-12 px-4 bg-white border border-line-base rounded-md focus:outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-100 transition"
                >
              </label>
              <label class="flex flex-col gap-1.5">
                <span class="text-sm font-medium">Số điện thoại <span class="text-red-700">*</span></span>
                <input
                  v-model="form.phone" type="tel" required placeholder="0903456789" inputmode="numeric"
                  class="h-12 px-4 bg-white border border-line-base rounded-md focus:outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-100 transition"
                >
              </label>
              <label class="flex flex-col gap-1.5">
                <span class="text-sm font-medium">Hạng xe quan tâm</span>
                <select
                  v-model="form.course"
                  class="h-12 px-4 bg-white border border-line-base rounded-md focus:outline-none focus:border-brand-700 focus:ring-2 focus:ring-brand-100 transition"
                >
                  <option value="">Chọn hạng xe</option>
                  <option v-for="c in featured" :key="c.id" :value="c.title">{{ c.title }} · {{ c.vehicle_group_display }}</option>
                </select>
              </label>
            </div>
            <button type="submit" :disabled="submitting"
              class="w-full inline-flex items-center justify-center gap-2 bg-brand-700 hover:bg-brand-800 text-white font-medium text-base h-12 rounded-md transition-colors disabled:opacity-60">
              {{ submitting ? 'Đang gửi…' : 'Gửi yêu cầu tư vấn' }}
              <PhArrowRight v-if="!submitting" class="size-4" weight="bold" />
            </button>
            <p v-if="submitMessage" class="text-sm mt-3 text-center" :class="submitMessage.includes('lỗi') || submitMessage.includes('không hợp lệ') ? 'text-red-700' : 'text-brand-700'">
              {{ submitMessage }}
            </p>
            <p v-else class="text-xs text-ink-40 text-center mt-3">Không spam. Không bán thông tin cho bên thứ ba.</p>
          </form>
        </div>
      </div>
    </div>
  </section>
</template>
