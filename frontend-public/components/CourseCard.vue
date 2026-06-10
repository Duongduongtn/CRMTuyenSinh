<script setup lang="ts">
import { PhArrowRight, PhCalendarBlank, PhFire } from '@phosphor-icons/vue'
import type { CourseListItem } from '~/composables/useCourses'
import { formatVND } from '~/composables/useCourses'

const props = defineProps<{ course: CourseListItem }>()

const fallbackImage = computed(() => {
  // Fallback ảnh Unsplash theo nhóm xe khi BE chưa upload cover_image
  const map: Record<string, string> = {
    motorcycle: 'https://images.unsplash.com/photo-1558981403-c5f9899a28bc?w=640&h=400&fit=crop&q=85',
    car: 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=640&h=400&fit=crop&q=85',
    truck: 'https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?w=640&h=400&fit=crop&q=85',
    bus: 'https://images.unsplash.com/photo-1565616462879-d7b21fdfff8e?w=640&h=400&fit=crop&q=85',
    upgrade: 'https://images.unsplash.com/photo-1542362567-b07e54358753?w=640&h=400&fit=crop&q=85',
  }
  return map[props.course.vehicle_group] || map.car
})

const imageUrl = computed(() => props.course.cover_image_url || fallbackImage.value)
</script>

<template>
  <NuxtLink
    :to="`/khoa-hoc/${course.slug}`"
    class="group flex flex-col bg-paper rounded-2xl overflow-hidden hover:-translate-y-0.5 transition-all duration-300 ease-out-expo"
    :class="course.is_featured ? 'border border-brand-600' : 'border border-line-base hover:border-ink'"
  >
    <div class="aspect-[16/10] overflow-hidden bg-paper-alt relative">
      <NuxtImg
        :src="imageUrl"
        :alt="`Ảnh đại diện hạng ${course.title}`"
        loading="lazy"
        sizes="sm:100vw md:50vw lg:33vw"
        width="640"
        height="400"
        class="size-full object-cover group-hover:scale-[1.03] transition-transform duration-500 ease-out-expo"
      />
      <div
        v-if="course.is_featured"
        class="absolute top-3 left-3 inline-flex items-center gap-1.5 bg-brand-700 text-white text-xs font-semibold px-3 py-1.5 rounded-full"
      >
        <PhFire class="size-3.5" weight="fill" />
        <span>Phổ biến nhất</span>
      </div>
    </div>
    <div class="p-6 md:p-7 flex flex-col flex-1">
      <div class="text-xs font-medium uppercase tracking-wider text-ink-40 mb-2">{{ course.vehicle_group_display }}</div>
      <h3 class="text-2xl font-bold tracking-tight mb-2">{{ course.title }}</h3>
      <p class="text-ink-60 leading-relaxed mb-5 flex-1">{{ course.short_description }}</p>
      <div class="flex items-end justify-between pt-5 border-t border-line-soft">
        <div>
          <div class="text-2xl font-bold num-display">{{ formatVND(course.tuition_fee) }}</div>
          <div v-if="course.duration_display" class="flex items-center gap-2 text-sm text-ink-60 mt-1">
            <PhCalendarBlank class="size-4" />
            <span>{{ course.duration_display }}</span>
          </div>
        </div>
        <span class="text-brand-700 group-hover:translate-x-1 transition-transform">
          <PhArrowRight class="size-5" weight="bold" />
        </span>
      </div>
    </div>
  </NuxtLink>
</template>
