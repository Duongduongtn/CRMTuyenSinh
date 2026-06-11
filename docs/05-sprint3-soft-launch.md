# Sprint 3 Tuần 7 — Soft Launch Checklist

> Tham chiếu: `infra/README.md` (setup), `03-phase1-plan.md` §Tuần 7 (acceptance).
> Trạng thái phiên này: bước 1-8 setup VPS xong, smoke test pass. Còn 4 nhóm key prod chưa fill — tài liệu này hướng dẫn user fill xong + smoke test E2E + go-live.

---

## 0. Trạng thái hiện tại (đã xong trong phiên 2026-06-11)

- ✅ VPS BNIX `36.50.26.199` clone repo về `/var/www/thanhdat/`.
- ✅ Deploy key `github-thanhdat` đã add Read-only vào GitHub repo.
- ✅ 3 GH Actions secret bắt buộc: `VPS_HOST`, `VPS_USER`, `VPS_SSH_PRIVATE_KEY`.
- ✅ SSL Let's Encrypt cấp cho `sale.trungtamthanhdat.com` + `hocvien.trungtamthanhdat.com` (hết hạn 2026-09-09, auto-renew certbot timer).
- ✅ nginx config symlink + reload sạch (5 site khác không bị ảnh hưởng).
- ✅ Docker compose 5 service healthy: `thanhdat-db` (PG17), `thanhdat-redis`, `thanhdat-backend` (gunicorn 0.0.0.0:8000 → 127.0.0.1:8003), `thanhdat-celery-worker`, `thanhdat-celery-beat`.
- ✅ DB migrate xong 17 migration, collectstatic 188 file, bootstrap_data tạo 4 Group + 9 Course + 5 DocumentType + SiteSettings singleton.
- ✅ Superuser `admin` credentials lưu tại `/root/thanhdat-admin-credentials.txt` (chmod 600).
- ✅ pg_backup cron `/etc/cron.d/thanhdat-pg-backup`: daily 2h, retention 30 ngày.
- ✅ Smoke test HTTPS pass: `/admin/login/` 200, `/api/site-settings` 200 (brand "Trung tâm Đào tạo Lái xe"), `/api/public/courses/` 200 (9 course đầy đủ A1/A/B1/B-AT/B-MT/C1/C/D1/D2).
- ⏳ FE `/` 403 (dist rỗng) — sẽ pass khi CI/CD rsync `frontend-crm/dist/` lên VPS sau push.

## 1. Lấy 4 nhóm key prod

### 1.1 Casso (đối soát QR thanh toán)

1. Đăng nhập [my.casso.vn](https://my.casso.vn) → menu **Tích hợp** → **Webhook**.
2. **Add Webhook URL:** `https://sale.trungtamthanhdat.com/api/payments/casso-webhook/`.
3. Casso sinh `Secret` → copy. **Đây là `CASSO_WEBHOOK_SECRET`**.
4. **API Key** (nếu dùng API gọi check): menu **API Token** → copy. **Đây là `CASSO_API_KEY`**.

### 1.2 Zalo ZNS (OTP học viên)

> ZNS = Zalo Notification Service. OTP gửi qua app Zalo, không phải SMS thường.

1. Đăng nhập [oa.zalo.me](https://oa.zalo.me/manage) → chọn OA của trung tâm.
2. **Tích hợp ZNS:** menu **ZNS** → **Cài đặt** → bật ZNS API.
3. Lấy **Access Token** + **Refresh Token** (token có TTL 7 ngày, refresh dùng kéo dài). → `ZNS_ACCESS_TOKEN`, `ZNS_REFRESH_TOKEN`.
4. **Tạo 2 template ZNS:**
   - Template OTP (6 chữ số xác minh): variable `{otp}`, `{minutes}`. → ID dán vào `ZNS_TEMPLATE_ID_OTP`.
   - Template thông báo đặt cọc thành công: variable `{full_name}`, `{course}`, `{amount}`, `{order_code}`. → ID dán vào `ZNS_TEMPLATE_ID_DEPOSIT`.
5. Submit template chờ Zalo duyệt 1-3 ngày làm việc.

### 1.3 Facebook Lead Ads

> Cần Meta Business App có quyền Lead Retrieval.

1. Tạo Meta App tại [developers.facebook.com](https://developers.facebook.com/apps/) → loại **Business**.
2. Add product **Webhooks** → object `page` → field `leadgen`.
3. **Callback URL:** `https://sale.trungtamthanhdat.com/api/marketing/fb-lead-webhook/`.
4. **Verify Token:** tự đặt chuỗi random 32 ký tự → `FB_LEAD_VERIFY_TOKEN`. Paste vào Meta UI, Meta gọi GET để verify.
5. **App Secret:** menu **Cài đặt → Cơ bản** → "Hiển thị" → copy → `FB_APP_SECRET`. (Dùng verify HMAC signature mỗi webhook event.)

### 1.4 SMTP (email nội bộ)

> Dùng Brevo (sendinblue) free 300 email/ngày, hoặc Sendgrid/Mailgun.

1. Đăng ký [brevo.com](https://www.brevo.com) free → menu **SMTP & API**.
2. Tạo SMTP key:
   - `EMAIL_HOST=smtp-relay.brevo.com`
   - `EMAIL_PORT=587`
   - `EMAIL_USE_TLS=True`
   - `EMAIL_HOST_USER=<smtp-user-id>` (số ID)
   - `EMAIL_HOST_PASSWORD=<smtp-key>` (key dài 64 ký tự)

## 2. Paste key vào `.env.prod` trên VPS

> KHÔNG paste key qua chat/email/Slack. SSH thẳng vào VPS, paste qua `nano`.

```bash
ssh root@36.50.26.199
cd /var/www/thanhdat/infra
nano .env.prod
# Sửa 13 dòng sau (giữ nguyên tên field, paste value):
#   CASSO_WEBHOOK_SECRET=...
#   CASSO_API_KEY=...
#   ZNS_ACCESS_TOKEN=...
#   ZNS_REFRESH_TOKEN=...
#   ZNS_TEMPLATE_ID_OTP=...
#   ZNS_TEMPLATE_ID_DEPOSIT=...
#   FB_APP_SECRET=...
#   FB_LEAD_VERIFY_TOKEN=...
#   EMAIL_HOST=smtp-relay.brevo.com
#   EMAIL_HOST_USER=...
#   EMAIL_HOST_PASSWORD=...
# Ctrl+O save, Ctrl+X exit.

# Restart 3 service đọc .env (không cần rebuild image vì code không đổi).
docker compose --env-file .env.prod -f docker-compose.prod.yml restart backend celery-worker celery-beat

# Verify ZNS init OK (sẽ log lỗi nếu token sai).
docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=30 backend | grep -iE "zns|casso|fb_|smtp"
```

## 3. Add 2 GH Secrets tùy chọn (Telegram)

> Telegram bot notify CI/CD pass/fail. Bỏ qua nếu user không cần — workflow đã xử lý gracefully.

1. Tạo bot: chat với [@BotFather](https://t.me/BotFather) → `/newbot` → đặt tên → lấy token.
2. Tạo group Telegram → add bot vào → gửi 1 tin nhắn bất kỳ.
3. Lấy chat ID:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   → tìm `"chat":{"id":-12345...}` (số âm = group).
4. GitHub repo → Settings → Secrets → Actions → add:
   - `TELEGRAM_BOT_TOKEN` = token bot
   - `TELEGRAM_CHAT_ID` = chat ID (kể cả dấu `-`)

## 4. Sentry observability (tùy chọn, sau go-live)

> SDK đã wire ở commit `3a4aa46`, DSN trống = no-op. Bật khi muốn.

1. Đăng ký [sentry.io](https://sentry.io) free (5K events/tháng).
2. Tạo organization → tạo 2 project:
   - Project 1: platform **Django** → copy DSN.
   - Project 2: platform **Vue** → copy DSN.
3. SSH VPS, edit `.env.prod`:
   ```
   SENTRY_DSN=<DSN Django>
   ```
4. Edit GH Actions `.github/workflows/deploy.yml` job `frontend-crm-build` step "Build" thêm env:
   ```yaml
   env:
     VITE_API_BASE: https://sale.trungtamthanhdat.com
     VITE_SENTRY_DSN: <DSN Vue>
   ```
   Hoặc tốt hơn: add GH Secret `VITE_SENTRY_DSN` rồi reference `${{ secrets.VITE_SENTRY_DSN }}`.
5. Restart backend:
   ```bash
   docker compose --env-file .env.prod -f docker-compose.prod.yml restart backend celery-worker celery-beat
   ```
6. Smoke test BE:
   ```bash
   docker compose --env-file .env.prod -f docker-compose.prod.yml exec backend \
     python -c "import sentry_sdk; sentry_sdk.capture_message('Smoke test BE go-live')"
   ```
   Vào Sentry UI → Issues → thấy "Smoke test BE go-live" trong <60s.

## 5. Smoke test E2E flow 5 step (chạy sau khi paste key prod)

> Test thật trên domain prod. Cần 1 SĐT Zalo thật để nhận OTP + 1 số tài khoản ngân hàng dummy để test chuyển khoản (chuyển 10.000đ test rồi rút lại).

### Step 1: Capture lead qua FE public

```bash
# Mở https://trungtamthanhdat.com (Cloudflare Pages, FE Nuxt).
# Bấm nút "Đăng ký tư vấn" → fill form: tên, SĐT thật, chọn hạng B.
# Submit → expect: thông báo "Đã nhận thông tin, tư vấn sẽ liên hệ trong 15 phút".
# Verify backend nhận lead:
curl -sS https://sale.trungtamthanhdat.com/api/leads/ \
  -H "Authorization: Bearer <admin token>" \
  | head -c 500
# Hoặc vào https://sale.trungtamthanhdat.com/admin/leads/lead/ → thấy lead mới.
```

### Step 2: Sale chốt đơn → tạo Order + QR cọc

```bash
# Đăng nhập CRM SPA: https://sale.trungtamthanhdat.com/login
# Username: admin (hoặc account sale).
# Vào tab "Lead" → chọn lead vừa tạo → "Chốt đơn" → chọn course B-MT → "Tạo đơn".
# Expect: order_code "TD20260611NNNN" + QR code VietQR hiện.
# Verify URL QR mở được:
QR_URL=$(curl -sS "https://sale.trungtamthanhdat.com/api/orders/<order-id>/" \
  -H "Authorization: Bearer <admin token>" | jq -r .qr_url)
echo "QR: $QR_URL"
curl -sS -I "$QR_URL"  # expect 200, content-type image/png
```

### Step 3: Học viên chuyển cọc qua QR → Casso webhook xác nhận

```bash
# Quét QR bằng app banking → chuyển 200.000đ (mức cọc thấp nhất).
# Chờ 1-2 phút, Casso gửi webhook đến /api/payments/casso-webhook/.
# Verify backend log:
ssh vps 'cd /var/www/thanhdat/infra && docker compose --env-file .env.prod -f docker-compose.prod.yml logs --tail=50 backend | grep -i casso'
# Expect: "Casso webhook hợp lệ", "Order TD... đã xác nhận đặt cọc".
# Verify status order:
curl -sS "https://sale.trungtamthanhdat.com/api/orders/<order-id>/" \
  -H "Authorization: Bearer <admin token>" | jq .status
# Expect: "deposited"
```

### Step 4: Học viên login PWA + upload CCCD + văn thư duyệt

```bash
# Mở https://hocvien.trungtamthanhdat.com.
# Nhập SĐT đã đăng ký → bấm "Gửi OTP".
# Verify ZNS gửi OTP qua Zalo app (15-30s).
# Nhập OTP → vào trang Hồ sơ.
# Upload 2 ảnh: CCCD mặt trước + mặt sau (<5MB mỗi ảnh).
# Verify upload OK:
curl -sS "https://sale.trungtamthanhdat.com/api/documents/?enrollment=<id>" \
  -H "Authorization: Bearer <admin token>" | jq .

# Văn thư đăng nhập CRM → tab "Hồ sơ chờ duyệt" → chọn hồ sơ → bấm "Duyệt".
# Expect: status "approved", học viên nhận push notification PWA.
```

### Step 5: In PDF đơn đăng ký

```bash
# Sau khi văn thư duyệt, vào order detail → bấm "In đơn đăng ký Sở GTVT".
# Expect: PDF tải xuống, tên file "don-dang-ky-<order-code>.pdf".
# Verify nội dung PDF:
# - Họ tên + ngày sinh + CCCD học viên đúng.
# - Tiếng Việt có dấu (font Noto Sans).
# - Logo trung tâm + chữ ký số (nếu có).
# - Số đăng ký + ngày tạo đúng.
```

## 6. Khi 5 step E2E pass → soft launch 5 lead thật

1. Bật quảng cáo FB ads với budget 100k/ngày, target Bình Phước.
2. Đợi 5 lead đầu tiên (1-3 ngày).
3. Quy trình tracking:
   - Mỗi lead vào → 1 sale chốt → 1 học viên cọc → 1 hồ sơ → 1 PDF.
   - Ghi log: thời gian phản hồi tư vấn, tỉ lệ convert, lỗi gặp phải.
4. Sau 5 lead pass → mở rộng budget → 1 chiến dịch ads thật (mục tiêu Sprint 3 acceptance).

## 7. Monitoring sau go-live

### UptimeRobot (free 50 monitor, ping 5p/lần)

1. Đăng ký [uptimerobot.com](https://uptimerobot.com).
2. Add 3 monitor HTTPS:
   - `https://sale.trungtamthanhdat.com/api/site-settings` (BE health)
   - `https://hocvien.trungtamthanhdat.com/` (PWA)
   - `https://trungtamthanhdat.com/` (FE public Cloudflare Pages)
3. Alert contact: email + Telegram (xem mục 3 thêm bot).
4. Threshold: HTTP code !=200 trong 2 lần check liên tiếp → alert.

### Log review hằng ngày (5 phút)

```bash
ssh vps
# Backend error 500:
docker logs thanhdat-backend 2>&1 | grep -E "ERROR|500" | tail -30
# Celery task fail:
docker logs thanhdat-celery-worker 2>&1 | grep -iE "fail|error" | tail -30
# Nginx 5xx:
tail -100 /var/log/nginx/thanhdat-sale.error.log
# Auth failure (brute force?):
grep "Forbidden\|401" /var/log/nginx/thanhdat-sale.access.log | tail -20
```

### Backup verify hằng tuần (2 phút)

```bash
ssh vps
ls -lh /var/backups/thanhdat/ | tail -10
# Verify gzip integrity:
for f in /var/backups/thanhdat/crm-*.sql.gz; do gzip -t "$f" && echo "OK: $(basename $f)"; done
# Tải 1 backup về local mỗi tuần (offsite manual):
scp vps:/var/backups/thanhdat/crm-$(date +%Y%m%d)-*.sql.gz ~/Backups/thanhdat/
```

## 8. Rollback emergency

Nếu phát hiện lỗi nghiêm trọng (data corrupt, security incident, SSL fail):

```bash
ssh vps
cd /var/www/thanhdat
# 1. Rollback code về commit ổn định cuối:
git log --oneline -10
git reset --hard <sha-on-dinh>
# 2. Rebuild backend image:
cd infra
docker compose --env-file .env.prod -f docker-compose.prod.yml build backend
# 3. Restart:
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
# 4. Nếu DB corrupt → restore backup:
docker compose --env-file .env.prod -f docker-compose.prod.yml stop backend celery-worker celery-beat
bash /var/www/thanhdat/infra/scripts/pg_restore.sh --latest
docker compose --env-file .env.prod -f docker-compose.prod.yml start backend celery-worker celery-beat
```

## 9. Definition of Done — Sprint 3 Tuần 7

- [ ] 4 nhóm key prod paste vào `.env.prod`, restart container, log không có ERROR.
- [ ] Smoke test E2E 5 step pass với 1 lead test thật.
- [ ] FE CRM SPA build + rsync lên VPS qua CI/CD (`/` trả 200, không 403).
- [ ] PWA học viên build + deploy lên `hocvien.*` (`/` trả 200).
- [ ] UptimeRobot ping 3 monitor xanh trong 24h.
- [ ] pg_backup cron chạy đúng 2h sáng (verify log ngày 1).
- [ ] Đổi password superuser `admin` sau login lần đầu.
- [ ] Xoá file `/root/thanhdat-admin-credentials.txt` sau khi user nhớ password.
- [ ] 5 lead thật từ FB Lead Ads vào CRM, conversion → enrollment → paid ít nhất 1 case.
- [ ] Sentry events nhận được trong 24h đầu (nếu bật).
