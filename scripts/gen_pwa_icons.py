"""Sinh icon PWA cho frontend-student/public/.

Output:
  - icon-192.png   (192x192, PWA standard)
  - icon-512.png   (512x512, PWA standard + maskable any)
  - favicon.ico    (32x32 + 16x16 multi-resolution)

Logo: chữ "HV" (Học Viên) trắng trên nền xanh #15803D (theme_color trong
nuxt.config.ts của frontend-student). Khi user đổi brand, sửa BG/TEXT/FONT
rồi chạy lại: `python scripts/gen_pwa_icons.py`.

Đầy đủ nền đặc kín → an toàn cho maskable purpose (không bị crop trắng).
"""
from __future__ import annotations
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parents[1] / "frontend-student" / "public"
BG = (21, 128, 61)       # emerald-700 #15803D
TEXT_COLOR = (255, 255, 255)
TEXT = "HV"

CANDIDATE_FONTS = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVu-Sans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in CANDIDATE_FONTS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def draw_centered_text(img: Image.Image, text: str, font_size: int) -> None:
    draw = ImageDraw.Draw(img)
    font = load_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (img.width - text_w) / 2 - bbox[0]
    y = (img.height - text_h) / 2 - bbox[1]
    draw.text((x, y), text, fill=TEXT_COLOR, font=font)


def make_icon(size: int, out_path: Path) -> None:
    img = Image.new("RGB", (size, size), BG)
    draw_centered_text(img, TEXT, int(size * 0.42))
    img.save(out_path, format="PNG", optimize=True)
    print(f"  + {out_path.name} ({size}x{size})")


def make_favicon(out_path: Path) -> None:
    base = Image.new("RGB", (64, 64), BG)
    draw_centered_text(base, TEXT, 30)
    base.save(out_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"  + {out_path.name} (multi: 16/32/48)")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Sinh icon PWA vào {OUT_DIR}")
    make_icon(192, OUT_DIR / "icon-192.png")
    make_icon(512, OUT_DIR / "icon-512.png")
    make_favicon(OUT_DIR / "favicon.ico")
    print("Xong.")


if __name__ == "__main__":
    main()
