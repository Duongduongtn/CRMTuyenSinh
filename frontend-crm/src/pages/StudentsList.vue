<script setup lang="ts">
import { GraduationCap } from '@/lib/icons'
import Card from '@/components/ui/Card.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
</script>

<template>
  <div class="space-y-6">
    <header>
      <p class="text-[12px] uppercase tracking-wider text-brand-700 font-semibold">Hồ sơ học viên</p>
      <h2 class="text-3xl font-semibold tracking-tighter text-ink mt-1">Học viên</h2>
      <p class="text-[13px] text-ink-60 mt-1">
        Danh sách Person + Enrollment. UI v1 dùng đơn → trang chi tiết student liên kết qua đơn.
      </p>
    </header>

    <Card>
      <EmptyState
        title="Module học viên đang phát triển"
        description="Học viên hiện hiển thị qua trang Đơn đăng ký (person_name, person_phone). PR Sprint 3 tiếp theo sẽ tách màn Học viên đầy đủ với hồ sơ + lịch sử."
      >
        <template #icon><GraduationCap :size="24" weight="duotone" class="text-brand-700" /></template>
      </EmptyState>
    </Card>
  </div>
</template>
