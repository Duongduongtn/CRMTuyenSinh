<script setup lang="ts">
import { PhClock, PhCalendarBlank, PhArrowRight } from '@phosphor-icons/vue'

const route = useRoute()
const category = computed(() => {
  const c = route.query.chuyen_muc
  return typeof c === 'string' ? c : undefined
})

const { data: posts } = await useBlogPosts({ category: category.value })
const { data: categories } = await useBlogCategories()
const { data: site } = await useSiteSettings()

useSeoMeta({
  title: 'Tin tức và hướng dẫn',
  description: site.value?.description
    ? `Tin tức học lái xe, luật mới 2025, hướng dẫn thi sát hạch từ ${site.value.brand_name}.`
    : 'Tin tức học lái xe, luật mới 2025, hướng dẫn thi sát hạch.',
})

useReveal()

const featured = computed(() => posts.value?.results.find(p => p.is_featured) || posts.value?.results[0])
const list = computed(() => {
  const all = posts.value?.results || []
  const feat = featured.value
  return feat ? all.filter(p => p.id !== feat.id) : all
})
</script>

<template>
  <div>
    <!-- Hero -->
    <section class="container-base pt-14 md:pt-20 pb-10">
      <p class="eyebrow mb-3">Tin tức và hướng dẫn</p>
      <h1 class="text-3xl md:text-5xl font-bold tracking-tighter mb-4 max-w-3xl">
        Cập nhật mới nhất về luật lái xe và quy trình đào tạo
      </h1>
      <p class="text-base md:text-lg text-ink-60 leading-relaxed max-w-2xl">
        Hướng dẫn thi sát hạch, các thay đổi của Luật Trật tự An toàn giao thông 2024,
        kinh nghiệm học và thi cho người đi làm.
      </p>
    </section>

    <!-- Categories filter -->
    <section v-if="categories?.results.length" class="container-base pb-6">
      <div class="flex flex-wrap gap-2">
        <NuxtLink
          to="/tin-tuc"
          class="px-4 py-2 rounded-full text-sm font-medium border transition"
          :class="!category ? 'bg-ink text-white border-ink' : 'border-line-base text-ink-60 hover:border-ink hover:text-ink'"
        >
          Tất cả
        </NuxtLink>
        <NuxtLink
          v-for="cat in categories.results"
          :key="cat.id"
          :to="`/tin-tuc?chuyen_muc=${cat.slug}`"
          class="px-4 py-2 rounded-full text-sm font-medium border transition"
          :class="category === cat.slug ? 'bg-ink text-white border-ink' : 'border-line-base text-ink-60 hover:border-ink hover:text-ink'"
        >
          {{ cat.name }}
        </NuxtLink>
      </div>
    </section>

    <!-- Featured + grid -->
    <section class="container-base pb-20">
      <div v-if="!posts?.results.length" class="card-base text-center py-16">
        <p class="text-ink-60">Chưa có bài viết nào.</p>
      </div>

      <template v-else>
        <NuxtLink
          v-if="featured"
          :to="`/tin-tuc/${featured.slug}`"
          class="block group reveal mb-12"
        >
          <div class="grid md:grid-cols-2 gap-6 md:gap-10 items-center">
            <div class="aspect-[4/3] bg-paper-alt rounded-xl overflow-hidden">
              <img
                v-if="featured.cover_image_url"
                :src="featured.cover_image_url"
                :alt="featured.cover_alt || featured.title"
                class="size-full object-cover group-hover:scale-[1.02] transition-transform duration-500 ease-out-expo"
                loading="eager"
              >
              <div v-else class="size-full grid place-items-center text-ink-40 text-sm">Không có ảnh</div>
            </div>
            <div>
              <p class="eyebrow mb-3">{{ featured.category.name }}</p>
              <h2 class="text-2xl md:text-4xl font-bold tracking-tight mb-3 group-hover:text-brand-700 transition-colors">
                {{ featured.title }}
              </h2>
              <p class="text-base md:text-lg text-ink-60 leading-relaxed mb-4 max-w-xl">
                {{ featured.excerpt }}
              </p>
              <div class="flex items-center gap-4 text-sm text-ink-40">
                <span class="inline-flex items-center gap-1"><PhCalendarBlank class="size-4" /> {{ formatDateVN(featured.published_at) }}</span>
                <span class="inline-flex items-center gap-1 num-display"><PhClock class="size-4" /> {{ featured.read_time_minutes }} phút đọc</span>
              </div>
            </div>
          </div>
        </NuxtLink>

        <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <article
            v-for="post in list"
            :key="post.id"
            class="group reveal"
          >
            <NuxtLink :to="`/tin-tuc/${post.slug}`" class="block">
              <div class="aspect-[3/2] bg-paper-alt rounded-lg overflow-hidden mb-4">
                <img
                  v-if="post.cover_image_url"
                  :src="post.cover_image_url"
                  :alt="post.cover_alt || post.title"
                  class="size-full object-cover group-hover:scale-[1.03] transition-transform duration-500 ease-out-expo"
                  loading="lazy"
                >
                <div v-else class="size-full grid place-items-center text-ink-40 text-xs">Không có ảnh</div>
              </div>
              <p class="text-xs uppercase tracking-wider text-brand-700 font-semibold mb-2">
                {{ post.category.name }}
              </p>
              <h3 class="text-lg font-bold leading-snug mb-2 group-hover:text-brand-700 transition-colors">
                {{ post.title }}
              </h3>
              <p class="text-sm text-ink-60 leading-relaxed line-clamp-2 mb-3">
                {{ post.excerpt }}
              </p>
              <div class="flex items-center gap-3 text-xs text-ink-40">
                <span class="inline-flex items-center gap-1"><PhCalendarBlank class="size-3.5" /> {{ formatDateVN(post.published_at) }}</span>
                <span class="inline-flex items-center gap-1 num-display"><PhClock class="size-3.5" /> {{ post.read_time_minutes }}p</span>
              </div>
            </NuxtLink>
          </article>
        </div>
      </template>
    </section>
  </div>
</template>
