# CRM Tuyển Sinh — Backend Django

Python 3.11+, Django 5, PostgreSQL (prod) hoặc SQLite (dev), Celery + Redis (prod).

## Setup local lần đầu

### 1. Tạo virtualenv và cài dependencies

```bash
cd D:/Du_An/CRMTuyensinh/backend
python -m venv .venv

# Activate venv:
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows Git Bash:
source .venv/Scripts/activate
# Linux/Mac:
source .venv/bin/activate

pip install --upgrade pip wheel
pip install -r requirements.txt
```

### 2. Tạo `.env`

```bash
cp .env.example .env  # Linux/Mac
copy .env.example .env  # Windows cmd
```

Mặc định `.env.example` đã set `DATABASE_URL` rỗng → dùng SQLite. Chạy ngay được, không cần Postgres.

Nếu muốn dùng Postgres local (đã có service đang chạy):

```env
DATABASE_URL=postgres://postgres:YOUR_PASSWORD@localhost:5432/crm_tuyensinh_dev
```

Trước đó tạo DB:
```bash
# Trong PowerShell với Postgres bin trong PATH:
& "C:\Program Files\PostgreSQL\17\bin\createdb.exe" -U postgres crm_tuyensinh_dev
```

### 3. Migrate + bootstrap data + tạo superuser

```bash
python manage.py migrate
python manage.py bootstrap_data
python manage.py createsuperuser
```

`bootstrap_data` tạo:
- 4 Group quyền: admin / sale / accountant / clerk
- 9 Course theo Luật 2025: A1, A, B1, B số tự động, B số sàn, C1, C, D1, D2
- 1 SiteSettings singleton mặc định

### 4. Chạy server

```bash
python manage.py runserver
```

Mở http://localhost:8000/admin/ → đăng nhập bằng superuser vừa tạo.

## Cấu trúc thư mục

```
backend/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── config/
│   ├── settings/
│   │   ├── base.py    # Common, đọc env vars
│   │   └── dev.py     # DEBUG=True, debug-toolbar, eager Celery
│   ├── urls.py
│   ├── celery.py
│   ├── wsgi.py
│   └── asgi.py
└── apps/
    ├── core/          # SiteSettings, SystemSetting, AuditLog + bootstrap_data
    ├── users/         # CustomUser (phone, full_name, multi-group)
    └── courses/       # Course, CourseSchedule (9 hạng GPLX Luật 2025)
```

Sprint 2 sẽ thêm: `leads/`, `orders/`, `payments/`, `students/`, `documents/`, `blog/`, `notifications/`, `marketing/`.

## Brand info chỉnh trên admin

Vào `/admin/` → "Thông tin trung tâm" → chỉnh:
- Tên trung tâm, logo, slogan
- Hotline (số máy + định dạng hiển thị)
- Địa chỉ + tọa độ Google Map + URL embed
- Email, Facebook, Zalo OA, YouTube
- Giấy phép, mã số thuế
- Stats hiển thị FE (số học viên đã đỗ, tỉ lệ đỗ, năm kinh nghiệm)
- SEO mặc định (meta title, description, OG image)

Mọi thông tin sẽ được pull qua API `/api/site-settings/` (sẽ làm tuần sau) cho Nuxt FE.

## Phân quyền (4 Group)

- `admin` — toàn quyền (toàn bộ permission Django built-in)
- `sale` — quản lý lead, tạo đơn từ lead
- `accountant` — xác nhận thanh toán, xem báo cáo
- `clerk` — duyệt hồ sơ, in đơn, upload hộ học viên

1 user có thể thuộc nhiều group (ví dụ: sale + kế toán nếu trung tâm nhỏ). Gán trong trang "Người dùng CRM" → tick checkbox group.

## Settings env vars

| Biến | Mặc định | Mô tả |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev-insecure-change-me | **Đổi trong prod**, dùng `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DJANGO_DEBUG` | False (dev.py override True) | |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated |
| `BASE_DOMAIN` | `tencongty.vn` | Đổi khi mua domain thật |
| `DATABASE_URL` | (trống = SQLite) | `postgres://...` để dùng Postgres |
| `REDIS_URL` | (trống) | Production set `redis://localhost:6379/0` |
| `CELERY_TASK_ALWAYS_EAGER` | False (dev.py override True) | Chạy sync, không cần Redis |
| `CASSO_WEBHOOK_SECRET` | "" | Sprint 1 tuần 3 sẽ dùng |
| `ZNS_*` | "" | Sprint 2 sẽ dùng |
| `TELEGRAM_BOT_TOKEN` | "" | Sprint 1 tuần 2 sẽ dùng |

## Lệnh hay dùng

```bash
# Tạo migration mới sau khi đổi model
python manage.py makemigrations

# Apply migration
python manage.py migrate

# Chạy bootstrap lại (idempotent, không phá data)
python manage.py bootstrap_data

# Mở Django shell với ipython
python manage.py shell

# Mở shell+ với auto-import models (django-extensions)
python manage.py shell_plus

# Show SQL của migration mà không apply
python manage.py sqlmigrate courses 0001

# Collect static cho prod
python manage.py collectstatic --noinput
```

## Test

```bash
pytest                          # Sẽ thêm pytest config Sprint 1 tuần 3
python manage.py test           # Built-in test runner
```

## Pending

Xem `../docs/03-phase1-plan.md` cho roadmap chi tiết 3 sprint.
