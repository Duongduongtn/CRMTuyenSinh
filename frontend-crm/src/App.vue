<script setup lang="ts">
import { onMounted } from 'vue'
import { Toaster } from 'vue-sonner'
import { useSiteStore } from '@/stores/site'

const site = useSiteStore()
onMounted(() => {
  site.load()
})
</script>

<template>
  <RouterView />
  <Toaster position="top-right" theme="light" rich-colors close-button />
</template>
