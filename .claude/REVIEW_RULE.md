# Rule: Subagent review sau mỗi gói việc

> Áp dụng cho mọi phiên làm việc trên dự án CRMTuyensinh.
> Tham chiếu chi tiết mapping: `docs/04-skills-agents-mapping.md`.

## Nguyên tắc

Sau mỗi gói code (BE / FE / integration / security) xong + smoke test pass local, **BẮT BUỘC** spawn reviewer agent tương ứng **TRƯỚC khi commit/push**. Không gộp nhiều gói rồi review một lượt — mất context, miss issue.

## Mapping nhanh

| Thay đổi đụng vào | Spawn reviewer | Khi |
|---|---|---|
| `backend/apps/*` model, migration, view, serializer, settings, admin | `backend-django-reviewer` | Sau code BE xong, trước commit |
| `apps/leads/`, `apps/orders/` lead capture / convert flow | `lead-pipeline-reviewer` | Sau sửa pipeline lead → order |
| `apps/payments/`, Casso webhook, idempotency key | `payment-integration-reviewer` | Sau sửa payment |
| `frontend-public/`, `frontend-crm/`, `frontend-student/` — `.vue`, `.html`, `.css`, `.ts` UI | `frontend-ui-reviewer` | Sau xong component, trước commit |
| `frontend-public/` SEO meta, JSON-LD schema, sitemap, robots | `seo-public-reviewer` | Sau sửa public + trước deploy FE |
| Endpoint mới, secret handling (Fernet, .env.prod), file upload CCCD, IDOR risk | `security-rbac-reviewer` | Sau code, trước launch |
| Trước go-live production lần đầu | `phase3-prelaunch-reviewer` | Cuối Sprint 3, full audit |

## Quy tắc thực hành

1. **Spawn SAU smoke test pass local** — không gửi code chưa chạy cho reviewer (lãng phí).
2. **Reviewer PASS → commit** | **Reviewer FAIL → fix theo recommendation → spawn lại**.
3. **Báo cáo nội bộ cuối phiên** phải liệt kê reviewer nào đã chạy + verdict (PASS / FAIL + số issue fix).
4. **Phase-gate reviewer** chỉ spawn ở milestone cuối phase, không spawn cho từng commit.
5. **Song song nhiều reviewer**: khi 1 gói đụng nhiều domain (vd BE + FE cùng commit) → spawn nhiều reviewer trong 1 message (mỗi `Agent` 1 block).
6. **Reviewer bị skip có lý do** → ghi rõ vào báo cáo cuối phiên (vd "FE chỉ đổi text VN, không cần frontend-ui-reviewer").

## Ví dụ phiên Sprint 3 Tuần 7 (gói A — 2026-06-11)

| Bước | Loại | Reviewer dự kiến |
|---|---|---|
| 1. Cấp FERNET_SECRET trên VPS | Security (secret handling) | `security-rbac-reviewer` |
| 2. Rebuild backend + migrate IntegrationCredential | BE Django | `backend-django-reviewer` |
| 3. Refactor BE bỏ ZNS + SMTP khỏi INTEGRATION_SCHEMA | BE Django + Security | `backend-django-reviewer` + `security-rbac-reviewer` (song song) |
| 4. Build SPA Vue 3 tab `/admin/integrations` | FE UI | `frontend-ui-reviewer` |
| 5. Trước commit + push cuối phiên | Tổng | Tổng kết verdict trong commit message |

## Lý do tồn tại rule này

User chăm chút thẩm mỹ FE (memory `frontend-aesthetic-priority`) + dự án xử lý CCCD nhạy cảm (NĐ 13/2023) + payment thật. Một mình code không đủ — reviewer agent là layer thứ 2 bắt issue trước khi push prod.

Bỏ qua rule này = ship code chưa review = rủi ro break prod + lộ data + UI tầm thường.
