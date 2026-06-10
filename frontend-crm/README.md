# Frontend CRM — Vue 3 + Vite SPA

Admin CRM của trung tâm tuyển sinh, deploy ở subdomain `crm.tencongty.vn`.
Phục vụ 4 nhóm quyền: admin / sale (tư vấn) / accountant (kế toán) / clerk (văn thư).

## Stack

- Vue 3 + TypeScript + Vite 5
- Tailwind CSS 3 (cùng design tokens với FE public — emerald accent, Be Vietnam Pro)
- Pinia (store) · Vue Router 4 · TanStack Vue Query (fetch + cache)
- VeeValidate + Zod (form validation)
- Phosphor icons · vue-sonner (toast) · radix-vue (Dialog headless)
- Axios + session cookie + CSRF token

## Auth

Dùng session cookie Django built-in + CSRF token (không JWT).
Flow:

1. `GET /api/auth/csrf` → set cookie `csrftoken`.
2. `POST /api/auth/login {username, password}` → BE set session cookie.
3. `GET /api/auth/me` → trả thông tin user + groups + permissions.
4. `POST /api/auth/logout` → xoá session.

Router guard tự gọi `bootstrap()` lúc app load; route private redirect về `/login?next=…` nếu chưa auth.

## Dev

```bash
cd frontend-crm
npm install
cp .env.example .env
npm run dev   # http://localhost:5173
```

BE Django chạy ở `http://localhost:8000` (Vite proxy `/api/*` sang BE). 

## Build

```bash
npm run build
npm run preview
```

## Phân quyền UI

Sidebar tự ẩn nav item nếu user không có group tương ứng. Map:

| Trang | Group được xem |
| --- | --- |
| Dashboard | Tất cả |
| Leads | admin, sale |
| Orders | admin, sale, accountant, clerk |
| Payments | admin, accountant |
| Documents | admin, clerk |
| Students | admin, sale, clerk |

## Quy ước

- KHÔNG hard-code brand. Mọi tên trung tâm pull qua `/api/site-settings`.
- KHÔNG dùng em-dash, KHÔNG gradient AI, KHÔNG shadow nặng.
- 1 accent: emerald `brand-600`. Toàn bộ status badge dùng palette success/warning/danger/info đã định.
- Tất cả số tiền hiển thị qua `formatVND()`, ngày qua `formatDate/formatDateTime`.
- File CCCD / hồ sơ học viên: KHÔNG bao giờ serve qua `/media/`. Module Documents (Sprint 3 tiếp theo) gọi endpoint `/api/student/documents/<kind>/<id>/file` (JWT + IDOR + audit).
