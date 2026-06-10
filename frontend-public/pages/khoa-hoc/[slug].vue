<script setup lang="ts">
import {
  PhArrowRight,
  PhArrowLeft,
  PhCalendarBlank,
  PhCheckCircle,
  PhCertificate,
  PhSeal,
  PhPhone,
} from '@phosphor-icons/vue'
import { useCourse, formatVND } from '~/composables/useCourses'
import { useSiteSettings } from '~/composables/useSiteSettings'

const route = useRoute()
const slug = computed(() => String(route.params.slug))
const { data: course, error } = await useCourse(slug.value)
const { data: site } = await useSiteSettings()
useReveal()

if (error.value || !course.value) {
  throw createError({ statusCode: 404, statusMessage: 'Không tìm thấy khóa học', fatal: true })
}

const heroImage = computed(() => {
  if (course.value?.cover_image_url) return course.value.cover_image_url
  const map: Record<string, string> = {
    motorcycle: 'https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=1280&h=720&fit=crop&q=85',
    car: 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=1280&h=720&fit=crop&q=85',
    truck: 'https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?w=1280&h=720&fit=crop&q=85',
    bus: 'https://images.unsplash.com/photo-1565616462879-d7b21fdfff8e?w=1280&h=720&fit=crop&q=85',
    upgrade: 'https://images.unsplash.com/photo-1542362567-b07e54358753?w=1280&h=720&fit=crop&q=85',
  }
  return map[course.value?.vehicle_group ?? 'car'] || map.car
})

const includes = [
  'Lý thuyết 600 câu cập nhật Luật 2025',
  'Thực hành sa hình tại sân tập riêng',
  'Thực hành đường trường có huấn luyện viên kèm',
  'Hồ sơ đăng ký thi sát hạch hỗ trợ trọn gói',
  'Nhắc lịch học qua Zalo và ứng dụng học viên',
  'Hoàn cọc 100% nếu hủy trước khai giảng 7 ngày',
]

useSeoMeta({
  title: course.value.meta_title || `${course.value.title} · ${course.value.vehicle_class_display}`,
  description:
    course.value.meta_description ||
    course.value.short_description ||
    `Khóa đào tạo ${course.value.title}. Học phí ${formatVND(course.value.tuition_fee)}. Cọc giữ chỗ ${formatVND(course.value.deposit_amount)}.`,
  ogImage: course.value.og_image_url || heroImage.value,
  ogType: 'article',
  twitterTitle: course.value.meta_title || `${course.value.title} · ${course.value.vehicle_class_display}`,
  twitterDescription:
    course.value.meta_description ||
    course.value.short_description ||
    `Khóa đào tạo ${course.value.title}`,
  twitterImage: course.value.og_image_url || heroImage.value,
})

const siteUrl = useRuntimeConfig().public.siteUrl
const canonical = `${siteUrl}/khoa-hoc/${course.value.slug}`
useHead({
  link: [{ rel: 'canonical', href: canonical }],
})

const courseSchema = computed(() => ({
  '@context': 'https://schema.org',
  '@type': 'Course',
  name: `${course.value!.title} · ${course.value!.vehicle_class_display}`,
  description: course.value!.short_description || course.value!.meta_description,
  url: canonical,
  image: heroImage.value,
  provider: {
    '@type': 'DrivingSchool',
    name: site.value?.brand_name,
    url: siteUrl,
    sameAs: siteUrl,
  },
  offers: {
    '@type': 'Offer',
    price: course.value!.tuition_fee,
    priceCurrency: 'VND',
    availability: 'https://schema.org/InStock',
    url: canonical,
  },
  hasCourseInstance: {
    '@type': 'CourseInstance',
    courseMode: 'onsite',
    courseSchedule: {
      '@type': 'Schedule',
      repeatFrequency: 'P1W',
      scheduleTimezone: 'Asia/Ho_Chi_Minh',
    },
    location: {
      '@type': 'Place',
      name: site.value?.brand_name,
      address: site.value?.address_full,
    },
    inLanguage: 'vi',
    ...(course.value!.duration_days
      ? { courseWorkload: `P${course.value!.duration_days}D` }
      : {}),
  },
}))

const breadcrumbSchema = computed(() => ({
  '@context': 'https://schema.org',
  '@type': 'BreadcrumbList',
  itemListElement: [
    { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${siteUrl}/` },
    { '@type': 'ListItem', position: 2, name: 'Khóa học', item: `${siteUrl}/khoa-hoc` },
    {
      '@type': 'ListItem',
      position: 3,
      name: course.value!.title,
      item: canonical,
    },
  ],
}))

useHead({
  script: [
    {
      type: 'application/ld+json',
      innerHTML: () => JSON.stringify(courseSchema.value),
    },
    {
      type: 'application/ld+json',
      innerHTML: () => JSON.stringify(breadcrumbSchema.value),
    },
  ],
})
</script>

<template>
  <article v-if="course" class="border-b border-line-soft">
    <div class="container-base pt-8 md:pt-12 pb-16 md:pb-24">
      <NuxtLink to="/khoa-hoc" class="inline-flex items-center gap-1.5 text-sm text-ink-60 hover:text-ink transition mb-8">
        <PhArrowLeft class="size-4" weight="bold" />
        <span>Tất cả khóa học</span>
      </NuxtLink>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-start reveal">
        <div class="lg:col-span-7">
          <div class="aspect-[16/9] overflow-hidden rounded-2xl bg-paper-tint mb-8">
            <NuxtImg
              :src="heroImage" :alt="`Khóa học ${course.title}`"
              width="1280" height="720" loading="eager"
              class="size-full object-cover"
            />
          </div>
          <div class="eyebrow mb-3">{{ course.vehicle_group_display }}</div>
          <h1 class="text-4xl md:text-6xl font-bold tracking-tight leading-[1.05]">{{ course.title }}</h1>
          <p class="mt-5 text-lg text-ink-60 leading-relaxed">{{ course.vehicle_class_display }}</p>

          <div class="mt-8 prose max-w-none">
            <p v-if="course.short_description" class="text-lg leading-relaxed text-ink">{{ course.short_description }}</p>
            <div v-if="course.description_md" class="mt-6 text-ink-60 leading-relaxed whitespace-pre-line">{{ course.description_md }}</div>
          </div>

          <div class="mt-10">
            <h2 class="text-2xl font-bold tracking-tight mb-5">Khóa học bao gồm</h2>
            <ul class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <li v-for="(item, i) in includes" :key="i" class="flex gap-3 items-start">
                <PhCheckCircle weight="fill" class="size-5 text-brand-700 shrink-0 mt-0.5" />
                <span class="text-ink-60 leading-relaxed">{{ item }}</span>
              </li>
            </ul>
          </div>
        </div>

        <aside class="lg:col-span-5 lg:sticky lg:top-24">
          <div class="bg-paper border border-line-base rounded-2xl p-6 md:p-8 shadow-[var(--shadow-soft)]">
            <div class="eyebrow mb-3">Học phí trọn khóa</div>
            <div class="text-4xl md:text-5xl font-bold num-display tracking-tight">{{ formatVND(course.tuition_fee) }}</div>
            <div class="mt-2 text-sm text-ink-60">Đóng theo tiến độ, không phụ phí phát sinh.</div>

            <div class="mt-7 grid grid-cols-2 gap-4">
              <div class="border-l-2 border-brand-600 pl-4">
                <div class="text-xs text-ink-40 uppercase tracking-wider">Đặt cọc</div>
                <div class="font-bold text-lg mt-1 num-display">{{ formatVND(course.deposit_amount) }}</div>
              </div>
              <div class="border-l-2 border-brand-600 pl-4">
                <div class="text-xs text-ink-40 uppercase tracking-wider">Thời gian</div>
                <div class="font-bold text-lg mt-1">{{ course.duration_display || `${course.duration_days} ngày` }}</div>
              </div>
            </div>

            <a href="/#lien-he" class="btn-emerald w-full mt-7">
              Đăng ký tư vấn
              <PhArrowRight class="size-4" weight="bold" />
            </a>
            <a v-if="site?.hotline" :href="`tel:${site.hotline}`" class="btn-secondary w-full mt-3">
              <PhPhone class="size-4" />
              Gọi {{ site.hotline_display || site.hotline }}
            </a>

            <div class="mt-8 pt-6 border-t border-line-soft space-y-3 text-sm">
              <div class="flex gap-3 items-start">
                <PhCertificate class="size-5 text-brand-700 shrink-0 mt-0.5" />
                <div>
                  <div class="font-medium">Chứng nhận hoàn thành</div>
                  <div class="text-ink-60 mt-0.5">Hỗ trợ làm hồ sơ thi sát hạch</div>
                </div>
              </div>
              <div class="flex gap-3 items-start">
                <PhSeal class="size-5 text-brand-700 shrink-0 mt-0.5" />
                <div>
                  <div class="font-medium">Cam kết hoàn cọc 100%</div>
                  <div class="text-ink-60 mt-0.5">Hủy trước khai giảng 7 ngày</div>
                </div>
              </div>
              <div class="flex gap-3 items-start">
                <PhCalendarBlank class="size-5 text-brand-700 shrink-0 mt-0.5" />
                <div>
                  <div class="font-medium">Mở lớp liên tục</div>
                  <div class="text-ink-60 mt-0.5">Liên hệ để biết khung lịch phù hợp</div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  </article>
</template>
