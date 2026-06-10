<script setup lang="ts">
import { FolderSimple } from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
</script>

<template>
  <div class="space-y-6">
    <header>
      <p class="text-[12px] uppercase tracking-wider text-brand-700 font-semibold">Văn thư</p>
      <h2 class="text-3xl font-semibold tracking-tighter text-ink mt-1">Hồ sơ học viên</h2>
      <p class="text-[13px] text-ink-60 mt-1">
        Duyệt CCCD, ảnh thẻ, giấy khám sức khoẻ. Module review duyệt sẽ bổ sung ở Sprint 3 cuối.
      </p>
    </header>

    <Card>
      <EmptyState
        title="Module hồ sơ đang phát triển"
        description="Hồ sơ học viên upload trực tiếp qua PWA hocvien.tencongty.vn. Trang duyệt sẽ kết nối API /api/student/documents/* trong PR tiếp theo của Sprint 3."
      >
        <template #icon><FolderSimple :size="24" weight="duotone" class="text-brand-700" /></template>
      </EmptyState>
    </Card>
  </div>
</template>
