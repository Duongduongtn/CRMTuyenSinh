# Mapping Skill ↔ Phase ↔ Subagent

Phiên bản: v2, ngày 10/06/2026.
Phạm vi: 3 sprint của v1 + post-launch.

> **Nguyên tắc cốt lõi:**
> 1. **Taste-skill family là BẮT BUỘC và XUYÊN SUỐT** mọi phase có UI/UX. Không có exception.
> 2. **Mỗi phase có 1 gate reviewer** chạy ở cuối phase, đảm bảo không qua phase mới khi acceptance criteria chưa đạt.
> 3. **6 specialist reviewer** chạy liên tục trong phase, mỗi khi sửa file thuộc domain của mình.

---

## 1. Stack đã chốt (cập nhật v2)

| Layer | Stack | Lý do |
|---|---|---|
| Database | PostgreSQL 17 (prod) / SQLite (dev) | Production-ready, có sẵn local |
| Backend | Django 5 + DRF + Celery + Redis | Built-in auth, admin, ORM mạnh |
| FE public landing | Nuxt 3 SSG/ISR | SEO tốt cho Google |
| FE CRM admin | Vue 3 + Vite SPA | **Nhất quán với FE public** (user yêu cầu) — không cần SEO |
| FE PWA học viên | Nuxt 3 PWA CSR | SĐT+OTP, mobile-first |
| Django Admin (built-in) | django-unfold | Fallback cho superadmin / dev tool |

---

## 2. Tổng 24 skills trong `.claude/skills/`

### A. UI/Design (4) — XUYÊN PHASE 1+2+3

| Skill | Phase 1 | Phase 2 | Phase 3 | Vai trò |
|---|:-:|:-:|:-:|---|
| `taste-skill` | ✅ landing | ✅ PWA + blog | ✅ pre-flight | Dial system, anti-AI-slop, 80+ checkpoint |
| `minimalist-skill` | ✅ landing | ✅ blog | ✅ audit | Phong cách flat hiện đại |
| `soft-skill` | — | ✅ PWA premium | ✅ admin polish | Glass card, premium feel |
| `redesign-skill` | — | — | ✅ pre-launch | Audit AI-tells, fix UI |

### B. Backend Django (4)

| Skill | Phase 1 | Phase 2 | Phase 3 | Vai trò |
|---|:-:|:-:|:-:|---|
| `django-pro` | ✅ setup + models | ✅ API HV | ✅ perf | Pattern Django 5, ORM, async |
| `django-access-review` | ✅ admin perm | ✅ HV API | ✅ full audit | IDOR, object-level |
| `django-perf-review` | — | ✅ dashboard HV | ✅ pre-launch | N+1, prefetch |
| `api-patterns` | ✅ lead capture | ✅ student API | ✅ FB webhook | REST design |

### C. Database (2)

| Skill | Phase 1 | Phase 2 | Phase 3 | Vai trò |
|---|:-:|:-:|:-:|---|
| `postgresql` | ✅ schema setup | ✅ blog index | ✅ prod tune | Schema design, JSONB |
| `postgres-best-practices` | — | — | ✅ prod | RLS, pooling, replication |

### D. Auth + Security + Files + Payment (4)

| Skill | Phase 1 | Phase 2 | Phase 3 | Vai trò |
|---|:-:|:-:|:-:|---|
| `auth-implementation-patterns` | — | ✅ OTP HV | ✅ audit | JWT, OTP, session, rate limit |
| `file-uploads` | — | ✅ CCCD upload | ✅ audit | Magic bytes, EXIF strip, presigned |
| `payment-integration` | ✅ Casso webhook | ✅ payment partials | ✅ go-live | Idempotency, HMAC |
| `pdf-official` | — | ✅ in đơn | ✅ template polish | WeasyPrint/reportlab |

### E. SEO (2)

| Skill | Phase 1 | Phase 2 | Phase 3 | Vai trò |
|---|:-:|:-:|:-:|---|
| `seo-technical` | ✅ landing | ✅ blog | ✅ pre-launch | robots, sitemap, CWV |
| `seo-aeo-schema-generator` | ✅ Course/LB schema | ✅ Article schema | ✅ validate | JSON-LD |

### F. Frontend general (4 — bổ sung Vue/React không có specific)

| Skill | Phase 1 | Phase 2 | Phase 3 | Vai trò |
|---|:-:|:-:|:-:|---|
| `frontend-developer` | ✅ FE setup | ✅ PWA + CRM SPA | ✅ polish | General FE patterns Vue/React |
| `frontend-dev-guidelines` | ✅ structure | ✅ components | ✅ refactor | Code style, folder layout |
| `frontend-api-integration-patterns` | ✅ landing → API | ✅ PWA → API | ✅ CRM → API | Fetch, error, retry, cache |
| `senior-frontend` | ✅ architecture | ✅ state mgmt | ✅ perf opt | Senior-level patterns |

### G. Forms + Tailwind + Testing (4)

| Skill | Phase 1 | Phase 2 | Phase 3 | Vai trò |
|---|:-:|:-:|:-:|---|
| `form-cro` | ✅ lead capture form | ✅ upload form | ✅ A/B test | Form conversion, friction |
| `tailwind-patterns` | ✅ landing tokens | ✅ PWA + CRM | ✅ utility audit | Tailwind utility patterns |
| `test-driven-development` | ✅ critical path | ✅ HV flow test | ✅ pre-launch cov | TDD discipline |
| `unit-testing-test-generate` | ✅ models | ✅ services | ✅ regression | Generate test cases |

> **Lưu ý Vue/Nuxt**: Antigravity skill set không có Vue/Nuxt specialist. Dùng `frontend-developer` + `senior-frontend` + `frontend-dev-guidelines` cho general patterns, và `WebFetch` tới `nuxt.com` / `vuejs.org` khi cần.

---

## 3. Tổng 9 subagent trong `.claude/agents/`

### A. 6 Specialist reviewer (chạy liên tục trong phase)

| Subagent | Skills dùng | Trigger spawn |
|---|---|---|
| `backend-django-reviewer` | django-pro, django-access-review, django-perf-review, postgresql, postgres-best-practices | Sau sửa apps/*.py, settings, migration |
| `payment-integration-reviewer` | payment-integration, django-access-review | Sau sửa Casso webhook, VietQR |
| `frontend-ui-reviewer` | **taste-skill, minimalist-skill, soft-skill, redesign-skill** | Sau sửa .vue/.html/.css |
| `seo-public-reviewer` | seo-technical, seo-aeo-schema-generator | Khi thêm trang public, sửa schema |
| `security-rbac-reviewer` | django-access-review, file-uploads, auth-implementation-patterns | Trước launch, sau thêm endpoint |
| `lead-pipeline-reviewer` | django-pro, api-patterns, django-access-review | Sau sửa apps/leads/, apps/orders/ convert |

### B. 3 Phase-gate reviewer (chạy cuối phase)

| Subagent | Phase | Khi nào spawn |
|---|---|---|
| `phase1-gate-reviewer` | Cuối Sprint 1 (sau tuần 3) | User: "review Sprint 1", "phase 1 xong chưa" |
| `phase2-gate-reviewer` | Cuối Sprint 2 (sau tuần 5) | User: "review Sprint 2", "gate Sprint 2" |
| `phase3-prelaunch-reviewer` | Trước go-live (cuối tuần 7) | User: "review trước launch", "sẵn sàng deploy chưa" |

Phase-gate reviewer là **orchestrator** — sẽ đề xuất spawn các specialist reviewer rồi tổng hợp output.

---

## 4. Phase-by-phase RÕ RÀNG

### 🔸 PHASE 1 — Sprint 1 (Tuần 1-3): Backbone CRM + Landing core

**Code mới sẽ viết:**
- Backend: app users, core, courses, leads, orders, payments + Casso webhook
- FE public: trang chủ, list khóa, chi tiết khóa, đặt cọc QR

**Skills BẮT BUỘC đọc trước khi code:**
- `django-pro` + `postgresql` + `api-patterns` (backend)
- `payment-integration` (Casso + VietQR)
- `taste-skill` + `minimalist-skill` (UI landing) ← **TRIỆT ĐỂ**
- `seo-aeo-schema-generator` + `seo-technical` (landing SEO)
- `frontend-developer` + `tailwind-patterns` (FE Nuxt setup)
- `form-cro` (lead capture form)
- `test-driven-development` (critical path test)

**Subagent ĐƯỢC SPAWN trong Sprint 1:**

| Tuần | Subagent spawn liên tục | Output |
|---|---|---|
| 1 | `backend-django-reviewer` sau mỗi commit models/admin | Report findings |
| 2 | `backend-django-reviewer` + `lead-pipeline-reviewer` sau khi xong app leads | Coverage check |
| 3a | `payment-integration-reviewer` + `security-rbac-reviewer` sau Casso webhook | Idempotency + HMAC pass |
| 3b | `frontend-ui-reviewer` + `seo-public-reviewer` sau khi Nuxt landing có 3 trang | Anti-AI-slop pass |

**Gate spawn cuối Phase 1:** `phase1-gate-reviewer`
- Đầu vào: toàn bộ code Sprint 1
- Output: GO / GO-WITH-WARNINGS / NO-GO → quyết định qua Sprint 2

---

### 🔸 PHASE 2 — Sprint 2 (Tuần 4-5): PWA HV + Blog + PDF + Văn thư workflow

**Code mới sẽ viết:**
- Backend: app students (auth, OTP), documents (upload, văn thư duyệt, auto-purge), notifications (Zalo ZNS), blog
- FE public: blog list + detail, liên hệ, đặt cọc polling
- PWA học viên (`hocvien.tencongty.vn`): login OTP, dashboard, upload hồ sơ

**Skills BẮT BUỘC đọc trước khi code:**
- `auth-implementation-patterns` (OTP + JWT)
- `file-uploads` (CCCD + EXIF + magic bytes) ← **CRITICAL cho compliance NĐ 13/2023**
- `django-access-review` (IDOR cho HV)
- `pdf-official` (in đơn)
- `taste-skill` + `minimalist-skill` (UI PWA) ← **TRIỆT ĐỂ**
- `seo-aeo-schema-generator` (Article schema)
- `senior-frontend` (state management PWA + form)
- `form-cro` (upload form UX)
- `django-perf-review` (dashboard HV không N+1)

**Subagent SPAWN trong Sprint 2:**

| Tuần | Subagent | Trigger |
|---|---|---|
| 4 | `frontend-ui-reviewer` + `seo-public-reviewer` | Mỗi khi xong 1 trang FE |
| 4 | `payment-integration-reviewer` | Polling Casso + bổ sung partial payment |
| 5a | `security-rbac-reviewer` + `backend-django-reviewer` | Sau khi xong OTP + upload |
| 5b | `seo-public-reviewer` (blog schema) | Khi blog ready |
| 5b | `backend-django-reviewer` (PDF render) | Khi PDF generator ready |

**Gate spawn cuối Phase 2:** `phase2-gate-reviewer`
- Đầu vào: code Sprint 2 + verify Sprint 1 không regression
- Output: PASS / WARNINGS / FAIL → quyết định qua Sprint 3
- **CRITICAL:** check NĐ 13/2023 compliance trước khi PASS

---

### 🔸 PHASE 3 — Sprint 3 (Tuần 6-7): Marketing + Deploy + Pre-launch

**Code mới sẽ viết:**
- Backend: FB Lead Ads webhook + báo cáo + audit log middleware + security headers + quick-view JWT
- FE CRM admin: bắt đầu Vite + Vue 3 SPA (nếu user xác nhận build trong v1, tham khảo Phương án ở Q&A)
- Deploy: VPS + nginx + SSL wildcard + Cloudflare + CI/CD GitHub Actions

**Skills BẮT BUỘC đọc:**
- `postgres-best-practices` (prod tuning)
- `redesign-skill` (audit UI pre-launch)
- `taste-skill` Section 14 (pre-flight 80+ checkpoint) ← **TRIỆT ĐỂ FINAL**
- Tất cả security skill cho audit

**Subagent SPAWN trong Sprint 3:**

| Tuần | Subagent | Trigger |
|---|---|---|
| 6 | `lead-pipeline-reviewer` (FB webhook) + `security-rbac-reviewer` (quick-view JWT) | Sau khi xong FB integration |
| 6 | `backend-django-reviewer` (báo cáo + audit middleware) | Sau khi xong báo cáo |
| 7a | (manual review deploy config) | nginx, SSL, CI/CD |
| 7b | **TẤT CẢ 6 specialist subagent chạy song song** | Pre-launch audit |

**Gate spawn cuối Phase 3:** `phase3-prelaunch-reviewer`
- Sẽ tự đề xuất spawn 5 specialist trước khi cho GO/NO-GO
- Đầu vào: toàn bộ code + deploy + monitoring
- Output: **GO / GO-WITH-CAVEATS / NO-GO** — quyết định cuối cùng

---

## 5. Áp dụng TASTE-SKILL TRIỆT ĐỂ (CRITICAL)

User nhấn mạnh nhiều lần. Quy trình BẮT BUỘC:

### A. Trước khi viết bất kỳ component .vue/.html/.css mới

1. Đọc `.claude/skills/taste-skill/SKILL.md` Section 0-5 (brief inference + 3 dials).
2. Confirm 3 dials:
   - `DESIGN_VARIANCE = 6` (asymmetric, không experimental quá)
   - `MOTION_INTENSITY = 5` (smooth, không kinetic)
   - `VISUAL_DENSITY = 4` (breathing room)
3. Đọc `memory/taste-skill-paths.md` để biết cài đặt mặc định + palette dự án.
4. Mở mẫu chuẩn `docs/wireframes-html/index.html` để tham khảo.

### B. Khi viết — quy tắc CỨNG (không exception)

- **ZERO em-dash `—`** trong .vue/.html/.md user-facing.
- **1 accent color** duy nhất: emerald-600/700. KHÔNG purple gradient.
- **1 corner-radius system**: rounded-md/lg/xl, không mix.
- **Asymmetric** thay vì 3 card đều giữa trang.
- **Real images** (Unsplash hoặc gen-tool), KHÔNG fake-div screenshot.
- **Phosphor Icons**, KHÔNG hand-roll SVG.
- **Hero fit viewport**: headline ≤ 2 dòng, subtext ≤ 20 từ, CTA visible no-scroll.
- **Geist Sans**, KHÔNG Inter, KHÔNG Fraunces serif.
- **Vietnamese diacritic clearance**: `leading-[1.05]+` và `pb-1` cho heading có `ư/ơ/ờ/ễ/ặ`.
- **Off-black `#0F1F1A`** + **off-white `#FFFFFF`**, không `#000`/`#fff` thuần.

### C. Sau khi viết — pre-flight 4 step

1. `frontend-ui-reviewer` spawn trên file vừa sửa.
2. Đọc Section 14 của `taste-skill/SKILL.md` — 80+ checkpoint, tick từng cái.
3. Test 3 viewport: mobile 375px, tablet 800px, desktop 1440px.
4. Test `prefers-reduced-motion: reduce`.

### D. Reviewer chặn merge nếu vi phạm CRITICAL

`frontend-ui-reviewer` PHẢI fail PR nếu thấy:
- `—` em-dash bất kỳ vị trí
- 3 card đều ở section feature
- AI purple gradient
- Centered hero + dark mesh
- Fake-div screenshot
- Hand-rolled SVG icon
- Generic copy (`Elevate`, `Seamless`, `Unleash`, `Reimagine`, `Next-Gen`)

---

## 6. Cách spawn subagent (lệnh thực tế)

### Cách 1: Claude tự đề xuất

Khi user nói "review lead capture" → Claude tự nhận và đề xuất:
```
Tôi sẽ spawn lead-pipeline-reviewer + backend-django-reviewer để review song song.
```

### Cách 2: User gọi tay

```
"Spawn backend-django-reviewer review apps/courses/models.py"
"Chạy frontend-ui-reviewer kiểm tra index.html"
"Dùng phase1-gate-reviewer audit toàn bộ Sprint 1"
"Phase 3 pre-launch review"
```

### Cách 3: Lệnh tổng (Sprint 3 sẽ tạo slash commands)

```
/review-backend   → spawn backend-django-reviewer
/review-ui        → spawn frontend-ui-reviewer
/review-payment   → spawn payment-integration-reviewer
/review-security  → spawn security-rbac-reviewer + payment-integration-reviewer
/gate-phase1      → spawn phase1-gate-reviewer
/gate-phase2      → spawn phase2-gate-reviewer
/prelaunch        → spawn phase3-prelaunch-reviewer
```

---

## 7. Ma trận trách nhiệm tổng quan

| Phase | BE | UI/UX | Auth | Payment | SEO | Gate |
|---|---|---|---|---|---|---|
| **Phase 1** | backend-django + lead-pipeline | **frontend-ui (taste cốt lõi)** | security-rbac (basic) | payment-integration | seo-public (landing) | `phase1-gate-reviewer` |
| **Phase 2** | backend-django + django-perf | **frontend-ui (PWA + taste)** | security-rbac (HV full) | payment-integration (partials) | seo-public (blog) | `phase2-gate-reviewer` |
| **Phase 3** | backend-django (perf prod) | **frontend-ui + redesign-skill** | security-rbac (final) | payment-integration (final) | seo-public (CWV final) | `phase3-prelaunch-reviewer` |

---

## 8. Liên kết tài liệu

- `.claude/skills/` — 24 skills (xem section 2)
- `.claude/agents/` — 9 subagent (xem section 3)
- `docs/02-design-system.md` — design tokens chuẩn dự án (palette, font, motion)
- `docs/03-phase1-plan.md` — sprint task chi tiết
- Memory `taste-skill-paths.md` — palette + dial mặc định
- Memory `claude-project-tooling.md` — index .claude/

---

## 9. Checklist cho mỗi commit (developer)

Trước khi `git commit`:
1. [ ] Đã đọc skill liên quan đến code đang sửa.
2. [ ] Nếu sửa .vue/.html → đã chạy `frontend-ui-reviewer` mentally hoặc spawn agent.
3. [ ] Nếu sửa model/migration → đã chạy `backend-django-reviewer`.
4. [ ] Nếu sửa webhook/payment → đã chạy `payment-integration-reviewer`.
5. [ ] Test có pass (manual hoặc unit test).
6. [ ] Không leak secret, không commit `.env`.

Cuối phase: spawn gate reviewer tương ứng. Không qua phase mới khi chưa PASS.
