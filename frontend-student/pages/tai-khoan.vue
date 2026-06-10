<script setup lang="ts">
import { PhPhone, PhSignOut, PhShieldCheck, PhInfo } from '@phosphor-icons/vue'

const { account, logout } = useAuth()
useHead({ title: 'Tài khoản' })
</script>

<template>
  <div class="container-base pt-4">
    <h1 class="text-xl font-bold tracking-tight mb-4">Tài khoản</h1>

    <section class="card-base mb-3">
      <div class="flex items-center gap-3 mb-3">
        <div class="size-12 bg-brand-50 text-brand-700 rounded-full flex items-center justify-center font-bold text-lg">
          {{ (account?.display_name || 'H').charAt(0) }}
        </div>
        <div class="min-w-0">
          <p class="font-semibold truncate">{{ account?.display_name || 'Học viên' }}</p>
          <p class="text-sm text-ink-60 inline-flex items-center gap-1 num-display">
            <PhPhone class="size-3.5" />
            {{ account?.phone }}
          </p>
        </div>
      </div>
    </section>

    <section class="card-base mb-3">
      <h2 class="font-semibold text-sm mb-2 flex items-center gap-1.5">
        <PhShieldCheck class="size-4 text-brand-700" />
        Bảo mật
      </h2>
      <p class="text-sm text-ink-60 leading-relaxed">
        Tài khoản đăng nhập bằng OTP gửi qua Zalo. Không có mật khẩu để lộ.
        Tự đăng xuất sau 30 ngày không hoạt động.
      </p>
    </section>

    <section class="card-base mb-3">
      <h2 class="font-semibold text-sm mb-2 flex items-center gap-1.5">
        <PhInfo class="size-4 text-brand-700" />
        Dữ liệu cá nhân
      </h2>
      <p class="text-sm text-ink-60 leading-relaxed">
        CCCD và giấy khám sức khỏe được tự động xóa khỏi hệ thống sau 90 ngày
        kể từ khi hoàn thành khóa học, theo Nghị định 13/2023 về bảo vệ dữ liệu
        cá nhân.
      </p>
    </section>

    <button
      type="button"
      class="btn-secondary w-full text-danger border-danger/30 hover:border-danger"
      @click="logout"
    >
      <PhSignOut class="size-5" />
      Đăng xuất
    </button>
  </div>
</template>
