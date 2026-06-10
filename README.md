# CRM Tuyển Sinh Học Lái Xe

Hệ thống quản lý tuyển sinh cho trung tâm đào tạo lái xe, bao gồm:
- Landing page tuyển sinh SEO Google
- CRM quản lý lead, đơn hàng, thanh toán, hồ sơ học viên
- App học viên upload hồ sơ và xem công nợ
- Tích hợp thanh toán QR online (Casso đối soát tự động)

## Stack

| Layer | Stack | Subdomain |
|---|---|---|
| FE public landing | Nuxt 3 SSG | `tencongty.vn` |
| FE CRM admin | Vue 3 + Vite SPA + shadcn-vue | `crm.tencongty.vn` |
| FE PWA học viên | Nuxt 3 CSR | `hocvien.tencongty.vn` |
| Backend | Django 5 + DRF + Celery + PostgreSQL | `crm.tencongty.vn/api/` |
| Payment | VietQR + Casso webhook | |
| Notification | Telegram bot + Zalo ZNS | |

## Cấu trúc thư mục

```
.
├── backend/          # Django REST API + admin
├── frontend-public/  # Nuxt 3 SSG (sẽ scaffold ở Sprint 1 Tuần 3)
├── frontend-crm/     # Vue 3 + Vite (sẽ scaffold ở Sprint 2)
├── frontend-student/ # Nuxt 3 PWA (sẽ scaffold ở Sprint 2)
├── docs/             # Wireframes, design system, plan, mapping
├── .claude/          # Skills + reviewer subagents cho Claude Code
└── .vscode/          # IDE settings
```

## Phát triển local (Backend)

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
# .venv\Scripts\Activate.ps1     # PowerShell

pip install -r requirements.txt
cp .env.example .env

python manage.py migrate
python manage.py bootstrap_data           # 4 group + 9 khóa + SiteSettings
python manage.py createsuperuser
python manage.py runserver
```

Mở http://localhost:8000/admin/login/.

Chi tiết: [backend/README.md](./backend/README.md).

## Tài liệu thiết kế

- [docs/README.md](./docs/README.md) — index tổng quan
- [docs/01-wireframes-fe-public.md](./docs/01-wireframes-fe-public.md) — wireframe ASCII 8 trang FE
- [docs/02-design-system.md](./docs/02-design-system.md) — palette, typography, motion
- [docs/03-phase1-plan.md](./docs/03-phase1-plan.md) — plan 3 sprint chi tiết
- [docs/04-skills-agents-mapping.md](./docs/04-skills-agents-mapping.md) — mapping skill × phase × subagent
- [docs/wireframes-html/](./docs/wireframes-html/) — HTML wireframe mở browser xem được

## Trạng thái dự án

- ✅ Sprint 1 Tuần 1: Backend skeleton + apps `core` (SiteSettings) + `users` + `courses` (9 hạng Luật 2025)
- ✅ Sprint 1 Tuần 2: App `leads` + capture API + Telegram alert
- 🔜 Sprint 1 Tuần 3: App `orders` + `payments` + Casso webhook + scaffold Nuxt landing
- 🔜 Sprint 2: PWA học viên, app blog, PDF generator, Vue CRM SPA
- 🔜 Sprint 3: Marketing webhook, báo cáo, deploy
