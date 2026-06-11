# Cloudflare Pages — Deploy FE public (trungtamthanhdat.com)

> Tham chiếu: `frontend-public/nuxt.config.ts`, `docs/05-sprint3-soft-launch.md` mục 5 (smoke test E2E).
> Mục đích: deploy FE public landing tuyển sinh lên Cloudflare Pages, gắn domain chính `trungtamthanhdat.com`, miễn phí, CDN global, SSL auto.

---

## 0. Vì sao Cloudflare Pages

- **Free** 500 build/tháng, 100GB bandwidth/tháng — quá đủ cho landing.
- **CDN global**: visitor VN ping <50ms, không cần VPS riêng cho FE.
- **SSL auto** Let's Encrypt + HTTP/3.
- **Atomic deploy + rollback**: mỗi push main → 1 deployment, rollback 1 click.
- **Tách hẳn VPS BNIX**: VPS chỉ chạy CRM + BE + PWA HV. FE public sập không ảnh hưởng `sale.*` `hocvien.*`.

## 1. Pre-requisite

- [ ] Tên miền `trungtamthanhdat.com` đã trỏ DNS về Cloudflare (NS records). Nếu mua qua nhà cung cấp khác (Mắt Bão, PA Việt Nam, GoDaddy...), vào panel của họ đổi NS thành 2 nameserver Cloudflare cấp (ví dụ `alex.ns.cloudflare.com`, `nora.ns.cloudflare.com`). Đợi 10-60 phút propagate.
- [ ] Repo `Duongduongtn/CRMTuyenSinh` đã có nhánh `main` xanh CI.
- [ ] Cloudflare account đăng ký (free tier — đủ).

## 2. Quyết định kiến trúc — Hybrid SSR, KHÔNG pure SSG

Route `/dh/[token]` (đặt cọc QR) ở `frontend-public/pages/dh/[token].vue` gọi `useEnrollmentByToken()` top-level setup → cần Node runtime SSR. Pure SSG `nuxt generate` sẽ trả 404 vì route động không prerender.

**Giải pháp**: deploy hybrid Nuxt qua nitro preset `cloudflare-pages`. CF Pages chạy `_worker.js` (Cloudflare Workers Runtime) cho SSR `/dh/**`, các route khác (`/`, `/khoa-hoc/**`, `/tin-tuc/**`, `/lien-he`) đã prerender sẵn thành HTML tĩnh — serve siêu nhanh từ CDN edge.

→ **Build command đổi**: `pnpm install && pnpm run build` (KHÔNG dùng `pnpm run generate`).
→ **Build output dir**: `frontend-public/.output/public/` (chuẩn Nuxt 3 + cloudflare-pages preset).
→ **Env build-time**: `NITRO_PRESET=cloudflare-pages`.

## 3. Tạo project Cloudflare Pages

### 3.1 Connect Git

1. Login [dash.cloudflare.com](https://dash.cloudflare.com) → menu **Workers & Pages** → tab **Create application** → **Pages** → **Connect to Git**.
2. Authorize GitHub → chọn account `Duongduongtn` → chọn repo `CRMTuyenSinh`.
3. Begin setup:
   - **Project name**: `crm-tuyensinh-fe-public` (xuất hiện ở subdomain CF tạm thời: `crm-tuyensinh-fe-public.pages.dev`).
   - **Production branch**: `main`.

### 3.2 Build settings

| Field | Giá trị |
|---|---|
| **Framework preset** | `Nuxt.js` |
| **Build command** | `pnpm install && pnpm run build` |
| **Build output directory** | `frontend-public/.output/public` |
| **Root directory** (Advanced) | `frontend-public` |
| **Node version** | `20` (tương thích Nuxt 3.21 + nitro 2.13) |

> **Lưu ý Root directory**: vì repo có 3 FE (`frontend-public`, `frontend-student`, `frontend-crm`), set root = `frontend-public` để CF chỉ build folder này, không bị cồng kềnh node_modules của 2 FE kia.

### 3.3 Environment variables (build & runtime)

Mục **Settings → Environment variables** sau khi tạo project xong. Chia thành 2 scope: **Production** và **Preview** (cùng giá trị cho soft launch).

| Tên | Production | Mục đích |
|---|---|---|
| `NITRO_PRESET` | `cloudflare-pages` | Nitro biết build cho CF Workers, sinh `_worker.js` |
| `NUXT_PUBLIC_API_BASE` | `https://sale.trungtamthanhdat.com/api` | FE gọi BE qua subdomain CRM |
| `NUXT_PUBLIC_SITE_URL` | `https://trungtamthanhdat.com` | Canonical URL cho SEO + OG meta |
| `NUXT_PUBLIC_STUDENT_URL` | `https://hocvien.trungtamthanhdat.com` | CTA "Học viên" link sang PWA |
| `NODE_VERSION` | `20` | Backup khi UI preset bỏ qua |

> KHÔNG paste secret (API token, JWT signing key) ở đây — FE public CHỈ cần URL công khai. Tất cả secret nằm ở backend `.env.prod` trên VPS.

### 3.4 Save & deploy lần đầu

- Bấm **Save and Deploy** → CF chạy build ~3-5 phút.
- Theo dõi log realtime: nếu fail thường do:
  - Thiếu `NITRO_PRESET` → mặc định preset `node-server`, build vẫn pass nhưng output sai cấu trúc, runtime 500.
  - pnpm version mismatch → CF dùng `corepack`, repo có `packageManager` field trong `package.json` thì auto pick đúng version. Nếu chưa có, set env `PNPM_VERSION=9` để khớp lock.
  - Memory OOM khi build (lock file lớn) → enable **Build cache** ở Settings → Builds.

## 4. Gắn custom domain `trungtamthanhdat.com`

### 4.1 Apex domain

1. Project → tab **Custom domains** → **Set up a custom domain**.
2. Nhập `trungtamthanhdat.com` (không có `www.`, không có `https://`).
3. CF tự thêm DNS record: `CNAME @ crm-tuyensinh-fe-public.pages.dev` (proxied). Vì DNS đã trên Cloudflare → bấm **Activate domain** xong.
4. SSL Universal Edge cert phát hành <2 phút.

### 4.2 www → apex (301)

1. Tab **DNS** ở dashboard chính (không phải trong project Pages) → add record:
   - Type `CNAME`, Name `www`, Target `trungtamthanhdat.com`, Proxy `On`.
2. Tab **Rules → Redirect Rules** → Create → preset **Redirect from WWW to root**:
   - Hostname equals `www.trungtamthanhdat.com` → 301 → `https://trungtamthanhdat.com/$1`.

### 4.3 Force HTTPS

Tab **SSL/TLS → Edge Certificates**:
- Always Use HTTPS = **On**.
- Automatic HTTPS Rewrites = **On**.
- Minimum TLS Version = **TLS 1.2**.

## 5. Smoke test sau deploy (5 phút)

```bash
# 1. Apex 200, render HTML đúng tiếng Việt có dấu
curl -sS -o /dev/null -w "apex: %{http_code}\n" -m 10 https://trungtamthanhdat.com/
curl -sS https://trungtamthanhdat.com/ | grep -oE "(Đặt cọc|Trung tâm|hạng B|tư vấn)" | head -5

# 2. www redirect 301 về apex
curl -sS -o /dev/null -w "www: %{http_code} -> %{redirect_url}\n" -m 10 https://www.trungtamthanhdat.com/

# 3. Khóa học prerender
curl -sS -o /dev/null -w "khoa-hoc: %{http_code}\n" -m 10 https://trungtamthanhdat.com/khoa-hoc
curl -sS -o /dev/null -w "khoa-hoc B-MT: %{http_code}\n" -m 10 https://trungtamthanhdat.com/khoa-hoc/b-mt

# 4. SSR /dh/[token] — token dummy phải trả 404 (createError 404 trong setup), KHÔNG phải 500
curl -sS -o /dev/null -w "dh dummy: %{http_code}\n" -m 10 https://trungtamthanhdat.com/dh/abc123

# 5. Sitemap + robots
curl -sS -o /dev/null -w "sitemap: %{http_code}\n" -m 10 https://trungtamthanhdat.com/sitemap.xml
curl -sS -o /dev/null -w "robots: %{http_code}\n" -m 10 https://trungtamthanhdat.com/robots.txt
```

Expected:
- apex 200, www 301, khoa-hoc 200, khoa-hoc/b-mt 200, dh/abc123 **404** (đúng — token không hợp lệ), sitemap 200, robots 200.

## 6. Smoke test E2E Step 1 capture lead

Sau khi 5 bước trên pass, quay về `docs/05-sprint3-soft-launch.md` **mục 5 Step 1**:

1. Mở `https://trungtamthanhdat.com/` browser thật.
2. Bấm **Đăng ký tư vấn** → fill form: tên, SĐT thật, chọn hạng B.
3. Submit → kỳ vọng:
   - Thông báo thành công.
   - Lead xuất hiện ở `https://sale.trungtamthanhdat.com/admin/leads/lead/`.
4. Nếu form submit fail → DevTools Network tab → check request đến `https://sale.trungtamthanhdat.com/api/public/leads/`:
   - 200/201 = OK.
   - **0 (CORS)** = BE chưa cho phép origin `https://trungtamthanhdat.com`. Sửa `CORS_ALLOWED_ORIGINS` trong `.env.prod` trên VPS rồi `docker compose restart backend`.
   - 404 = endpoint sai (check composable `useLeadCapture.ts`).
   - 500 = BE log có exception → SSH VPS `docker logs thanhdat-backend`.

## 7. Rollback nhanh

Tab **Deployments** → tìm deployment cũ ổn định → menu (...) → **Rollback to this deployment**. Mất ~10s, không cần đụng Git.

## 8. CI/CD note

CF Pages tự nhận webhook từ GitHub mỗi push `main` → trigger build. **Workflow `.github/workflows/deploy.yml` của VPS KHÔNG cần care về FE public** — chỉ care backend + PWA student + CRM admin SPA.

→ Khi push commit chỉ động đến `frontend-public/**`:
- VPS workflow chạy nhanh (skip rsync FE public dist).
- CF Pages build độc lập, không ảnh hưởng VPS uptime.

## 9. Definition of Done — Cloudflare Pages

- [ ] Project CF Pages tạo xong, build pass.
- [ ] Custom domain `trungtamthanhdat.com` active SSL valid.
- [ ] 5 endpoint smoke test mục 5 đúng status code.
- [ ] 1 lead test submit từ FE public landing → xuất hiện trong CRM admin.
- [ ] Push 1 commit nhỏ → CF auto build + deploy trong <5 phút.
