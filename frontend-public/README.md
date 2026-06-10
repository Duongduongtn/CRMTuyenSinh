# FE Public — CRM Tuyển Sinh Học Lái Xe

Nuxt 3 SSG + Tailwind CSS theo `docs/02-design-system.md`.

## Phát triển

```bash
pnpm install
cp .env.example .env  # rồi sửa NUXT_PUBLIC_API_BASE nếu BE chạy port khác
pnpm dev              # http://localhost:3000
```

Cần Django BE chạy ở `http://localhost:8000` (xem `backend/README.md`).

## Build production

```bash
pnpm generate   # SSG → output trong .output/public/
pnpm preview    # preview build SSG
```

`/dh/[token]` được cấu hình `prerender: false` (SSR runtime) vì dữ liệu phụ thuộc
trạng thái đặt cọc thay đổi liên tục.

## Cấu trúc

- `pages/index.vue` — trang chủ (asymmetric hero + 6 section + form lead capture)
- `pages/khoa-hoc/index.vue` — danh sách 9 khóa + filter theo nhóm
- `pages/khoa-hoc/[slug].vue` — chi tiết khóa + JSON-LD `Course` + canonical
- `pages/dh/[token].vue` — QR đặt cọc + polling 3s
- `components/` — `AppHeader`, `AppFooter`, `CourseCard`
- `composables/` — `useSiteSettings`, `useCourses`, `useEnrollment`, `useReveal`
- `server/routes/sitemap.xml.ts` — sitemap động lấy từ BE

## Quy ước

- KHÔNG hardcode tên trung tâm, hotline, địa chỉ — đọc qua `/api/site-settings`.
- 1 accent duy nhất: `brand-700` (emerald).
- 1 font: Geist self-host qua `@fontsource/geist-sans`.
- Icons: Phosphor Icons `@phosphor-icons/vue`, weight `regular` mặc định, `bold` cho icon button.
