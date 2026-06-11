# Infra / Deploy — CRM Tuyển Sinh

Bộ template + runbook để deploy CRM Tuyển Sinh lên VPS production (Sprint 3 Tuần 7).

## Kiến trúc tổng quan

```
                         ┌─────────────────────────────────────────────┐
                         │              VPS 36.50.26.199               │
                         │      (BNIX, Ubuntu 22.04 dùng chung)        │
                         │                                             │
   trungtamthanhdat.com ─┼─► Cloudflare Pages (FE public Nuxt SSG)     │
                         │                                             │
sale.trungtamthanhdat.com┼─► nginx host :443 ────► /var/www/thanhdat/  │
                         │                       │   frontend-crm/dist │
                         │                       │   (Vue SPA static)  │
                         │                       └─► /api/ proxy       │
                         │                            127.0.0.1:8003   │
                         │                            └──► thanhdat-backend (Django gunicorn)
                         │                                  ├──► thanhdat-db (Postgres 17)
                         │                                  ├──► thanhdat-redis
                         │                                  ├──► thanhdat-celery-worker
                         │                                  └──► thanhdat-celery-beat
                         │                                             │
hocvien.trungtamthanhdat.com ─► nginx host :443 ─► /var/www/thanhdat/  │
                         │                          frontend-student/  │
                         │                          .output/public/    │
                         │                          (Nuxt CSR static)  │
                         └─────────────────────────────────────────────┘
```

Phân chia rõ:
- **nginx native trên host** xử lý SSL Let's Encrypt + reverse proxy + serve FE static.
- **Docker compose** chỉ chạy services backend (Postgres / Redis / Django gunicorn / Celery).
- **FE build artifact** rsync trực tiếp lên `/var/www/thanhdat/frontend-crm/dist/` qua CI/CD (không cần container FE riêng).
- **Bind mount volume** `/var/www/thanhdat/backend-media` + `backend-static` để nginx host serve được trực tiếp file static + media.

## Pre-requisites

- [x] VPS Ubuntu 22.04 đã có Docker 29 + Compose v5, nginx 1.18, certbot 1.21.
- [x] Domain `trungtamthanhdat.com` đã mua.
- [x] DNS A record:
  - `sale.trungtamthanhdat.com` → 36.50.26.199
  - `hocvien.trungtamthanhdat.com` → 36.50.26.199 (nếu deploy PWA HV lên VPS)
  - `trungtamthanhdat.com` → Cloudflare Pages (CNAME, không phải VPS)
- [x] SSH key Claude: `~/.ssh/id_vps_production` (đã có).
- [x] Deploy key SSH `/root/.ssh/github_thanhdat` đã gen trên VPS (xem bước 2 dưới).
- [ ] Public key `/root/.ssh/github_thanhdat.pub` đã add vào GitHub Deploy Keys của repo `Duongduongtn/CRMTuyenSinh`.
- [ ] GitHub Actions secrets đã add (xem mục CI/CD bên dưới).

## File trong thư mục này

| File | Mục đích |
|---|---|
| `Dockerfile.backend` | Image Django + gunicorn (multi-stage, Python 3.12, có GTK runtime cho weasyprint PDF). |
| `.dockerignore` | Loại node_modules, venv, .env, frontend, .git khỏi build context. |
| `docker-compose.prod.yml` | Compose 5 service: db / redis / backend / celery-worker / celery-beat. |
| `.env.prod.example` | Template env. Copy thành `.env.prod` trên VPS (đặt bên cạnh compose). |
| `nginx/sale.trungtamthanhdat.com.conf` | nginx server block cho CRM SPA + /api proxy. |
| `nginx/hocvien.trungtamthanhdat.com.conf` | nginx server block cho PWA học viên. |
| `nginx/snippets/thanhdat-security-headers.conf` | Header HSTS/XCT/Permissions Policy include cho cả 2 server. |
| `../.github/workflows/deploy.yml` | CI/CD: test BE → build FE → SSH deploy → smoke test. |

## Setup lần đầu trên VPS (chỉ chạy 1 lần)

### 1. Add public key vào GitHub Deploy keys

Public key đã gen:
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIFYEH7Sg/F4pCL3NsSdMan4yG7bvqzSD65UU0RpYBdG github-deploy-key-thanhdat-crm
```

→ Vào `https://github.com/Duongduongtn/CRMTuyenSinh/settings/keys` → "Add deploy key":
- Title: `VPS BNIX thanhdat (read-only)`
- Key: paste public key trên
- "Allow write access": **KHÔNG check** (CI chỉ pull).

Test SSH từ VPS:
```bash
ssh root@36.50.26.199
ssh -T github-thanhdat
# Mong đợi: "Hi Duongduongtn/CRMTuyenSinh! You've successfully authenticated, but GitHub does not provide shell access."
```

### 2. Clone code + dựng cấu trúc thư mục

```bash
ssh root@36.50.26.199
mkdir -p /var/www/thanhdat
cd /var/www/thanhdat
git clone git@github-thanhdat:Duongduongtn/CRMTuyenSinh.git .

# Thư mục bind mount cho Docker volume.
mkdir -p backend-media backend-static
mkdir -p frontend-crm/dist
mkdir -p frontend-student/.output/public
chown -R 1000:1000 backend-media backend-static  # khớp UID user `app` trong Dockerfile
```

### 3. Tạo file `.env.prod`

```bash
cd /var/www/thanhdat/infra
cp .env.prod.example .env.prod

# Sinh SECRET_KEY 64 byte random.
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
# Sinh POSTGRES_PASSWORD 32 ký tự an toàn URL.
python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))"

# Edit .env.prod thay 5 giá trị:
#   DJANGO_SECRET_KEY=<value 1>
#   POSTGRES_PASSWORD=<value 2>
#   DATABASE_URL=postgres://crm_thanhdat:<value 2>@db:5432/crm_thanhdat
#   CASSO_WEBHOOK_SECRET=<lấy từ Casso dashboard>
#   ZNS_ACCESS_TOKEN + ZNS_REFRESH_TOKEN + ZNS_TEMPLATE_ID_*=<lấy từ Zalo Business>
#   TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID=<lấy từ @BotFather>
#   FB_APP_SECRET + FB_LEAD_VERIFY_TOKEN=<lấy từ Meta App>
#   EMAIL_HOST/USER/PASSWORD=<SMTP relay, vd Brevo / Sendgrid>
nano .env.prod
chmod 600 .env.prod
```

### 4. Cấp SSL cert qua certbot

```bash
# Cấp cert cho sale.* (HTTP-01 challenge, cần port 80 open + nginx serving):
sudo certbot certonly --webroot -w /var/www/certbot \
  -d sale.trungtamthanhdat.com \
  --email admin@trungtamthanhdat.com --agree-tos --no-eff-email

# Tương tự cho hocvien.* (nếu deploy PWA lên VPS):
sudo certbot certonly --webroot -w /var/www/certbot \
  -d hocvien.trungtamthanhdat.com \
  --email admin@trungtamthanhdat.com --agree-tos --no-eff-email

# Verify auto-renew (certbot timer đã cài sẵn trên Ubuntu).
sudo systemctl status certbot.timer
sudo certbot renew --dry-run
```

### 5. Cài nginx config

```bash
# Symlink config từ repo vào /etc/nginx/sites-enabled.
sudo ln -sf /var/www/thanhdat/infra/nginx/snippets/thanhdat-security-headers.conf \
            /etc/nginx/snippets/thanhdat-security-headers.conf
sudo ln -sf /var/www/thanhdat/infra/nginx/sale.trungtamthanhdat.com.conf \
            /etc/nginx/sites-enabled/sale.trungtamthanhdat.com
sudo ln -sf /var/www/thanhdat/infra/nginx/hocvien.trungtamthanhdat.com.conf \
            /etc/nginx/sites-enabled/hocvien.trungtamthanhdat.com

# Test cú pháp + reload.
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Build + chạy compose lần đầu

> **Lưu ý**: phải truyền `--env-file .env.prod` cho mọi lệnh `docker compose` vì substitution `${POSTGRES_DB}` trong compose file dùng env shell, không phải `env_file:` trong service definition.

```bash
cd /var/www/thanhdat/infra

# Build image backend.
docker compose --env-file .env.prod -f docker-compose.prod.yml build backend

# Up tất cả service.
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d

# Verify.
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f backend
```

> **Tip rút gọn**: tạo alias `dc='docker compose --env-file .env.prod -f docker-compose.prod.yml'` trong `~/.bashrc` để gõ ngắn `dc up -d`, `dc logs -f backend`.

Backend `CMD` trong Dockerfile sẽ tự chạy `migrate --noinput && collectstatic --noinput` trước khi gunicorn start.

### 7. Tạo superuser admin

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend python manage.py createsuperuser
# Sau đó: python manage.py bootstrap_data (tạo 4 Group + 9 Course)
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend python manage.py bootstrap_data
```

### 8. Smoke test cuối

```bash
curl -I https://sale.trungtamthanhdat.com/
curl -I https://sale.trungtamthanhdat.com/api/site-settings/
curl -I https://sale.trungtamthanhdat.com/admin/login/
```

## CI/CD GitHub Actions

### Secrets cần add vào repo

Vào `https://github.com/Duongduongtn/CRMTuyenSinh/settings/secrets/actions` → "New repository secret":

| Tên secret | Giá trị |
|---|---|
| `VPS_HOST` | `36.50.26.199` |
| `VPS_USER` | `root` |
| `VPS_SSH_PRIVATE_KEY` | Toàn bộ nội dung file `~/.ssh/id_vps_production` (private key, định dạng OpenSSH PEM). |
| `TELEGRAM_BOT_TOKEN` | (tùy chọn) Bot token để notify deploy. |
| `TELEGRAM_CHAT_ID` | (tùy chọn) Chat ID nhận thông báo. |

> **Lưu ý bảo mật**: `VPS_SSH_PRIVATE_KEY` là root SSH key — GitHub Actions sẽ có quyền root toàn bộ VPS. Nếu muốn tách quyền, tạo user `thanhdat-deploy` riêng trên VPS, cho `sudo` không password cho 1 vài command, dùng key user đó. Phiên này dùng root cho nhanh; lift quyền sau khi cần.

### Quy trình deploy tự động

Khi push lên `main`:
1. `backend-test` chạy Django tests với Postgres 17 service.
2. `frontend-crm-build` chạy `vue-tsc --noEmit` + `vite build`, upload `dist/` thành artifact.
3. `deploy` (chỉ chạy nếu 2 job trên pass):
   - SSH vào VPS.
   - `git pull` origin main.
   - `docker compose build backend`.
   - `docker compose run --rm backend python manage.py migrate`.
   - `docker compose up -d` (restart services nếu image mới).
   - `docker compose exec backend python manage.py collectstatic`.
   - `rsync` FE dist artifact lên `/var/www/thanhdat/frontend-crm/dist/`.
   - Smoke test HTTPS endpoints.
   - Notify Telegram (nếu cấu hình).

### Trigger thủ công

GitHub UI → Actions tab → "Deploy CRM Tuyen Sinh" → "Run workflow" → chọn branch `main` → Run.

## Rollback

### Khôi phục code

```bash
ssh root@36.50.26.199
cd /var/www/thanhdat
git log --oneline -10            # tìm commit ổn định cuối
git reset --hard <commit-sha>
cd infra
docker compose --env-file .env.prod -f docker-compose.prod.yml build backend
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

### Rollback migration (nếu migration mới gây lỗi)

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend \
  python manage.py migrate <app_name> <previous_migration_number>
```

### Khôi phục DB từ backup

Auto-backup đã có sẵn qua `infra/scripts/pg_backup.sh` + cron daily 2h sáng (xem mục [Backup Postgres](#backup-postgres) bên dưới).

```bash
# Restore từ snapshot cụ thể (sẽ DROP database hiện tại, có prompt xác nhận):
bash /var/www/thanhdat/infra/scripts/pg_restore.sh /var/backups/thanhdat/crm-YYYYMMDD-HHMM.sql.gz

# Restore từ snapshot mới nhất:
bash /var/www/thanhdat/infra/scripts/pg_restore.sh --latest

# Snapshot thủ công trước migration nguy hiểm:
bash /var/www/thanhdat/infra/scripts/pg_backup.sh
```

> Trước khi restore: stop backend + celery để tránh write conflict.
> ```bash
> docker compose --env-file .env.prod -f docker-compose.prod.yml stop backend celery-worker celery-beat
> bash infra/scripts/pg_restore.sh --latest
> docker compose --env-file .env.prod -f docker-compose.prod.yml start backend celery-worker celery-beat
> ```

## Backup Postgres

Script: `infra/scripts/pg_backup.sh` + cron file `infra/cron/thanhdat-pg-backup`.

**Cài đặt lần đầu** (chạy 1 lần khi setup VPS):

```bash
sudo cp /var/www/thanhdat/infra/cron/thanhdat-pg-backup /etc/cron.d/
sudo chmod 644 /etc/cron.d/thanhdat-pg-backup
sudo chown root:root /etc/cron.d/thanhdat-pg-backup
sudo chmod +x /var/www/thanhdat/infra/scripts/pg_backup.sh
sudo chmod +x /var/www/thanhdat/infra/scripts/pg_restore.sh

# Test thủ công lần đầu:
sudo bash /var/www/thanhdat/infra/scripts/pg_backup.sh

# Verify cron đã load (Ubuntu/Debian auto reload mỗi 1 phút):
sudo systemctl status cron
ls -la /var/backups/thanhdat/
tail -20 /var/log/thanhdat-backup.log
```

**Lịch chạy mặc định:**

| Lịch | Lệnh | Mục đích |
|---|---|---|
| `0 2 * * *` daily | `pg_backup.sh` | Dump + gzip, đặt `/var/backups/thanhdat/crm-YYYYMMDD-HHMM.sql.gz`. Rotate giữ 30 ngày. |
| `0 1 * * 0` chủ nhật | `pg_backup.sh --check` | Health check container + write quyền. Không dump. |

**Tuỳ chỉnh qua env** (đặt trong `/etc/default/thanhdat-backup` hoặc export trước khi gọi):

| Env | Mặc định | Ý nghĩa |
|---|---|---|
| `BACKUP_DIR` | `/var/backups/thanhdat` | Thư mục đích. |
| `BACKUP_RETENTION_DAYS` | `30` | Số ngày giữ, file cũ hơn sẽ bị xoá sau mỗi lần backup thành công. |
| `BACKUP_LOG` | `/var/log/thanhdat-backup.log` | File log append-only, soi qua `tail -f`. |
| `BACKUP_S3_BUCKET` | (unset) | Nếu set + có `aws` CLI, sync file lên S3/R2 sau khi dump. Dùng cho phase offsite. |
| `DB_CONTAINER` | `thanhdat-db` | Container Postgres, khớp `docker-compose.prod.yml`. |

**Kiểm tra hằng tuần (manual):**

```bash
# Liệt kê backup hiện có + size:
ls -lh /var/backups/thanhdat/

# Đọc 50 dòng log gần nhất:
tail -50 /var/log/thanhdat-backup.log

# Verify gzip integrity của tất cả file:
for f in /var/backups/thanhdat/crm-*.sql.gz; do gzip -t "$f" && echo "OK: $f" || echo "FAIL: $f"; done

# Test restore vào DB khác để verify (KHÔNG chạy trên prod):
gunzip -c /var/backups/thanhdat/crm-YYYYMMDD-HHMM.sql.gz | head -100
```

**Mở rộng offsite (sau go-live):**

1. Tạo bucket Cloudflare R2 hoặc S3, sinh access key.
2. Cài `aws` CLI trên VPS (`apt install awscli` hoặc dùng MinIO mc).
3. Tạo `/root/.aws/credentials` + `/root/.aws/config` cho user `root` (cron chạy với quyền root).
4. Thêm `BACKUP_S3_BUCKET=thanhdat-backup` vào `/etc/default/thanhdat-backup`.
5. Update cron file để source env:

```cron
0 2 * * * root . /etc/default/thanhdat-backup && /var/www/thanhdat/infra/scripts/pg_backup.sh >/dev/null 2>&1
```

## Logs

| Component | Path |
|---|---|
| nginx access (sale) | `/var/log/nginx/thanhdat-sale.access.log` |
| nginx error (sale) | `/var/log/nginx/thanhdat-sale.error.log` |
| nginx access (hocvien) | `/var/log/nginx/thanhdat-hocvien.access.log` |
| Backend gunicorn | `docker compose logs backend` |
| Celery worker | `docker compose logs celery-worker` |
| Celery beat | `docker compose logs celery-beat` |
| Postgres | `docker compose logs db` |
| Redis | `docker compose logs redis` |

## Renew SSL cert

Certbot timer đã cài sẵn (Ubuntu service). Verify:

```bash
sudo systemctl list-timers | grep certbot
sudo certbot renew --dry-run
```

Nếu cần renew thủ công:

```bash
sudo certbot renew
sudo systemctl reload nginx
```

## Troubleshooting

| Triệu chứng | Nguyên nhân thường gặp | Cách check |
|---|---|---|
| 502 Bad Gateway sale.* | Backend container down hoặc port 8003 không bind. | `docker compose ps`, `ss -tlnp \| grep 8003` |
| 504 Gateway Timeout | Gunicorn nuốt request lâu, timeout 60s. | `docker compose logs backend`, tăng `--timeout` |
| FE trắng trang (404 asset) | rsync chưa chạy, hoặc dist sai path. | `ls /var/www/thanhdat/frontend-crm/dist/` |
| CORS error từ hocvien | `DJANGO_CORS_ORIGINS` thiếu hocvien URL. | check `.env.prod` |
| OTP không gửi (silently fail) | `ZNS_ALLOW_MOCK=False` ở prod nhưng ZNS token chưa cấu hình. | `docker compose logs backend \| grep ZNS` |
| Casso webhook 403 | `CASSO_WEBHOOK_SECRET` sai hoặc thiếu. | check signature middleware |
| Static CSS không cập nhật | nginx cache 30d aggressive, build fingerprint chưa đổi. | check `dist/assets/*.js` hash đã đổi |
| Migration fail trên prod nhưng pass CI | Khác version Postgres giữa CI và prod. | Cả 2 đã ghim Postgres 17 — check log chi tiết |

## Checklist trước go-live

- [ ] Tất cả secrets `.env.prod` đã thay placeholder.
- [ ] Postgres `pg_dump` backup cronjob đã cài (`/etc/cron.d/thanhdat-pg-backup`, retention 30 ngày, log `/var/log/thanhdat-backup.log`).
- [ ] DNS A record đã trỏ đúng.
- [ ] SSL cert đã cấp + nginx reload OK.
- [ ] `python manage.py check --deploy` không có warning critical.
- [ ] Casso webhook URL đã update trong Casso dashboard: `https://sale.trungtamthanhdat.com/api/payments/casso-webhook/`.
- [ ] FB Lead Ads webhook URL update trong Meta: `https://sale.trungtamthanhdat.com/api/marketing/fb-lead-webhook/`.
- [ ] Zalo OA app đã verify domain `sale.trungtamthanhdat.com`.
- [ ] Sentry DSN (nếu có) đã add vào `.env.prod`.
- [ ] Uptime monitor (UptimeRobot / Better Stack) đã ping 5p/lần.
- [ ] Smoke test: capture lead → sale chốt → HV cọc → upload → văn thư duyệt → in PDF (acceptance Sprint 3 Tuần 7 ngày 3).
