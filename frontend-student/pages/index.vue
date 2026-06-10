<script setup lang="ts">
// Route gốc — redirect tùy auth state
definePageMeta({ layout: false })

onMounted(() => {
  const { isAuthenticated, hydrate } = useAuth()
  hydrate()
  navigateTo(isAuthenticated.value ? '/dashboard' : '/dang-nhap')
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center">
    <div class="text-ink-60 text-sm">Đang chuyển trang…</div>
  </div>
</template>
