<script setup lang="ts">
import { PhCar, PhMotorcycle, PhTruck, PhBus, PhTreeStructure } from '@phosphor-icons/vue'
import { useCourses } from '~/composables/useCourses'

const { data: courses } = await useCourses()
useReveal()

const groups = [
  { key: 'motorcycle', label: 'Mô tô', icon: PhMotorcycle },
  { key: 'car', label: 'Ô tô con', icon: PhCar },
  { key: 'truck', label: 'Xe tải', icon: PhTruck },
  { key: 'bus', label: 'Xe khách', icon: PhBus },
  { key: 'upgrade', label: 'Nâng hạng', icon: PhTreeStructure },
]

const activeGroup = ref<string>('')
const route = useRoute()
onMounted(() => {
  const q = route.query.nhom
  if (typeof q === 'string') activeGroup.value = q
})

const filtered = computed(() => {
  const list = courses.value?.results ?? []
  return activeGroup.value ? list.filter((c) => c.vehicle_group === activeGroup.value) : list
})

useSeoMeta({
  title: 'Khóa học GPLX — chín hạng theo Luật 2025',
  description:
    'Danh sách khóa đào tạo lái xe theo Luật 2025: A1, A, B1, B số sàn, B số tự động, C1, C, D1, D2. Học phí công khai, mở lớp liên tục.',
})
</script>

<template>
  <section class="border-b border-line-soft">
    <div class="container-base pt-16 md:pt-24 pb-12 md:pb-16 reveal">
      <div class="max-w-3xl">
        <div class="eyebrow mb-4">Khóa học</div>
        <h1 class="text-4xl md:text-6xl font-bold tracking-tight leading-[1.05]">
          Chín hạng GPLX<br>theo Luật 2025.
        </h1>
        <p class="mt-6 text-lg text-ink-60 leading-relaxed max-w-[60ch]">
          Học phí công khai, đóng theo tiến độ. Cọc giữ chỗ tối thiểu 200.000đ.
          Mở lớp liên tục cho toàn bộ chín hạng giấy phép lái xe theo Luật Trật tự
          An toàn giao thông đường bộ 2024.
        </p>
      </div>
    </div>
  </section>

  <section class="border-b border-line-soft bg-paper-alt">
    <div class="container-base py-6">
      <div class="flex flex-wrap items-center gap-2">
        <button
          @click="activeGroup = ''"
          class="inline-flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-full border transition-colors"
          :class="activeGroup === ''
            ? 'bg-ink text-white border-ink'
            : 'bg-paper text-ink-60 border-line-base hover:border-ink hover:text-ink'"
        >Tất cả</button>
        <button
          v-for="g in groups" :key="g.key"
          @click="activeGroup = g.key"
          class="inline-flex items-center gap-1.5 text-sm font-medium px-4 py-2 rounded-full border transition-colors"
          :class="activeGroup === g.key
            ? 'bg-ink text-white border-ink'
            : 'bg-paper text-ink-60 border-line-base hover:border-ink hover:text-ink'"
        >
          <component :is="g.icon" class="size-4" />
          {{ g.label }}
        </button>
      </div>
    </div>
  </section>

  <section class="py-16 md:py-24">
    <div class="container-base">
      <div v-if="filtered.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-7 reveal">
        <CourseCard v-for="c in filtered" :key="c.id" :course="c" />
      </div>
      <div v-else class="text-center py-20 text-ink-60">
        Chưa có khóa học nào cho nhóm này. Vui lòng chọn nhóm khác.
      </div>
    </div>
  </section>
</template>
