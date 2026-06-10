<script setup lang="ts">
import { PhSpinnerGap, PhArrowRight, PhUserCircle, PhWarning } from '@phosphor-icons/vue'

const me = ref<Awaited<ReturnType<typeof useMe>> | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const load = async () => {
  loading.value = true
  error.value = null
  try {
    me.value = await useMe()
  } catch (err: any) {
    error.value = 'Không tải được danh sách người học.'
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
useHead({ title: 'Hồ sơ' })
</script>

<template>
  <div class="container-base pt-4">
    <h1 class="text-xl font-bold tracking-tight mb-1">Hồ sơ học viên</h1>
    <p class="text-sm text-ink-60 mb-4">
      Chọn người học để xem và cập nhật giấy tờ.
    </p>

    <div v-if="loading" class="card-base flex items-center gap-3 text-ink-60">
      <PhSpinnerGap class="size-5 animate-spin" /> Đang tải…
    </div>

    <div v-else-if="error" class="card-base bg-danger-soft text-danger">
      <PhWarning class="size-5 inline mr-1.5" /> {{ error }}
    </div>

    <div v-else-if="!me?.persons?.length" class="card-base text-center py-8">
      <PhUserCircle class="size-10 mx-auto text-ink-40 mb-2" />
      <p class="font-semibold mb-1">Chưa có thông tin cá nhân</p>
      <p class="text-sm text-ink-60">
        Tư vấn viên sẽ cập nhật thông tin sau khi bạn cọc đơn đầu tiên.
      </p>
    </div>

    <ul v-else class="space-y-3">
      <li v-for="person in me.persons" :key="person.id">
        <NuxtLink
          :to="`/ho-so/${person.id}`"
          class="card-base flex items-center gap-3 hover:border-brand-300 transition group"
        >
          <div class="size-11 bg-brand-50 text-brand-700 rounded-full flex items-center justify-center font-semibold">
            {{ person.full_name.charAt(0) }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="font-semibold truncate">{{ person.full_name }}</p>
            <p v-if="person.id_number_last4" class="text-xs text-ink-60 num-display">
              CCCD ••••{{ person.id_number_last4 }}
            </p>
          </div>
          <PhArrowRight class="size-5 text-ink-40 group-hover:text-brand-700 group-hover:translate-x-0.5 transition" />
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
