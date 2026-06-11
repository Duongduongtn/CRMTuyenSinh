# Design System — FE Public CRM Tuyển Sinh Học Lái Xe

Phiên bản: v1 draft, ngày 10/06/2026.
Áp dụng cho: `tencongty.vn` (Nuxt 3 SSG) và `hocvien.tencongty.vn` (Nuxt 3 PWA).
Kế thừa từ: `D:\Du_An\taste-skill\skills\taste-skill\SKILL.md`.

> **Cấu hình dial mặc định cho dự án:**
> - `DESIGN_VARIANCE = 6` — asymmetric hero, balanced features.
> - `MOTION_INTENSITY = 5` — smooth, gentle, không kinetic.
> - `VISUAL_DENSITY = 4` — breathing room, không cockpit.

---

## 1. Color tokens (Trust-first palette)

Không dùng AI purple, beige+brass+oxblood+espresso, không gradient AI sci-fi. Chọn palette "professional driving school" với navy đậm làm core và emerald nhẹ làm accent.

### Light theme (mặc định, 95% người Việt 35-55 không bật dark mode)

```css
:root {
  /* Background */
  --bg-base:        #FBFAF7;  /* off-white cream, không phải #fff */
  --bg-surface:     #FFFFFF;  /* card / modal */
  --bg-subtle:      #F3F0E9;  /* section nhẹ tạo rhythm */
  --bg-inverse:     #0F1B2D;  /* CTA cuối, footer, hero contrast */

  /* Text */
  --text-primary:   #0F1B2D;  /* navy 950, KHÔNG #000 */
  --text-secondary: #4A5568;  /* slate body */
  --text-muted:     #94A3B8;  /* metadata, caption */
  --text-inverse:   #FBFAF7;  /* trên bg-inverse */

  /* Accent — emerald, saturation 65% */
  --accent-base:    #047857;  /* emerald 700, CTA primary */
  --accent-hover:   #065F46;  /* emerald 800 */
  --accent-subtle:  #ECFDF5;  /* badge bg nhẹ */
  --accent-text:    #047857;  /* text emerald */

  /* Functional */
  --success:        #047857;
  --warning:        #B45309;  /* amber 700 */
  --danger:         #B91C1C;  /* red 700, không neon */
  --info:           #1D4ED8;  /* blue 700 */

  /* Border */
  --border-base:    #E5E1D8;  /* warm gray */
  --border-strong:  #94A3B8;
  --border-focus:   #047857;

  /* Shadow (tinted to bg, không pure black) */
  --shadow-soft:    0 1px 2px rgba(15, 27, 45, 0.04),
                    0 2px 8px rgba(15, 27, 45, 0.06);
  --shadow-md:      0 4px 16px rgba(15, 27, 45, 0.08);
  --shadow-lg:      0 16px 48px rgba(15, 27, 45, 0.12);
}
```

### Dark theme (chỉ enable khi user toggle, mặc định OFF cho v1)

```css
[data-theme="dark"] {
  --bg-base:        #0A1525;  /* navy 950 darker */
  --bg-surface:     #0F1B2D;
  --bg-subtle:      #131F35;
  --bg-inverse:     #FBFAF7;
  --text-primary:   #F7F5F0;
  --text-secondary: #94A3B8;
  --accent-base:    #10B981;  /* emerald 500, sáng hơn cho dark */
  --accent-hover:   #34D399;
  --border-base:    #1F2937;
}
```

### Quy tắc dùng màu

- **1 accent duy nhất**: emerald. KHÔNG thêm orange CTA, purple highlight, blue link bừa.
- **Link inline**: dùng `--accent-base` + underline nhẹ. Không bold.
- **Badge**: bg `--accent-subtle` + text `--accent-text`. KHÔNG bg full accent.
- **CTA primary**: bg `--accent-base`, text trắng, hover `--accent-hover`.
- **CTA secondary**: outline `--text-primary`, text `--text-primary`, bg transparent. Hover bg `--bg-subtle`.
- **Contrast WCAG**: kiểm tra mọi cặp text/bg đạt AA 4.5:1 (large 3:1). Body text 16px+ trên cream bg đã đạt 8.4:1, đủ AAA.
- **KHÔNG dùng `#000` và `#fff` thuần** ở đâu hết.

---

## 2. Typography

### Font stack

```css
--font-sans: "Geist", "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
--font-mono: "Geist Mono", ui-monospace, "SF Mono", Consolas, monospace;
```

- Geist hỗ trợ đầy đủ dấu tiếng Việt (đã test diacritic).
- Tải qua `@nuxtjs/google-fonts` hoặc self-host (khuyến nghị self-host để tránh PII leak qua Google Fonts).
- KHÔNG dùng Inter (taste-skill cấm vì là AI default).
- KHÔNG dùng serif (Fraunces, Instrument_Serif) cho dự án này (trust-first, không editorial).

### Scale (mobile first → desktop)

| Token | Mobile | Desktop | Use case |
|---|---|---|---|
| `display-xl` | `text-4xl` (36px) | `text-6xl` (60px) | Hero headline |
| `display-lg` | `text-3xl` (30px) | `text-5xl` (48px) | Section title |
| `display-md` | `text-2xl` (24px) | `text-4xl` (36px) | Subsection |
| `heading-lg` | `text-xl` (20px) | `text-2xl` (24px) | Card title |
| `heading-md` | `text-lg` (18px) | `text-xl` (20px) | List item title |
| `body-lg` | `text-base` (16px) | `text-lg` (18px) | Hero subtext |
| `body` | `text-base` (16px) | `text-base` (16px) | Body content |
| `body-sm` | `text-sm` (14px) | `text-sm` (14px) | Caption, metadata |
| `eyebrow` | `text-xs` (12px) | `text-xs` (12px) | Section label uppercase |

### Quy tắc

- Display: `tracking-tighter` (`-0.025em`), `leading-none` hoặc `leading-tight`, weight 700.
- Body: `leading-relaxed` (`1.625`), max-w `65ch`, weight 400.
- Eyebrow: `uppercase`, `tracking-wider` (`0.1em`), weight 600, màu `--text-muted`.
- Max **1 eyebrow per 3 sections** (theo taste-skill).
- Vietnamese diacritic: đảm bảo descender clearance `pb-1` cho heading có dấu mũ (ư, ơ, ờ, ễ, ặ).
- KHÔNG italic cho heading tiếng Việt (xấu, mất dấu phụ).
- KHÔNG block uppercase cho heading dài > 4 từ tiếng Việt.

### Typography riêng cho CRM admin (compact density)

CRM admin Vue 3 SPA (`frontend-crm/`) dùng **Be Vietnam Pro** + density nhỏ hơn FE public. 5 token bổ sung trong `frontend-crm/tailwind.config.ts`:

| Token | Size / line-height | Letter spacing | Use case |
|---|---|---|---|
| `text-overline` | 10px / 14px | `+0.14em` | Section label nhỏ, badge meta (uppercase) |
| `text-caption` | 12px / 16px | — | Hint dưới input, footer, secondary meta |
| `text-body` | 13px / 20px | — | Nav item, table cell, body text mặc định CRM |
| `text-headline` | 16px / 22px | `-0.01em` | Card title, modal title, section heading |
| `text-display` | 30px / 34px | `-0.025em` | Page hero (Login wordmark, dashboard hero) |

**Quy tắc áp dụng**:

- **File mới**: ưu tiên dùng token (`text-body`, `text-headline`...) thay vì arbitrary `text-[13px]`.
- **File cũ**: KHÔNG bulk replace — refactor dần khi đụng vào file cho nhu cầu khác.
- Không phá scale Tailwind mặc định (`text-sm`, `text-base`...) — token là thêm tier riêng cho design system, không override.

---

## 3. Spacing và layout

### Spacing scale (Tailwind default)

```
0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64
(0.25rem, 0.5rem, 0.75rem, 1rem, ...)
```

### Section padding (theo density = 4)

```css
.section {
  padding-top: var(--py-section);     /* py-16 mobile, py-24 desktop */
  padding-bottom: var(--py-section);
}
.section-spacious {
  padding-top: var(--py-spacious);    /* py-24 mobile, py-32 desktop */
  padding-bottom: var(--py-spacious);
}
```

- Mobile: `py-16` mặc định (64px).
- Desktop: `py-24` mặc định (96px).
- Hero: `pt-12 pb-16 md:pt-24 md:pb-32`.

### Container

```css
.container-narrow { max-width: 768px; }
.container-base   { max-width: 1200px; }
.container-wide   { max-width: 1440px; }
```

- Padding ngang: `px-4 md:px-6 lg:px-8`.

### Grid

- 12 cột Bootstrap-style cho layout phức tạp.
- 4/8/12 column cho bento (vd: hero 7/5, khóa list 6/3/3, chi tiết khóa 8/4).
- Gap: `gap-4 md:gap-6 lg:gap-8`.

### Border radius

```css
--radius-sm: 0.375rem;  /* badge, input nhỏ */
--radius-md: 0.625rem;  /* input, button, card nhỏ */
--radius-lg: 1rem;      /* card lớn, modal */
--radius-xl: 1.25rem;   /* hero image, feature bento */
--radius-2xl: 1.5rem;   /* modal lớn, special card */
```

- **1 corner-radius system** duy nhất (taste-skill rule). KHÔNG mix `rounded-full` với `rounded-md` ngẫu nhiên.
- `rounded-full` chỉ cho: avatar, pill badge, icon button.

---

## 4. Motion (intensity = 5)

### Easing

```css
--ease-default: cubic-bezier(0.16, 1, 0.3, 1);
--ease-in:      cubic-bezier(0.4, 0, 1, 1);
--ease-out:     cubic-bezier(0, 0, 0.2, 1);
```

- KHÔNG dùng `linear` hay `ease-in-out` mặc định của browser.

### Duration

| Token | Time | Use case |
|---|---|---|
| `--motion-fast` | 150ms | Hover, focus, tap feedback |
| `--motion-base` | 300ms | Card lift, modal open, tooltip |
| `--motion-slow` | 600ms | Hero entry, scroll reveal, page transition |
| `--motion-very-slow` | 1200ms | Hero cinematic, không dùng nhiều |

### Patterns

- **Hover scale**: `scale(0.98)` cho button, `scale(1.02)` cho card. Không scale lớn hơn 1.05.
- **Scroll reveal**: `opacity 0 → 1`, `translateY 24px → 0`, stagger 80-100ms. Dùng Motion `whileInView`, KHÔNG `addEventListener('scroll')` + React state.
- **Image lazy**: cross-fade 300ms khi load xong, không "pop in".
- **Page transition**: fade 200ms (Nuxt `<NuxtPage transition="fade" />`).

### Banned

- Magnetic hover (quá playful cho 50yo audience).
- Parallax background.
- Marquee chạy mãi không pause (max 1 per page, có pause on hover).
- Glitch / RGB split effect.
- Cursor follower lớn.
- `prefers-reduced-motion`: PHẢI disable scroll reveal + page transition, giữ fade nhẹ 150ms.

### Chỉ animate transform và opacity

```css
/* ✅ GPU-accelerated */
transition: transform 300ms var(--ease-default),
            opacity 300ms var(--ease-default);

/* ❌ Cấm — gây reflow */
transition: width, height, top, left, margin, padding;
```

---

## 5. Components core

### Button

```tsx
// Primary
<button class="
  inline-flex items-center justify-center gap-2
  px-6 py-3 md:px-8 md:py-4
  bg-emerald-700 hover:bg-emerald-800
  text-white font-medium text-base
  rounded-md
  transition-all duration-150 ease-out
  hover:scale-[0.98]
  focus-visible:ring-2 focus-visible:ring-emerald-700 focus-visible:ring-offset-2
  disabled:opacity-60 disabled:cursor-not-allowed
">
  Đăng ký khóa học
  <ArrowRight class="size-4" />
</button>

// Secondary
<button class="
  inline-flex items-center justify-center gap-2
  px-6 py-3 md:px-8 md:py-4
  border border-slate-900 text-slate-900
  hover:bg-slate-50
  font-medium text-base
  rounded-md
">
  Tư vấn miễn phí
</button>

// Ghost (tertiary, link-like)
<button class="
  inline-flex items-center gap-1
  text-emerald-700 hover:text-emerald-800
  font-medium underline-offset-4 hover:underline
">
  Xem chi tiết
  <ArrowRight class="size-4" />
</button>
```

**Quy tắc:**
- Label 2-3 từ max. KHÔNG "Click here to register" → dùng "Đăng ký".
- Icon đặt SAU label cho action tiếp tục (`→`), TRƯỚC label cho action lùi (`←`).
- Tap target tối thiểu 44x44px (a11y).

### Card

```tsx
<article class="
  flex flex-col gap-4
  p-6 md:p-8
  bg-white
  border border-stone-200
  rounded-xl
  shadow-[var(--shadow-soft)]
  hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5
  transition-all duration-300 ease-out
">
  <div class="aspect-[16/10] overflow-hidden rounded-lg">
    <img src="..." class="size-full object-cover" loading="lazy">
  </div>
  <span class="text-xs uppercase tracking-wider text-stone-500 font-semibold">
    EYEBROW (tùy chọn)
  </span>
  <h3 class="text-xl font-semibold text-slate-900 leading-tight">
    Tiêu đề card
  </h3>
  <p class="text-base text-stone-600 leading-relaxed">
    Mô tả ngắn 2 dòng, không quá 25 từ.
  </p>
  <div class="mt-auto flex items-center justify-between">
    <span class="text-2xl font-bold text-slate-900">17.500.000đ</span>
    <a class="...ghost-button">Chi tiết</a>
  </div>
</article>
```

### Form input

```tsx
<label class="flex flex-col gap-2">
  <span class="text-sm font-medium text-slate-900">
    Số điện thoại <span class="text-red-700">*</span>
  </span>
  <input
    type="tel"
    class="
      h-12 px-4
      bg-white
      border border-stone-300
      rounded-md
      text-base text-slate-900 placeholder:text-stone-400
      focus:outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100
      invalid:border-red-700
    "
    placeholder="0901234567"
  />
  <span class="text-sm text-red-700 hidden peer-invalid:block">
    Số điện thoại không hợp lệ
  </span>
</label>
```

**Quy tắc:**
- Label LUÔN ở trên input, không placeholder-as-label.
- Required marker: `*` đỏ nhạt sau label.
- Height tối thiểu 48px cho mobile.
- Error message dưới input, có `aria-live="polite"`.

### Badge

```tsx
<span class="
  inline-flex items-center gap-1
  px-2.5 py-1
  bg-emerald-50 text-emerald-700
  text-xs font-semibold
  rounded-full
">
  Phổ biến
</span>
```

### Header (navigation)

```tsx
<header class="
  sticky top-0 z-50
  bg-white/80 backdrop-blur-md
  border-b border-stone-200
">
  <nav class="container-base flex items-center justify-between h-16 md:h-20 px-4 md:px-6">
    <a href="/" class="flex items-center gap-2">
      <Logo class="size-8" />
      <span class="font-bold text-lg text-slate-900">Tên Trung Tâm</span>
    </a>
    <ul class="hidden md:flex items-center gap-8">
      <li><a class="text-sm font-medium hover:text-emerald-700">Khóa học</a></li>
      <li><a class="text-sm font-medium hover:text-emerald-700">Tin tức</a></li>
      <li><a class="text-sm font-medium hover:text-emerald-700">Về chúng tôi</a></li>
      <li><a class="text-sm font-medium hover:text-emerald-700">Liên hệ</a></li>
    </ul>
    <div class="flex items-center gap-3">
      <a href="tel:..." class="hidden md:inline-flex ... ghost-button">
        <Phone class="size-4" /> 0900.xxx.xxx
      </a>
      <button class="primary-button">Tư vấn</button>
      <button class="md:hidden"><Menu /></button>
    </div>
  </nav>
</header>
```

---

## 6. Iconography

- **Library**: Phosphor Icons (`@phosphor-icons/vue`). KHÔNG hand-roll SVG.
- **Style**: `regular` cho thân thiện, `bold` cho icon button.
- **Size**: `size-4` (16px), `size-5` (20px), `size-6` (24px). Cho hero feature dùng `size-8` (32px).
- **Color**: thừa hưởng từ text color, không hard-code.
- **Icon thường dùng**:
  - `CaretRight` cho link tiếp tục
  - `CheckCircle` cho list "đã bao gồm"
  - `Phone`, `WhatsappLogo`, `Envelope` cho liên hệ
  - `Calendar`, `Clock` cho lịch khai giảng
  - `Certificate` cho bằng cấp / chứng chỉ
  - `Car`, `Motorcycle`, `Truck`, `Bus` cho hạng xe

---

## 7. Imagery

### Quy tắc nguồn ảnh

- **Ưu tiên 1**: Ảnh thật chụp tại trung tâm (HLV, học viên, sân tập, xe). User cần cung cấp 20-30 ảnh chất lượng cao.
- **Ưu tiên 2**: AI gen-tool (Midjourney, FLUX) với prompt cụ thể.
- **Ưu tiên 3**: Stock từ Pexels/Unsplash (chọn ảnh Việt Nam / Đông Nam Á, không quá Tây).
- **CẤM**: ảnh AI sci-fi gradient, ảnh fake screenshot dashboard, illustrations vector flat AI-style.

### Ảnh cần có cho v1

| Vị trí | Loại | Tỉ lệ | Số lượng |
|---|---|---|---|
| Hero trang chủ | HLV + xe + sân | 4:5 | 1 |
| Section "tại sao chúng tôi" | Lớp lý thuyết | 5:4 | 1 |
| Section "quy trình" | Học viên thực hành | 5:4 | 1 |
| Card khóa học | Xe đại diện hạng | 4:3 | 9 (mỗi hạng 1) |
| Hero chi tiết khóa | Xe + HLV + sân | 16:9 | 9 |
| Avatar HLV | Chân dung | 1:1 | 6-10 |
| Cover blog post | Tùy nội dung | 16:9 | mỗi bài 1 |
| OG image | Logo + slogan | 1200x630 | 1 mặc định + tùy bài |

### Tối ưu

- Format: AVIF (fallback WebP, fallback JPG).
- Responsive: `srcset` 3 size (mobile 480w, tablet 800w, desktop 1440w).
- `loading="lazy"` cho ảnh dưới fold, `priority` (Nuxt Image) cho hero.
- Dùng `@nuxt/image` hoặc Cloudflare Images CDN.

---

## 8. Responsive breakpoints

```css
sm:  640px   /* mobile lớn / tablet nhỏ */
md:  768px   /* tablet */
lg:  1024px  /* laptop nhỏ / desktop */
xl:  1280px  /* desktop */
2xl: 1536px  /* desktop lớn */
```

### Mobile-first checklist

- Hero ảnh xuống dưới text, không stack ngang.
- Bento → 1 cột.
- Sidebar chi tiết khóa → đẩy xuống dưới content.
- Header: hamburger menu + CTA chính giữ.
- Form: full width, button full width.
- Modal: full screen, không có corner radius.
- Font size base giữ 16px (KHÔNG nhỏ hơn để tránh zoom iOS).

---

## 9. Accessibility

- **WCAG AA tối thiểu** cho mọi cặp màu.
- **Focus ring**: visible mọi interactive (`focus-visible:ring-2 ring-emerald-700 ring-offset-2`).
- **Skip-to-content**: link đầu trang ẩn cho đến khi focus.
- **Aria label**: cho mọi icon button, nav link.
- **Form**: label ABOVE input, error có `aria-live`, `aria-invalid`.
- **Reduced motion**: respect `prefers-reduced-motion`, giảm scroll reveal.
- **Color blind**: trust không CHỈ dùng màu (badge "phổ biến" vẫn có text + icon).
- **Heading hierarchy**: đúng thứ tự `h1 → h2 → h3`, không nhảy cóc.

---

## 10. Tham khảo nội bộ

- Skill chính: `D:\Du_An\taste-skill\skills\taste-skill\SKILL.md`
- Skill soft (premium): `D:\Du_An\taste-skill\skills\soft-skill\SKILL.md` — tham khảo cho card lift, glass effect nhẹ.
- Pre-flight checklist: Section 14 của `SKILL.md` — chạy trước mỗi PR merge.
- Wireframe: `docs/01-wireframes-fe-public.md`.
- Plan triển khai: `docs/03-phase1-plan.md`.
