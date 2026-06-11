<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { z } from 'zod'
import { CaretRight, Lock, User, Eye, EyeSlash } from '@/lib/icons'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import BrandTile from '@/components/BrandTile.vue'
import { useAuthStore } from '@/stores/auth'
import { useSiteStore } from '@/stores/site'

const auth = useAuthStore()
const site = useSiteStore()
const router = useRouter()
const route = useRoute()

const loginSchema = z.object({
  username: z.string().trim().min(1, 'Vui lòng nhập tên đăng nhập.'),
  password: z.string().min(1, 'Vui lòng nhập mật khẩu.'),
})

const { defineField, handleSubmit, errors, isSubmitting } = useForm({
  validationSchema: toTypedSchema(loginSchema),
  initialValues: { username: '', password: '' },
})

const [username, usernameAttrs] = defineField('username')
const [password, passwordAttrs] = defineField('password')
const showPassword = ref(false)

const onSubmit = handleSubmit(async (values) => {
  try {
    await auth.login(values.username, values.password)
    toast.success(`Chào ${auth.user?.display_name ?? ''}`)
    const next = typeof route.query.next === 'string' ? route.query.next : '/'
    await router.replace(next.startsWith('/') ? next : '/')
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; data?: { detail?: string } } }
    if (e?.response?.status === 401) {
      toast.error('Tên đăng nhập hoặc mật khẩu không đúng.')
    } else if (e?.response?.status === 403) {
      toast.error(e.response.data?.detail || 'Tài khoản không có quyền truy cập CRM.')
    } else if (e?.response?.status === 429) {
      toast.error('Bạn đã thử quá nhiều lần. Vui lòng đợi rồi thử lại.')
    } else {
      toast.error('Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.')
    }
  }
})
</script>

<template>
  <main class="min-h-screen bg-paper grid lg:grid-cols-[1fr_minmax(0,420px)] xl:grid-cols-[1fr_460px]">
    <!-- Cột thương hiệu, chỉ hiện desktop, tối, asymmetric -->
    <aside class="relative hidden lg:flex flex-col justify-between bg-ink text-paper p-12 xl:p-16 overflow-hidden">
      <div class="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-brand-600/15 blur-3xl" aria-hidden="true" />
      <div class="absolute bottom-0 right-0 h-72 w-72 rounded-full bg-brand-500/10 blur-3xl" aria-hidden="true" />

      <div class="relative">
        <BrandTile variant="dark" size="md" caption="Hệ thống nội bộ" fallback="CRM Tuyển Sinh" />
      </div>

      <div class="relative space-y-6 max-w-md">
        <h1 class="text-4xl xl:text-5xl font-semibold tracking-tighter leading-[1.05] text-balance">
          Quản lý tuyển sinh<br />
          <span class="text-brand-300">trọn vòng đời học viên.</span>
        </h1>
        <p class="text-paper/70 leading-relaxed">
          Tiếp nhận khách, chốt đơn, đối soát thanh toán, duyệt hồ sơ.
          Một quy trình, một nguồn dữ liệu cho tư vấn viên, kế toán và văn thư.
        </p>
        <ul class="space-y-3 text-[13px] text-paper/70">
          <li class="flex items-start gap-2.5">
            <CaretRight :size="14" weight="bold" class="text-brand-300 mt-1 shrink-0" />
            <span>Đối soát Casso tự động trong vòng 2 phút sau khi học viên cọc.</span>
          </li>
          <li class="flex items-start gap-2.5">
            <CaretRight :size="14" weight="bold" class="text-brand-300 mt-1 shrink-0" />
            <span>Hồ sơ CCCD lưu mã hoá, tự huỷ sau 90 ngày theo Nghị định 13/2023.</span>
          </li>
          <li class="flex items-start gap-2.5">
            <CaretRight :size="14" weight="bold" class="text-brand-300 mt-1 shrink-0" />
            <span>Lịch sử tiếp xúc của từng lead, không mất dấu vết khi đổi sale phụ trách.</span>
          </li>
        </ul>
      </div>

      <div class="relative flex items-center gap-2 text-[12px] text-paper/40">
        <Lock :size="14" />
        <span>Phiên đăng nhập được mã hoá, tự huỷ sau 12 giờ không hoạt động.</span>
      </div>
    </aside>

    <!-- Cột form đăng nhập -->
    <section class="flex items-center justify-center px-6 py-12 lg:py-16">
      <div class="w-full max-w-sm space-y-8 animate-slide-up">
        <header class="space-y-2">
          <p class="text-[12px] uppercase tracking-wider text-brand-700 font-semibold">Đăng nhập</p>
          <h2 class="text-3xl font-semibold tracking-tighter text-ink">Vào CRM</h2>
          <p class="text-[13px] text-ink-60 leading-relaxed">
            Sử dụng tài khoản được quản trị viên cấp. Nếu quên mật khẩu, liên hệ admin trung tâm để reset.
          </p>
        </header>

        <form class="space-y-4" autocomplete="on" @submit.prevent="onSubmit">
          <Input
            v-model="username"
            v-bind="usernameAttrs"
            label="Tên đăng nhập"
            placeholder="tendangnhap"
            autocomplete="username"
            :error="errors.username"
            icon-left
            required
          >
            <template #iconLeft><User :size="16" /></template>
          </Input>

          <Input
            v-model="password"
            v-bind="passwordAttrs"
            label="Mật khẩu"
            :type="showPassword ? 'text' : 'password'"
            placeholder="••••••••"
            autocomplete="current-password"
            :error="errors.password"
            icon-left
            icon-right
            required
          >
            <template #iconLeft><Lock :size="16" /></template>
            <template #iconRight>
              <button
                type="button"
                class="flex h-full items-center text-ink-40 hover:text-ink transition-colors"
                :aria-label="showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'"
                @click="showPassword = !showPassword"
              >
                <component :is="showPassword ? EyeSlash : Eye" :size="16" />
              </button>
            </template>
          </Input>

          <Button type="submit" variant="primary" size="lg" :loading="isSubmitting" class="w-full">
            <span>Đăng nhập</span>
            <CaretRight :size="16" weight="bold" />
          </Button>

          <p v-if="site.settings?.student_url" class="text-center text-[12px] text-ink-40 pt-2">
            Học viên xem khoá học, lịch học?
            <a :href="site.settings.student_url" class="text-brand-700 hover:underline underline-offset-2">
              Vào trang học viên
            </a>
          </p>
        </form>
      </div>
    </section>
  </main>
</template>
