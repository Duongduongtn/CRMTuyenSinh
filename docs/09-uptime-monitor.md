# UptimeRobot — giám sát 3 subdomain

> Mục đích: alert email khi 1 trong 3 subdomain CRM tuyển sinh xuống (apex, sale, hocvien).
> Free tier UptimeRobot cho phép 50 monitor + 5 phút polling. Đủ cho dự án.

## 1. Cấu hình 3 monitor

Truy cập `https://uptimerobot.com/dashboard` → New monitor cho từng entry.

### Monitor 1 — Apex (FE public landing)

| Trường | Giá trị |
|---|---|
| Monitor Type | `HTTP(s)` |
| Friendly Name | `Apex trungtamthanhdat.com` |
| URL | `https://trungtamthanhdat.com/` |
| Monitoring Interval | `5 minutes` (free max) |
| Monitor Timeout | `30 seconds` |
| Keyword Type | (để trống — kiểm 200 status đủ) |
| HTTP Method | `HEAD` (giảm bandwidth) |
| Alert Contacts | tick email đã add ở §3 |

> Nếu muốn keyword check sâu hơn: chọn `HTTP(s)` Type, `Keyword Type = exists`, `Keyword = trungtamthanhdat`. Bắt được case server trả 200 nhưng nội dung sai (vd vhost conflict trả VNT Media như commit V đã gặp).

### Monitor 2 — Sale CRM (Vue SPA)

| Trường | Giá trị |
|---|---|
| Friendly Name | `Sale CRM (Vue SPA)` |
| URL | `https://sale.trungtamthanhdat.com/api/site-settings` |
| Monitoring Interval | `5 minutes` |
| Monitor Timeout | `30 seconds` |
| HTTP Method | `GET` |
| Keyword Type | `exists` |
| Keyword | `brand_name` |

> Lý do gọi `/api/site-settings` thay vì `/`: API endpoint nhẹ, trả JSON có field `brand_name`, verify cả BE Django + DB còn sống. Tránh false-positive khi FE bundle hỏng nhưng BE OK.

### Monitor 3 — PWA học viên (hocvien)

| Trường | Giá trị |
|---|---|
| Friendly Name | `PWA hocvien` |
| URL | `https://hocvien.trungtamthanhdat.com/` |
| Monitoring Interval | `5 minutes` |
| Monitor Timeout | `30 seconds` |
| HTTP Method | `GET` |
| Keyword Type | `exists` |
| Keyword | `Học viên` |

> PWA Nuxt SPA static, response chứa `<title>Học viên</title>`. Keyword check bắt được case nginx trả 200 nhưng `.output/public/` rỗng (rsync fail).

## 2. Alert contact

`My Settings` → `Alert Contacts` → `Add Alert Contact`.

| Trường | Giá trị |
|---|---|
| Alert Contact Type | `E-mail` |
| Friendly Name | `Admin email` |
| Send To | email quản trị của trung tâm |
| Verify | check inbox + click verify link |

Sau khi verify, vào từng monitor → tick alert contact vừa add.

## 3. Threshold thông báo (khuyến nghị)

`Settings` của mỗi monitor:
- `When down for at least` → `2 lần fail liên tiếp` (= 10 phút). Tránh alert spam khi timeout tạm.
- `Notification frequency` → `Send notification when status changes` (chỉ alert lúc đổi trạng thái, không lặp).

## 4. Verify

Sau khi tạo, đợi 5-10 phút cho lần check đầu. Status từng monitor phải hiện màu xanh `up`. Nếu vàng/đỏ:
- `Up` → OK, polling đều.
- `Seems down` → 1 lần fail tạm.
- `Down` → fail liên tiếp, đã gửi mail.

Smoke nhân tạo: ssh vào VPS, `docker compose -f infra/docker-compose.prod.yml stop backend` → đợi 10-15 phút → kiểm email + nhận alert → `start backend` → kiểm khôi phục.

## 5. Cấu hình status page (optional)

`Public Status Pages` → `Add new` → chọn 3 monitor → URL `status-trungtamthanhdat.uptimerobot.com` hoặc custom domain. Có thể nhúng vào FE public sau này.

## 6. Mở rộng tương lai

- Thêm monitor `https://sale.trungtamthanhdat.com/api/admin/integrations/` (expect 403, free tier không hỗ trợ "expect status code", phải nâng Pro hoặc bỏ).
- SSL expiry monitor (tự động cảnh báo cert hết hạn 14 ngày trước): UptimeRobot Pro hoặc dùng `ssl-checker.io` cron riêng.
- Response time threshold alert: Pro tier.
