<script setup lang="ts">
import Sidebar from './Sidebar.vue'
import Topbar from './Topbar.vue'
</script>

<template>
  <div class="flex min-h-screen bg-paper-alt/50">
    <Sidebar />
    <div class="flex flex-1 flex-col min-w-0">
      <Topbar />
      <main class="flex-1 px-5 lg:px-8 py-8">
        <div class="mx-auto w-full max-w-[1440px] animate-fade-in">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>
