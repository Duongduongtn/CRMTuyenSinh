# UI quản lý integration credentials (Casso + FB Lead Ads)

> Tham chiếu: `backend/apps/core/models.py:IntegrationCredential`, `backend/apps/core/crypto.py`, `backend/apps/core/integrations.py`, `backend/apps/core/views.py`.
> Mục đích: thay flow SSH `nano .env.prod` bằng form CRM SPA `/admin/integrations`. Vận hành (không phải dev) tự paste key vào UI, BE encrypt Fernet lưu DB, runtime đọc qua loader có cache 60s.

## Scope chốt 2026-06-11 (Sprint 3 Tuần 7)

User chốt **bỏ ZNS Zalo + SMTP khỏi MVP**:
- ZNS Zalo: auth học viên chuyển sang SĐT + 6 số cuối CCCD (xem memory `student-auth-flow`). Code ZNS adapter / OTP / quick-view task sẽ bị xóa ở gói B (phiên sau).
- SMTP: admin tự reset password trong CRM SPA, không gửi email. `EMAIL_BACKEND` ở prod đã đổi default sang `dummy` (`send_mail` no-op).

`Provider.ZNS` + `Provider.SMTP` trong model GIỮ trong choices (deprecated) để code app cũ chưa refactor không crash. UI chỉ hiện Casso + FB.

---

## 1. Tổng quan

```
User CRM SPA → PUT /api/admin/integrations/casso/ {webhook_secret: "...", api_key: "..."}
            → view encrypt Fernet → IntegrationCredential.value_encrypted (binary)
            → audit log (CHỈ tên key, KHÔNG plaintext)
            → invalidate cache

Backend service (webhook Casso, FB Lead Ads webhook) gọi:
  get_credential("casso", "webhook_secret")
            → cache 60s → DB IntegrationCredential → settings.<NAME> (ENV) → ""
```

2 nhóm provider + key active (xem `apps/core/integrations.py:INTEGRATION_SCHEMA`):

| Provider | Key | Sensitive | Ghi chú |
|---|---|---|---|
| casso | webhook_secret | có | Verify HMAC từ Casso webhook |
| casso | api_key | có | Gọi Casso API check giao dịch |
| fb | app_secret | có | Verify HMAC FB webhook |
| fb | lead_verify_token | có | FB GET verify lúc setup |

> **FB Lead Ads**: defer — giữ UI tab để paste key khi nào user thật sự chạy quảng cáo Facebook. Code FB webhook handler chưa cần wire-up cho MVP launch.

## 2. Bootstrap FERNET_SECRET (chạy 1 LẦN trên VPS)

### 2.1 Sinh key

```bash
ssh root@36.50.26.199
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend \
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Output ví dụ: dWxoTGZIYWxWZWVZdjk2dGJlSk4xQUJDREVGR0hJSktMTU5PUFE=
```

### 2.2 Backup key vào nơi an toàn

**QUAN TRỌNG**: Mất key này = **không decrypt được** bất kỳ credential nào trong DB. Phải:
- Lưu vào password manager (1Password / Bitwarden / KeePass).
- Lưu 1 bản giấy in offline cất tủ.
- Chia sẻ cho người chịu trách nhiệm bằng kênh secure (Signal / 1Password Share, KHÔNG email/Telegram).

### 2.3 Paste vào `.env.prod` + restart

```bash
ssh root@36.50.26.199
cd /var/www/thanhdat/infra
nano .env.prod
# Sửa dòng:
#   FERNET_SECRET=dWxoTGZIYWxWZWVZdjk2dGJlSk4xQUJDREVGR0hJSktMTU5PUFE=
# (giữ FERNET_SECRET_OLD= rỗng, chỉ dùng khi rotate)

docker compose --env-file .env.prod -f docker-compose.prod.yml restart backend celery-worker celery-beat
```

### 2.4 Verify load OK

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend \
  python manage.py shell -c "from apps.core.crypto import get_cipher; print(type(get_cipher()).__name__)"
# Output: Fernet (hoặc MultiFernet nếu có FERNET_SECRET_OLD)
```

Nếu raise `ImproperlyConfigured: FERNET_SECRET chưa được cấu hình`:
- Check ENV `.env.prod` đã save chưa: `grep FERNET .env.prod`.
- Container đã restart: `docker compose ... restart backend`.

## 3. Login CRM SPA paste key

1. Mở `https://sale.trungtamthanhdat.com/admin/integrations` (SPA Vue 3 + Vite, taste-skill).
2. Login bằng superuser (admin).
3. Tab Casso → paste `webhook_secret` + `api_key` → Save.
4. Tab Facebook → paste `app_secret` + `lead_verify_token` → Save (khi nào chạy FB Ads).

Sau Save: backend đọc credential mới sau tối đa **60s** (cache TTL). KHÔNG cần restart container.

> **Django admin fallback** `/admin/core/integrationcredential/` chỉ READ-ONLY: superuser xem được masked + audit timeline, KHÔNG add/edit/delete được (chặn cứng `has_add_permission = has_delete_permission = False`). Mọi tạo/xóa phải qua API có AuditLog.

## 4. Test bằng cURL (debug)

### 4.1 GET list (xem có gì + masked)

```bash
# Lấy session cookie từ admin login trước. Đơn giản nhất: dùng browser DevTools.
curl -sS https://sale.trungtamthanhdat.com/api/admin/integrations/ \
  -H "Cookie: sessionid=<cookie từ browser>; csrftoken=<csrf>" \
  | jq .
```

Output:
```json
{
  "casso": [
    {
      "key": "webhook_secret",
      "label": "Webhook Secret",
      "sensitive": true,
      "help_text": "Lấy từ my.casso.vn → ...",
      "masked": "****abcd",
      "has_value": true,
      "source": "db",
      "updated_at": "2026-06-11T14:25:00+0700",
      "updated_by_username": "admin"
    },
    ...
  ],
  "fb": [...]
}
```

### 4.2 PUT update

```bash
curl -sS -X PUT https://sale.trungtamthanhdat.com/api/admin/integrations/casso/ \
  -H "Cookie: ..." -H "X-CSRFToken: ..." \
  -H "Content-Type: application/json" \
  -d '{"webhook_secret": "secret-moi", "api_key": "api-moi"}'
```

## 5. Rotation FERNET_SECRET

Khi nghi ngờ key lộ hoặc rotate định kỳ:

```bash
# 1. Sinh key mới.
NEW_KEY=$(docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T backend \
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "Key mới: $NEW_KEY"

# 2. Edit .env.prod:
#   FERNET_SECRET_OLD=<KEY_CŨ>      # CHUYỂN KEY CŨ qua đây
#   FERNET_SECRET=<KEY_MỚI>          # KEY MỚI thay chỗ cũ

ssh root@36.50.26.199
nano /var/www/thanhdat/infra/.env.prod

# 3. Restart - MultiFernet([new, old]) sẽ decrypt được data cũ + encrypt mới bằng new.
docker compose --env-file .env.prod -f docker-compose.prod.yml restart backend celery-worker celery-beat

# 4. Re-encrypt toàn bộ credential sang new key (Python script):
docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend python manage.py shell -c "
from apps.core.models import IntegrationCredential
from apps.core.integrations import invalidate
n = 0
for c in IntegrationCredential.objects.all():
    val = c.get_value()
    if val:
        c.set_value(val)  # encrypt lại bằng primary key (new)
        c.save(update_fields=['value_encrypted'])
        invalidate(c.provider, c.key)
        n += 1
print(f'Re-encrypted {n} credential')
"

# 5. Xác nhận đọc OK: gọi GET /api/admin/integrations/, có data.

# 6. Gỡ FERNET_SECRET_OLD khỏi .env.prod + restart.
#    Lúc này chỉ còn 1 key — key cũ vô hiệu hoá hoàn toàn.
```

## 6. Disaster recovery

### 6.1 Mất key + chưa backup

KHÔNG decrypt được DB cũ. Phương án:
- Reset toàn bộ credential: `IntegrationCredential.objects.all().delete()`.
- Lấy lại key từ provider (Casso/Zalo/FB/Brevo).
- Paste lại qua UI bằng key mới.

### 6.2 DB lỗi, restore từ backup

`pg_backup` cron daily đã có (`infra/scripts/pg_backup.sh`). Restore xong, credential vẫn dùng key Fernet hiện tại — chỉ cần đảm bảo FERNET_SECRET không bị thay đổi giữa backup time và restore time.

Nếu giữa lúc backup và lúc restore mà key Fernet ĐÃ rotate (bỏ FERNET_SECRET_OLD), thì:
- Tạm thời paste lại FERNET_SECRET_OLD từ password manager backup.
- Restore DB.
- Re-encrypt + gỡ OLD như section 5.

## 7. Audit + giám sát

Mọi PUT `/api/admin/integrations/{provider}/` tạo 1 `AuditLog`:
- `action=update`
- `target_model=IntegrationCredential`
- `target_id=<provider>`
- `changes={"keys_changed": ["webhook_secret"], "keys_cleared": []}` — **KHÔNG có plaintext**.
- `user`, `ip_address`, `user_agent` đầy đủ.

Query: `AuditLog.objects.filter(target_model="IntegrationCredential").order_by("-created_at")`.

Xem qua Django admin: `/admin/core/auditlog/`.

## 8. Definition of Done

- [x] Model `IntegrationCredential` + migration `0005`.
- [x] `apps/core/crypto.py` Fernet wrapper + MultiFernet rotation.
- [x] `apps/core/integrations.py` loader cache 60s + fallback ENV.
- [x] Refactor call site Casso webhook + FB webhook dùng loader (ZNS adapter còn legacy, gói B sẽ xóa).
- [x] API `GET /api/admin/integrations/` + `PUT /api/admin/integrations/{provider}/` superuser only.
- [x] Audit log mỗi PUT (CHỈ tên key, KHÔNG plaintext).
- [x] Unit test crypto + loader + API permission + masking + idempotent.
- [x] Doc bootstrap + rotation + disaster recovery.
- [ ] **SPA tab `/admin/integrations`** — phiên này (Vue 3 + shadcn-vue, taste-skill, 2 tab Casso + FB).
- [ ] **Test connection button** Casso (ping `casso.vn/v2/userInfo`) + FB (`graph.facebook.com/debug_token`) — phiên này.
- ~~SMTP runtime wire~~ — bỏ scope (user chốt bỏ SMTP).
- ~~ZNS adapter refactor~~ — bỏ scope (user chốt bỏ ZNS, gói B sẽ xóa code legacy).
