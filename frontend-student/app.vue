<script setup lang="ts">
const { hydrate } = useAuth()

onMounted(() => {
  hydrate()
})
</script>

<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>
