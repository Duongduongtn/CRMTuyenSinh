# Deploy FE public lên VPS BNIX (thay Cloudflare Pages)

> Tham chiếu: `frontend-public/nuxt.config.ts`, `infra/docker-compose.prod.yml`, `infra/nginx/trungtamthanhdat.com.conf`, `.github/workflows/deploy.yml`.
> Quyết định kiến trúc: docs/06 đề xuất Cloudflare Pages nhưng yêu cầu đổi NS Cloudflare + click OAuth dashboard. Domain `trungtamthanhdat.com` apex A đã trỏ thẳng VPS BNIX `36.50.26.199` từ trước, NS còn ở parking. Để soft launch sớm, deploy lên chính VPS cùng `sale.*` và `hocvien.*`. Migrate sang CF Pages sau nếu lưu lượng cần CDN global.

---

## 1. Kiến trúc

- **Build**: Nuxt 3 hybrid (`nitro.preset: 'node-server'`). CI sinh `.output/server/index.mjs` + `.output/public/` (route prerender).
- **Runtime**: docker service `frontend-public-ssr` (node:20-alpine) mount `.output` read-only, spawn `node server/index.mjs` listen `0.0.0.0:3000` trong container → bind `127.0.0.1:3104` ngoài host.
- **Nginx**: vhost apex `trungtamthanhdat.com.conf` proxy_pass `http://127.0.0.1:3104` cho mọi route. `/_nuxt/` có cache header 30 ngày.
- **CI**: workflow `deploy.yml` job `frontend-public-build` build + upload artifact, deploy job rsync vào `/var/www/thanhdat/frontend-public/.output/` rồi `docker compose restart frontend-public-ssr`.

```
visitor → nginx host (443) → 127.0.0.1:3104 (docker host port)
                          → thanhdat-frontend-public-ssr:3000 (container)
                          → node server/index.mjs (Nitro hybrid)
                          → serve static .output/public/* hoặc SSR render
```

## 2. Bootstrap lần đầu (chạy MỘT LẦN trên VPS, sau đó CI tự lo)

Pre-requisite:
- DNS A record `trungtamthanhdat.com` → `36.50.26.199` (đã có).
- DNS A record `www.trungtamthanhdat.com` → `36.50.26.199` (cần thêm tại panel registrar nếu chưa có).
- Verify: `dig +short trungtamthanhdat.com @1.1.1.1` → trả `36.50.26.199`.

### 2.1 Cấp SSL Let's Encrypt cho apex + www

Dùng webroot mode để không cần touching nginx HTTPS block khi cert chưa có.

```bash
ssh root@36.50.26.199

# Tạo vhost HTTP-only tạm để pass ACME challenge.
cat > /etc/nginx/sites-available/trungtamthanhdat.com.bootstrap <<'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name trungtamthanhdat.com www.trungtamthanhdat.com;
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    location / {
        return 404;
    }
}
EOF

mkdir -p /var/www/certbot
ln -sf /etc/nginx/sites-available/trungtamthanhdat.com.bootstrap \
       /etc/nginx/sites-enabled/trungtamthanhdat.com.bootstrap
nginx -t && systemctl reload nginx

# Cấp cert (1 cert cho 2 domain).
certbot certonly --webroot -w /var/www/certbot \
  -d trungtamthanhdat.com -d www.trungtamthanhdat.com \
  --email admin@trungtamthanhdat.com --agree-tos --no-eff-email

# Verify cert.
ls -lh /etc/letsencrypt/live/trungtamthanhdat.com/
# fullchain.pem + privkey.pem phải có.

# Gỡ vhost bootstrap, swap sang vhost full SSL.
rm /etc/nginx/sites-enabled/trungtamthanhdat.com.bootstrap
ln -sf /var/www/thanhdat/infra/nginx/trungtamthanhdat.com.conf \
       /etc/nginx/sites-enabled/trungtamthanhdat.com
nginx -t && systemctl reload nginx
```

### 2.2 Khởi tạo docker service + folder mount

```bash
ssh root@36.50.26.199
mkdir -p /var/www/thanhdat/frontend-public/.output
cd /var/www/thanhdat/infra

# Lần đầu service chưa có artifact -> Node fail start. Đợi CI rsync xong rồi
# restart. Trước đó verify compose file đọc service mới:
docker compose --env-file .env.prod -f docker-compose.prod.yml config | grep -A 5 frontend-public-ssr
```

### 2.3 Trigger CI build + deploy

```bash
# Trên máy dev:
cd D:/Du_An/CRMTuyensinh
git push origin main
```

CI sẽ:
1. Build FE public (~2 phút).
2. Rsync `.output/` lên VPS.
3. SSH VPS chạy `docker compose up -d frontend-public-ssr` (lần đầu tạo container) + `restart` (reload code).
4. Smoke test apex 200.

## 3. Verify sau bootstrap

```bash
# Apex 200.
curl -sS -o /dev/null -w "apex: %{http_code}\n" -m 10 https://trungtamthanhdat.com/

# www -> apex 301.
curl -sS -o /dev/null -w "www: %{http_code} -> %{redirect_url}\n" -m 10 https://www.trungtamthanhdat.com/

# Khóa học prerender.
curl -sS -o /dev/null -w "khoa-hoc: %{http_code}\n" -m 10 https://trungtamthanhdat.com/khoa-hoc

# SSR /dh dummy (token sai -> 404, không 500).
curl -sS -o /dev/null -w "dh dummy: %{http_code}\n" -m 10 https://trungtamthanhdat.com/dh/abc123

# Sitemap + robots.
curl -sS -o /dev/null -w "sitemap: %{http_code}\n" -m 10 https://trungtamthanhdat.com/sitemap.xml
curl -sS -o /dev/null -w "robots: %{http_code}\n" -m 10 https://trungtamthanhdat.com/robots.txt

# Check tiếng Việt không mojibake.
curl -sS https://trungtamthanhdat.com/ | grep -oE "(Đặt cọc|Trung tâm|tư vấn)" | head -3
```

Mong đợi:
- apex 200, www 301, khoa-hoc 200, dh dummy 404, sitemap 200, robots 200.
- Tiếng Việt có dấu đầy đủ.

## 4. Troubleshoot

### 4.1 Apex trả 502 Bad Gateway

```bash
ssh root@36.50.26.199
docker logs thanhdat-frontend-public-ssr --tail=50
# Lỗi thường gặp:
# - "Cannot find module '/app/server/index.mjs'" -> artifact chưa rsync, chạy CI lại.
# - "EADDRINUSE :3000" -> service cũ chưa stop, `docker compose restart frontend-public-ssr`.
# - "permission denied" -> chmod folder /var/www/thanhdat/frontend-public/.output sang 755.
```

### 4.2 Apex trả 404 cho tất cả route

Container chạy nhưng index không match. Kiểm tra:
```bash
docker exec thanhdat-frontend-public-ssr ls /app/public/
# Phải có index.html, _nuxt/, khoa-hoc/, ...
docker exec thanhdat-frontend-public-ssr ls /app/server/
# Phải có index.mjs, chunks/, node_modules/.
```

Nếu thiếu file: rsync chưa hoàn tất hoặc artifact CI rỗng. Re-run workflow.

### 4.3 CORS error khi submit form lead

DevTools Network thấy `POST /api/public/leads/` bị block. Backend `CORS_ALLOWED_ORIGINS` chưa có `https://trungtamthanhdat.com`. Fix:
```bash
ssh root@36.50.26.199
cd /var/www/thanhdat/infra
# Verify .env.prod có dòng DJANGO_CORS_ORIGINS chứa apex.
grep DJANGO_CORS_ORIGINS .env.prod
docker compose --env-file .env.prod -f docker-compose.prod.yml restart backend
```

### 4.4 Tiếng Việt mojibake

Container Node mặc định locale C. Đã set `TZ=Asia/Ho_Chi_Minh` trong compose. Nếu vẫn lỗi:
```yaml
# docker-compose.prod.yml service frontend-public-ssr environment:
LANG: C.UTF-8
LC_ALL: C.UTF-8
```

## 5. Rollback

```bash
ssh root@36.50.26.199
# Giữ snapshot artifact hiện tại trước khi CI overwrite.
cp -r /var/www/thanhdat/frontend-public/.output /var/www/thanhdat/frontend-public/.output.prev

# Sau khi CI deploy version mới mà có lỗi:
mv /var/www/thanhdat/frontend-public/.output /var/www/thanhdat/frontend-public/.output.bad
mv /var/www/thanhdat/frontend-public/.output.prev /var/www/thanhdat/frontend-public/.output
docker compose --env-file .env.prod -f docker-compose.prod.yml restart frontend-public-ssr
```

Hoặc revert Git commit + push lại → CI build version cũ.

## 6. Migrate sang Cloudflare Pages sau này

Khi lưu lượng cần CDN global:
1. Đổi NS domain sang Cloudflare nameserver.
2. Setup CF Pages theo `docs/06-cloudflare-pages-fe-public.md`.
3. Sửa DNS apex `trungtamthanhdat.com` → CNAME `*.pages.dev` (proxied).
4. Gỡ vhost `trungtamthanhdat.com.conf` khỏi nginx host.
5. Stop docker service `frontend-public-ssr`.
6. Apex sẽ resolve về CF Pages, subdomain `sale.*` `hocvien.*` vẫn ở VPS.

## 7. Definition of Done

- [ ] SSL Let's Encrypt cấp xong cho `trungtamthanhdat.com` + `www.*`.
- [ ] Vhost `trungtamthanhdat.com.conf` symlink + reload nginx OK.
- [ ] Docker service `thanhdat-frontend-public-ssr` healthy.
- [ ] `https://trungtamthanhdat.com/` trả 200, render tiếng Việt có dấu đầy đủ.
- [ ] `https://www.trungtamthanhdat.com/` redirect 301 về apex.
- [ ] `https://trungtamthanhdat.com/dh/abc123` trả 404 (đúng — token sai), không 500.
- [ ] Form đăng ký tư vấn POST lên `https://sale.trungtamthanhdat.com/api/public/leads/` thành công.
- [ ] Push commit `frontend-public/**` → CI auto build + deploy <5 phút.
