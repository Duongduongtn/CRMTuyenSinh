# Plan triển khai v1 — CRM Tuyển Sinh Học Lái Xe

Phiên bản: v1, ngày 10/06/2026.
Phạm vi: 7-8 tuần, chia 3 sprint. Sản phẩm v1 launch được, có thể tuyển sinh thật.

> Tất cả quyết định kiến trúc đã chốt trong các phiên trước được tham chiếu từ memory:
> [vehicle-classes-2025](../../C:/Users/Admin/.claude/projects/d--Du-An-CRMTuyensinh/memory/vehicle-classes-2025.md),
> [crm-roles-flexible](../../C:/Users/Admin/.claude/projects/d--Du-An-CRMTuyensinh/memory/crm-roles-flexible.md),
> [student-auth-flow](../../C:/Users/Admin/.claude/projects/d--Du-An-CRMTuyensinh/memory/student-auth-flow.md),
> [person-enrollment-model](../../C:/Users/Admin/.claude/projects/d--Du-An-CRMTuyensinh/memory/person-enrollment-model.md),
> [subdomain-layout](../../C:/Users/Admin/.claude/projects/d--Du-An-CRMTuyensinh/memory/subdomain-layout.md).

---

## 1. Phạm vi v1

**Có trong v1:**
- FE public Nuxt 3 SSG: landing 1 trang chủ + 9 trang chi tiết khóa + danh sách khóa + tin tức (list + chi tiết) + liên hệ + đặt cọc.
- CRM admin Django: quản lý lead, course, order, payment, student, document, blog. 4 group quyền (sale, kế toán, văn thư, admin).
- PWA học viên Nuxt 3 CSR: đăng nhập SĐT + OTP Zalo ZNS, upload hồ sơ, xem công nợ.
- Backend Django + DRF + PostgreSQL: 11 apps theo plan đã chốt.
- Tích hợp: Casso webhook đối soát QR, VietQR generator, Telegram bot, Zalo ZNS, FB Lead Ads webhook.
- Auto-purge CCCD 90 ngày (NĐ 13/2023).
- In PDF đơn đăng ký học lái xe.

**KHÔNG có trong v1 (làm sau):**
- Hoa hồng sale tự động.
- LMS thật (video + thi thử 600 câu).
- Liên thông API Sở GTVT.
- Native app học viên (chỉ PWA).
- Multi-branch (1 trung tâm duy nhất).
- Báo cáo tài chính phức tạp.
- Email marketing automation.
- AI/ML lead scoring.

---

## 2. Tech stack chi tiết

### Backend
| Component | Lựa chọn | Lý do |
|---|---|---|
| Framework | Django 5.0 | Built-in admin tốt, ORM mạnh, ecosystem VN phổ biến |
| API | Django REST Framework 3.15 | Pattern chuẩn, serializer + permission rõ |
| DB | PostgreSQL 16 | TIMESTAMPTZ, JSONB, full-text search VN |
| Queue | Celery 5.4 + Redis 7 | Send Zalo ZNS, Telegram, cron purge CCCD |
| Admin UI | django-unfold | Modern look, tận dụng auth + group có sẵn |
| Storage file | Local filesystem (dev) / S3-compatible MinIO (prod) | Đơn giản, tự host được |
| PDF | WeasyPrint hoặc ReportLab | WeasyPrint cho HTML → PDF (mẫu Sở GTVT) |
| Validation | Pydantic 2 cho settings, DRF serializer cho API | Type-safe |
| Testing | pytest + pytest-django + factory_boy | Standard |

### Frontend
| Component | Lựa chọn | Lý do |
|---|---|---|
| Meta-framework | Nuxt 3.x | SSG/ISR cho SEO, file-based routing |
| UI | Tailwind CSS 3 + headlessui/vue | Theo taste-skill, không UI kit nặng |
| Form | Vee-Validate 4 + Yup | Validation tốt |
| Icons | @phosphor-icons/vue | Theo taste-skill |
| Image | @nuxt/image | Auto srcset + lazy + format |
| SEO | @nuxtjs/sitemap + @nuxtjs/robots + nuxt-schema-org | Đủ bộ SEO |
| Analytics | @nuxtjs/plausible hoặc GA4 | Privacy-friendly nếu chọn Plausible |
| Font | Self-hosted Geist | Tránh leak PII qua Google Fonts |

### DevOps
| Component | Lựa chọn | Lý do |
|---|---|---|
| FE public hosting | Cloudflare Pages | Free, edge CDN, Vietnam coverage tốt |
| BE hosting | VPS (Hetzner / DigitalOcean / Vultr SGP) | $20-40/tháng, full control |
| DB | Managed Postgres trên cùng VPS region | Latency thấp, snapshot dễ |
| Object storage | MinIO self-hosted hoặc Cloudflare R2 | R2 free egress, tốt cho file CCCD |
| DNS + CDN + WAF | Cloudflare (free plan) | Proxy 3 subdomain |
| Monitoring | Sentry (free tier) + uptimerobot | Đủ cho v1 |
| CI/CD | GitHub Actions | Free, đơn giản |

---

## 3. Cấu trúc thư mục

### Repository layout

```
D:/Du_An/CRMTuyensinh/
├── backend/                    # Django project
│   ├── manage.py
│   ├── pyproject.toml          # Poetry hoặc uv
│   ├── config/                 # Settings package
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── dev.py
│   │   │   ├── prod.py
│   │   │   └── test.py
│   │   ├── urls.py
│   │   ├── celery.py
│   │   └── wsgi.py / asgi.py
│   ├── apps/
│   │   ├── users/              # User + Group (sale, accountant, clerk, admin)
│   │   ├── courses/            # Course + Schedule + DocumentRequirement
│   │   ├── leads/              # Lead + LeadContact + LeadReason + LeadNote
│   │   ├── orders/             # Enrollment (= Order)
│   │   ├── payments/           # Payment + CassoTransaction + VietQR
│   │   ├── students/           # StudentAccount + Person + AccountPersonLink + OTPRequest
│   │   ├── documents/          # DocumentType + PersonDocument + EnrollmentDocument
│   │   ├── blog/               # BlogPost + BlogCategory + BlogTag
│   │   ├── notifications/      # NotificationTemplate + NotificationLog + Telegram/ZNS adapters
│   │   ├── marketing/          # LeadCaptureForm + FBLeadAdsWebhook
│   │   └── core/               # SystemSetting + AuditLog + utils
│   ├── templates/              # Django Admin override + email + PDF
│   ├── static/                 # Admin custom CSS
│   ├── media/                  # User upload (dev only)
│   └── tests/                  # Integration tests
│
├── frontend-public/            # Nuxt 3 SSG (tencongty.vn)
│   ├── nuxt.config.ts
│   ├── package.json
│   ├── app.vue
│   ├── pages/
│   │   ├── index.vue
│   │   ├── khoa-hoc/
│   │   │   ├── index.vue
│   │   │   └── [slug].vue
│   │   ├── tin-tuc/
│   │   │   ├── index.vue
│   │   │   └── [slug].vue
│   │   ├── lien-he.vue
│   │   └── dh/[code].vue       # Trang đặt cọc QR (public, có token)
│   ├── components/
│   ├── composables/
│   ├── layouts/
│   ├── public/
│   └── assets/                 # Fonts, CSS
│
├── frontend-student/           # Nuxt 3 PWA (hocvien.tencongty.vn)
│   ├── nuxt.config.ts
│   ├── pages/
│   │   ├── dang-nhap.vue       # SĐT + OTP
│   │   ├── dashboard.vue       # List enrollments
│   │   ├── enrollment/[id].vue # Chi tiết đơn + upload hồ sơ
│   │   └── quick/[token].vue   # Quick view không cần login
│   ├── components/
│   └── plugins/
│
├── docs/                       # ← Tài liệu thiết kế (đang ở đây)
│   ├── README.md
│   ├── 01-wireframes-fe-public.md
│   ├── 02-design-system.md
│   ├── 03-phase1-plan.md
│   └── wireframes-html/
│
├── docker/                     # Optional: compose cho dev local
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   └── nginx/
│
├── .github/workflows/          # CI/CD
│   ├── backend-ci.yml
│   ├── frontend-public-ci.yml
│   └── frontend-student-ci.yml
│
├── .gitignore
└── README.md
```

### Django app `leads/` (mẫu cho các app khác)

```
apps/leads/
├── __init__.py
├── apps.py
├── models.py              # Lead, LeadContact, LeadReason, LeadNote
├── admin.py               # Custom admin tùy biến với LeadContactInline + modal 2 cột
├── serializers.py         # DRF serializers
├── views.py               # ViewSets + capture endpoint
├── urls.py                # /api/leads/...
├── permissions.py         # IsInGroup('sale'), IsAssignedToLead, etc.
├── filters.py             # DjangoFilter cho status/priority/source
├── signals.py             # post_save Lead → Telegram alert
├── tasks.py               # Celery tasks (send Telegram)
├── migrations/
└── tests/
    ├── test_models.py
    ├── test_api.py
    └── test_admin.py
```

---

## 4. Sprint plan

### Sprint 1 — Backbone CRM + Landing (Tuần 1-3)

**Tuần 1: Setup + Auth + Models lõi**

| Ngày | Task | Deliverable |
|---|---|---|
| 1-2 | Setup Django project + Poetry + Postgres + Redis + Celery + pre-commit | Project chạy `python manage.py runserver` OK |
| 2-3 | App `users`: Custom User (phone unique), 4 Group (sale/accountant/clerk/admin), permissions seed fixture | Tạo user qua admin, gán group được |
| 3-4 | App `courses`: Course (9 hạng), CourseSchedule, DocumentRequirement | Tạo Course qua admin, set is_visible toggle |
| 4-5 | App `students`: StudentAccount, Person, AccountPersonLink, OTPRequest skeleton | Models + migration OK |
| 5 | Setup django-unfold cho admin UI, theme xanh lá | Admin có brand đúng |

**Tuần 2: Lead module + Telegram + Order skeleton**

| Ngày | Task | Deliverable |
|---|---|---|
| 1-2 | App `leads`: Lead, LeadContact, LeadReason, LeadNote models | Migration OK |
| 2-3 | API capture lead `POST /api/leads/` (public, có honeypot, rate limit) | curl test OK, lưu DB |
| 3 | Signal post_save Lead → Celery task Telegram | Nhận tin nhắn Telegram khi tạo lead |
| 4 | Admin tùy biến lead: modal "Ghi nhận liên hệ" 2 cột (form trái, timeline phải) — clone pattern website_thanhdat | Sale dùng được trên admin |
| 5 | App `orders`: Enrollment model + API `POST /api/leads/{id}/convert` atomic transaction | Lead → Enrollment idempotent |

**Tuần 3: Payment + Casso webhook + Setup Nuxt FE**

| Ngày | Task | Deliverable |
|---|---|---|
| 1-2 | App `payments`: Payment, CassoTransaction models. VietQR generator | Generate QR có data đúng |
| 2-3 | Webhook `POST /webhook/casso` với HMAC verify, regex match `ORD-xxxxx`, atomic confirm | Mock webhook test pass |
| 3 | Cron Celery beat: re-check pending payments mỗi 5 phút (fallback) | Task chạy đúng giờ |
| 4-5 | Setup Nuxt 3 project + Tailwind config theo `02-design-system.md` + Geist font self-host | Trang trống chạy OK |

**Sprint 1 Acceptance:**
- Sale tạo lead, gọi điện, ghi LeadContact, chuyển đơn → Enrollment tạo.
- HV mở trang `tencongty.vn/dh/ORD-12345`, thấy QR, chuyển khoản, Casso webhook tự confirm → Enrollment paid.
- Telegram alert real-time khi có lead mới.
- Django Admin có 4 group quyền hoạt động đúng (sale không xem được Payment confirm).

---

### Sprint 2 — FE public hoàn chỉnh + PWA HV + Blog + PDF (Tuần 4-5)

**Tuần 4: FE public các trang**

| Ngày | Task | Deliverable |
|---|---|---|
| 1-2 | Trang chủ Nuxt: implement đầy đủ theo `wireframes-html/index.html` | Lighthouse Performance > 90 |
| 2 | Trang danh sách khóa + chi tiết khóa (9 trang dynamic) | SEO meta + schema Course đầy đủ |
| 3 | Trang đặt cọc QR `/dh/[code]` với polling Casso status mỗi 3s | Live update "đã nhận cọc" |
| 4 | Trang liên hệ + Google Map embed + form capture lead | Form submit OK |
| 5 | Sitemap.xml + robots.txt + schema LocalBusiness/Course/FAQPage | Validate Schema.org OK |

**Tuần 5: PWA học viên + Blog + PDF + Auto-purge**

| Ngày | Task | Deliverable |
|---|---|---|
| 1 | App `notifications`: Zalo ZNS adapter (template đã duyệt) + OTP flow | Gửi OTP test OK |
| 2 | PWA HV: trang đăng nhập SĐT + OTP, JWT access 15p + refresh 30 ngày | Login OK |
| 2-3 | PWA dashboard: list Enrollment sort theo priority + hiển thị missing docs | Mobile responsive |
| 3 | App `documents`: PersonDocument + EnrollmentDocument + upload API (verify magic bytes, max 5MB) | Upload từ PWA OK |
| 4 | Admin văn thư: trang duyệt hồ sơ, quyền "upload hộ" | Văn thư duyệt được |
| 5 | App `blog`: model + admin + API + Nuxt trang `/tin-tuc` + `/tin-tuc/[slug]` | Blog hiển thị FE |
| 5 | PDF generator đơn đăng ký (WeasyPrint, mẫu Sở GTVT) | Download PDF OK |
| 5 | Celery beat task auto-purge CCCD sau 90 ngày | Test với date manipulation |

**Sprint 2 Acceptance:**
- FE public render đầy đủ 8 loại trang, SEO score Lighthouse > 90.
- HV vào `hocvien.tencongty.vn`, nhập SĐT, nhận OTP Zalo, đăng nhập, thấy dashboard với 1+ Enrollment.
- HV upload CCCD/ảnh chân dung/giấy khám SK → văn thư duyệt trong CRM → in PDF đơn đăng ký.
- Blog FE hiển thị đẹp, schema Article validate OK.
- Cron purge xóa CCCD đúng hạn 90 ngày.

---

### Sprint 3 — Tích hợp marketing + tối ưu + Deploy (Tuần 6-7)

**Tuần 6: Marketing + tối ưu**

| Ngày | Task | Deliverable |
|---|---|---|
| 1-2 | App `marketing`: FB Lead Ads webhook (verify token + push lead auto) | Test với form FB thật |
| 2-3 | Quick view JWT 24h link cho học viên qua Zalo ZNS | HV xem công nợ không cần login |
| 3-4 | Báo cáo cơ bản: doanh thu theo ngày, conversion lead → enrollment → paid | Export Excel đúng định dạng VN (dấu phân cách `.`, `,`) |
| 4 | Audit log model + middleware ghi CRUD + sensitive view | View được audit trail trên admin |
| 5 | Security harden: rate limit OTP, CSRF, CORS, IDOR test, security headers (CSP, HSTS) | Pass Mozilla Observatory grade A |

**Tuần 7: Deploy + QA + Launch**

| Ngày | Task | Deliverable |
|---|---|---|
| 1-2 | Setup VPS prod + nginx + SSL wildcard Let's Encrypt + Postgres + Redis + MinIO | 3 subdomain live HTTPS |
| 2 | Setup CI/CD GitHub Actions: BE test + lint + deploy auto. FE deploy lên Cloudflare Pages | Push main → deploy auto |
| 3 | Smoke test end-to-end: capture lead → sale chốt → HV cọc → upload → văn thư duyệt → in PDF | Tất cả flow pass |
| 4 | UX polish: animation, microcopy VN, error states, empty states | Visual QA pass |
| 5 | Soft launch: 5 lead test thật, theo dõi log + Sentry | Không crit error |

**Sprint 3 Acceptance:**
- Tất cả 3 subdomain live trên domain thật (tới lúc này user mua xong domain).
- Sentry tracking, uptime monitoring chạy.
- 1 chiến dịch FB ads test push được lead vào CRM.
- Báo cáo doanh thu/conversion xem được trên admin.

---

## 5. Acceptance criteria toàn dự án (Definition of Done v1)

### Chức năng
- ✅ Sale tạo lead, theo dõi, chuyển đơn không bị mất dữ liệu.
- ✅ HV cọc qua QR, hệ thống tự confirm trong 2 phút.
- ✅ HV đăng nhập, upload hồ sơ, văn thư duyệt, in PDF đơn đăng ký.
- ✅ Auto-purge CCCD 90 ngày chạy đúng.
- ✅ FE public Lighthouse 4 chỉ số > 90 (Performance, Accessibility, Best Practices, SEO).
- ✅ Schema.org validate OK trên trang khóa học + blog.

### Bảo mật
- ✅ Rate limit OTP 5/giờ/SĐT.
- ✅ CSRF + CORS + CSP headers đúng.
- ✅ Magic bytes check upload (chống upload exe nguỵ trang ảnh).
- ✅ IDOR test: HV A không xem được Enrollment của HV B.
- ✅ Admin RBAC: 4 group có quyền đúng theo ma trận `[06 phân quyền theo flow]`.
- ✅ Audit log mọi action CRUD + view sensitive (CCCD, payment).

### Vận hành
- ✅ Backup Postgres daily, retention 30 ngày.
- ✅ Monitoring Sentry + Uptimerobot active.
- ✅ Docs cho user cuối: hướng dẫn sale, kế toán, văn thư dùng CRM.

### Performance
- ✅ API response < 300ms p95.
- ✅ Postgres queries không có N+1 (kiểm tra bằng `django-silk` trong dev).
- ✅ FE LCP < 2.5s trên 4G mobile.

---

## 6. Dependencies bạn cần chuẩn bị

### Bạn cần cung cấp trước Sprint 1
1. **Tên trung tâm chính thức** (thay "Đông Á" placeholder).
2. **Logo** (SVG hoặc PNG transparent, 512x512+).
3. **Số hotline thật**.
4. **Địa chỉ trung tâm thật** + tọa độ Google Maps.
5. **Mẫu PDF đơn đăng ký Sở GTVT Bình Phước** (PDF hoặc Word).
6. **Token Telegram bot + chat ID** để alert sale.

### Bạn cần đăng ký trước Sprint 2
1. **Tài khoản Casso** (~9k/tháng) — đăng ký tại casso.vn, liên kết với tài khoản ngân hàng nhận cọc.
2. **Zalo OA + template ZNS** — đăng ký Zalo Official Account, submit template OTP để duyệt (mất 3-5 ngày làm việc, làm sớm).
3. **20-30 ảnh thật của trung tâm**: HLV, học viên, sân tập, xe tập, lớp lý thuyết.
4. **Nội dung 5-10 bài blog đầu tiên** (text Word/Markdown).

### Bạn cần chuẩn bị trước Sprint 3
1. **Tên miền chính thức** + DNS access.
2. **Facebook Page + Lead Ads app** nếu muốn FB integration.
3. **Danh sách giáo viên + lý lịch + ảnh chân dung** (cho trang chi tiết khóa).

---

## 7. Rủi ro và phương án giảm thiểu

| Rủi ro | Tác động | Mitigation |
|---|---|---|
| Zalo ZNS template duyệt chậm | Tuần 5 không có OTP gửi được | Đăng ký template từ tuần 1. Fallback SMS brandname có sẵn. |
| Casso không liên kết được với ngân hàng đang dùng | Không đối soát tự động | Liên hệ Casso check trước. Phương án dự phòng: kế toán confirm tay trong CRM. |
| Mẫu PDF Sở GTVT thay đổi giữa chừng | PDF in không hợp lệ | Dùng template HTML-based để dễ sửa. Văn thư review trước khi nộp Sở. |
| Sở GTVT yêu cầu format đặc biệt (chữ ký số, mã QR riêng) | PDF không nộp được | Hỏi Sở GTVT Bình Phước trước khi code. Có thể fallback in giấy + ký tay v1. |
| HV trung niên không quen smartphone | Upload hồ sơ tắc | Văn thư có quyền "upload hộ" đã thiết kế sẵn. |
| Lưu lượng FB ads cao gây overload | Server down giờ cao điểm | Rate limit lead capture 60/phút/IP. Cloudflare WAF chặn DDoS. |
| Dev solo, bug khó debug | Trễ tiến độ | Setup Sentry từ Sprint 1. Test coverage > 70% cho payment/auth. |

---

## 8. Lệnh setup nhanh (cho developer)

### Backend dev local

```bash
cd D:/Du_An/CRMTuyensinh/backend

# Tạo virtualenv (Python 3.12+)
python -m venv .venv
.venv\Scripts\activate.bat  # Windows

# Cài dependencies
pip install -U pip
pip install poetry
poetry install

# Setup Postgres local
# (Cài Postgres 16 trước. Tạo DB:)
createdb crm_tuyensinh_dev

# Migrations + superuser
python manage.py migrate
python manage.py createsuperuser
python manage.py loaddata fixtures/groups.json fixtures/courses.json

# Chạy
python manage.py runserver

# Trong terminal khác: Celery worker
celery -A config worker -l info -P solo  # Windows dùng -P solo
celery -A config beat -l info             # Cron tasks
```

### FE public dev local

```bash
cd D:/Du_An/CRMTuyensinh/frontend-public

pnpm install
pnpm dev   # http://localhost:3000
```

### FE student dev local

```bash
cd D:/Du_An/CRMTuyensinh/frontend-student

pnpm install
pnpm dev   # http://localhost:3001
```

### Biến môi trường (`.env`)

```env
# Backend
DJANGO_SETTINGS_MODULE=config.settings.dev
DJANGO_SECRET_KEY=...
BASE_DOMAIN=tencongty.vn
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/crm_tuyensinh_dev
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# Casso
CASSO_WEBHOOK_SECRET=...
CASSO_API_KEY=...

# Zalo ZNS
ZNS_ACCESS_TOKEN=...
ZNS_REFRESH_TOKEN=...
ZNS_TEMPLATE_ID_OTP=...
ZNS_TEMPLATE_ID_DEPOSIT_INFO=...

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Storage
MEDIA_BACKEND=local  # hoặc s3
S3_ENDPOINT=https://...r2.cloudflarestorage.com
S3_BUCKET=crm-tuyensinh
S3_ACCESS_KEY=...
S3_SECRET_KEY=...

# FE
NUXT_PUBLIC_API_BASE=https://crm.tencongty.vn/api
NUXT_PUBLIC_BASE_URL=https://tencongty.vn
NUXT_PUBLIC_STUDENT_URL=https://hocvien.tencongty.vn
```

---

## 9. Liên kết tới các tài liệu khác

- [README.md](./README.md) — index tài liệu
- [01-wireframes-fe-public.md](./01-wireframes-fe-public.md) — ASCII wireframe 8 trang FE
- [02-design-system.md](./02-design-system.md) — palette, typography, motion, components
- [wireframes-html/](./wireframes-html/) — HTML wireframe mở browser xem được

---

## 10. Sau v1 (preview Phase 2 sẽ làm sau)

Đây là idea pool để khi v1 chạy ổn, quay lại xem cái nào cần làm tiếp:

- LMS đầy đủ: video bài giảng + thi thử 600 câu có scoring
- Liên thông API Sở GTVT (nếu hỗ trợ ở Bình Phước)
- Native app Expo RN cho HV (offline-first upload hồ sơ)
- Báo cáo nâng cao: funnel analysis, time-to-convert, cohort
- Hoa hồng sale tự động
- Lead scoring AI (Gradient Boosting trên dữ liệu lịch sử)
- Multi-branch khi mở rộng chi nhánh
- Marketing automation (email drip campaign)
- Live chat widget thay vì chỉ Zalo
