<script setup lang="ts">
const { hydrate } = useAuth()

onMounted(() => {
  hydrate()
})
</script>

<template>
  <NuxtLayout>
    <NuxtPage :transition="{ name: 'slide', mode: 'out-in' }" />
  </NuxtLayout>
</template>
