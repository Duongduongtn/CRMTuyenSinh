# Tài liệu thiết kế — CRM Tuyển Sinh Học Lái Xe

Phiên bản: v1 draft, ngày 10/06/2026.

Dự án CRM tuyển sinh học lái xe gồm 3 mặt trận:
- **FE public** (Nuxt 3 SSG): landing page tuyển sinh, SEO Google, ở domain chính.
- **CRM admin** (Django + admin tùy biến): quản lý lead, đơn hàng, thanh toán, hồ sơ, blog. Ở subdomain `crm.`.
- **PWA học viên** (Nuxt 3 CSR): đăng nhập SĐT + OTP Zalo ZNS, upload hồ sơ, xem công nợ. Ở subdomain `hocvien.`.

Backend Django + PostgreSQL + Celery + Redis + Casso webhook.

---

## Mục lục tài liệu

### 1. Quy trình tư duy
- **[01-wireframes-fe-public.md](./01-wireframes-fe-public.md)** — Wireframe ASCII 8 trang FE public (trang chủ, list khóa, chi tiết khóa, đặt cọc QR, blog list, blog detail, liên hệ, modal đăng ký tư vấn).

### 2. Design system
- **[02-design-system.md](./02-design-system.md)** — Color tokens, typography, spacing, motion, components, iconography, responsive, accessibility. Tuân theo taste-skill.

### 3. Plan triển khai
- **[03-phase1-plan.md](./03-phase1-plan.md)** — Plan chi tiết v1 (7-8 tuần, 3 sprint), tech stack, cấu trúc thư mục, sprint task, acceptance criteria, rủi ro, setup commands.
- **[05-sprint3-soft-launch.md](./05-sprint3-soft-launch.md)** — Checklist Sprint 3 Tuần 7: lấy 4 nhóm key prod, paste `.env.prod`, smoke E2E 5 step, monitoring, rollback.
- **[06-cloudflare-pages-fe-public.md](./06-cloudflare-pages-fe-public.md)** — Setup Cloudflare Pages cho FE public landing (hybrid SSR via nitro `cloudflare-pages` preset), custom domain `trungtamthanhdat.com`.

### 4. HTML wireframe mở browser
- **[wireframes-html/index.html](./wireframes-html/index.html)** — Trang chủ (minimalist hiện đại, trắng + xanh lá).
- **[wireframes-html/khoa-hoc.html](./wireframes-html/khoa-hoc.html)** — Danh sách 9 khóa GPLX theo nhóm.
- **[wireframes-html/khoa-hoc-chi-tiet.html](./wireframes-html/khoa-hoc-chi-tiet.html)** — Chi tiết khóa B số sàn (sticky sidebar, FAQ riêng, HLV).
- **[wireframes-html/dat-coc.html](./wireframes-html/dat-coc.html)** — Trang đặt cọc QR (live status Casso).

Mở bằng double-click trong File Explorer → Chrome/Edge. File standalone, dùng Tailwind/Geist/Phosphor qua CDN. Bật DevTools mobile để test responsive.

---

## Memory đã lưu (tham chiếu cho mọi phiên sau)

Đường dẫn: `C:\Users\Admin\.claude\projects\d--Du-An-CRMTuyensinh\memory\`

| Memory | Mục đích |
|---|---|
| `MEMORY.md` | Index |
| `vehicle-classes-2025.md` | 9 hạng GPLX theo Luật 2025 (A1, A, B1 + B-AT, B-MT, C1, C, D1, D2). KHÔNG dùng hệ cũ A1/A2/B1/B2/C/D/E |
| `crm-roles-flexible.md` | RBAC group-based, 1 user nhiều quyền (Sale/Kế toán/Văn thư/Admin) |
| `student-auth-flow.md` | Passwordless, auto-provision khi sale chốt đơn, OTP Zalo ZNS, quick-view JWT 24h |
| `person-enrollment-model.md` | 3 tầng Account (SĐT) — Person (CCCD) — Enrollment (Order). CCCD/chân dung gắn Person, giấy khám SK/bằng cũ gắn Enrollment |
| `subdomain-layout.md` | `tencongty.vn` (placeholder) + `crm.` + `hocvien.` |
| `taste-skill-paths.md` | Đường dẫn 5 sub-skill taste-skill + anti-pattern + cài đặt mặc định cho dự án |

---

## Tóm tắt nghiệp vụ đã chốt với user

| Hạng mục | Quyết định |
|---|---|
| FE public stack | Nuxt 3 SSG |
| CRM admin stack | Django 5 + django-unfold admin |
| PWA học viên stack | Nuxt 3 CSR (subdomain riêng `hocvien.`) |
| Backend stack | Django + DRF + PostgreSQL 16 + Celery + Redis |
| Hạng GPLX | 9 hạng theo Luật 2025 |
| Phân quyền | 4 Group RBAC, multi-permission per user |
| Auth học viên | SĐT + OTP qua Zalo ZNS, fallback SMS |
| Tạo tài khoản HV | Auto-provision khi sale chốt đơn |
| Model hồ sơ | Person master (dedup CCCD) + Enrollment riêng đơn |
| Tài liệu chung | CCCD + chân dung gắn Person (dùng nhiều đơn) |
| Tài liệu riêng | Giấy khám SK + bằng lái cũ gắn Enrollment |
| Quyền upload hộ HV | Văn thư có (audit log) |
| Quick view công nợ | Link Zalo signed JWT 24h, read-only |
| Thanh toán | Cọc + còn lại, VietQR + Casso webhook |
| Hoa hồng sale | v1 chỉ track `recruited_by`, chưa tính tiền |
| Nguồn lead | Form FE + hotline/Zalo + FB Lead Ads webhook |
| Pháp lý CCCD | Auto-purge 90 ngày (NĐ 13/2023) |
| In đơn | PDF mẫu Sở GTVT (chưa liên thông API) |
| Phạm vi | 1 trung tâm, không multi-branch |
| Blog | App `blog` Django + FE `/tin-tuc`, schema Article |
| Phong cách UI | Minimalist hiện đại, trắng + xanh lá, theo taste-skill |

---

## Lộ trình v1 (3 sprint, 7-8 tuần)

```
Sprint 1 (Tuần 1-3) — Backbone CRM + Landing
├── Tuần 1: Setup + Auth + Models lõi
├── Tuần 2: Lead module + Telegram + Order
└── Tuần 3: Payment + Casso webhook + Setup Nuxt

Sprint 2 (Tuần 4-5) — FE đầy đủ + PWA + Blog + PDF
├── Tuần 4: FE public các trang theo wireframe
└── Tuần 5: PWA HV + Document workflow + Blog + PDF + Auto-purge

Sprint 3 (Tuần 6-7) — Marketing + Deploy
├── Tuần 6: FB Lead Ads + Quick view + Báo cáo + Security
└── Tuần 7: Deploy VPS + CI/CD + Smoke test + Soft launch
```

Chi tiết task từng ngày: xem [03-phase1-plan.md](./03-phase1-plan.md).

---

## Bước tiếp theo

1. **User duyệt 4 file HTML wireframe** trong browser. Có thể mở từ File Explorer hoặc dùng Live Server VSCode.
2. **User feedback** về:
   - Phong cách design (vibe, palette, layout)
   - Section thừa/thiếu trên FE
   - Chi tiết nghiệp vụ chưa khớp
3. **User cung cấp dependencies** đã liệt kê ở `03-phase1-plan.md` mục 6.
4. **Bắt đầu Sprint 1** — Setup Django project + migrations + admin.

---

## Liên hệ trong dự án

Trong các phiên Claude Code tiếp theo, chỉ cần nói "Mở dự án CRM tuyển sinh" — memory tự load:
- Hạng GPLX đúng (Luật 2025).
- Phân quyền group-based.
- Model 3 tầng Account/Person/Enrollment.
- Flow auth học viên.
- Design system minimalist + xanh lá.
- Subdomain layout.

Không cần giải thích lại từ đầu.
