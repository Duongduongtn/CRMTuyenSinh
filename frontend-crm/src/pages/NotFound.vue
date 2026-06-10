<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ArrowLeft, MagnifyingGlass } from '@/lib/icons'
import Button from '@/components/ui/Button.vue'

const router = useRouter()
</script>

<template>
  <main class="min-h-screen flex items-center justify-center bg-paper px-6">
    <div class="text-center max-w-md space-y-5 animate-slide-up">
      <div class="inline-flex h-14 w-14 items-center justify-center rounded-full bg-paper-tint">
        <MagnifyingGlass :size="24" weight="duotone" class="text-brand-700" />
      </div>
      <div class="space-y-2">
        <p class="text-[12px] uppercase tracking-wider text-ink-40 font-semibold">404</p>
        <h1 class="text-4xl font-semibold tracking-tighter text-ink">Không tìm thấy trang</h1>
        <p class="text-[14px] text-ink-60 leading-relaxed">
          Đường dẫn bạn vừa truy cập không tồn tại trong CRM, hoặc bạn không có quyền xem.
        </p>
      </div>
      <Button @click="router.replace('/')">
        <ArrowLeft :size="14" weight="bold" />
        Về tổng quan
      </Button>
    </div>
  </main>
</template>
