"""Helper validate + lưu ảnh brand cho SiteSettings (logo / favicon / og_image).

Tách thành module riêng để:

- Test logic validation độc lập với view DRF.
- Sprint 4+ có thể reuse cho upload ảnh blog cover, ảnh khóa học, avatar nhân
  viên... — pattern y hệt: enum field + spec MIME/size/dimension + AuditLog.

Pillow là dependency cứng (đã cài sẵn 10.4.0). Dùng PIL để xác minh content
THỰC SỰ là ảnh (chống attacker upload `.php` rename thành `.png`).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError

# Cap pixel count tổng tránh decompression bomb: attacker gửi PNG/WEBP nén raw
# 100x100 nhưng decode thành 100_000x100_000 → cấp phát ~10GB RAM khi PIL mở.
# PIL.Image.MAX_IMAGE_PIXELS default ~178MP, em hạ xuống 16MP = 4096x4096 khớp
# max_dimension lớn nhất trong IMAGE_FIELD_SPECS. PIL raise Image.DecompressionBombError
# (subclass of Exception) khi vượt → bị bắt vào nhánh ValidationError chuẩn.
Image.MAX_IMAGE_PIXELS = 4096 * 4096


@dataclass(frozen=True)
class ImageFieldSpec:
    """Spec cho 1 field ảnh trong SiteSettings.

    - ``allowed_mime``: tập MIME server-side coi là hợp lệ. Verify bằng PIL
      ``Image.format`` chứ KHÔNG tin ``Content-Type`` client gửi.
    - ``max_bytes``: cap kích thước upload.
    - ``min_dimension`` / ``max_dimension``: WxH bound (px).
    """

    field_name: str
    allowed_mime: frozenset[str]
    max_bytes: int
    min_dimension: tuple[int, int]
    max_dimension: tuple[int, int]


# PIL format → mime canonical. ICO không có MIME chuẩn (image/x-icon vs
# image/vnd.microsoft.icon) nên dùng PIL format text trực tiếp.
# WARN: phải đồng bộ với frontend-crm/src/api/siteSettings.ts BRAND_IMAGE_SPEC.
# Sprint 4+ có thể expose endpoint GET /api/admin/site-settings/image-spec/ để
# FE pull tránh drift. Hiện tại 1 nguồn duy nhất là file này, FE hard-code lại.
IMAGE_FIELD_SPECS: dict[str, ImageFieldSpec] = {
    "logo": ImageFieldSpec(
        field_name="logo",
        allowed_mime=frozenset({"PNG", "JPEG", "WEBP"}),
        max_bytes=2 * 1024 * 1024,  # 2 MB
        min_dimension=(256, 256),
        max_dimension=(4096, 4096),
    ),
    "favicon": ImageFieldSpec(
        field_name="favicon",
        allowed_mime=frozenset({"PNG", "ICO"}),
        max_bytes=512 * 1024,  # 512 KB
        min_dimension=(16, 16),
        max_dimension=(512, 512),
    ),
    "og_image": ImageFieldSpec(
        field_name="og_image",
        allowed_mime=frozenset({"PNG", "JPEG", "WEBP"}),
        max_bytes=5 * 1024 * 1024,  # 5 MB
        min_dimension=(600, 315),  # FB tối thiểu, sẽ bị scale up nếu nhỏ hơn
        max_dimension=(4096, 4096),
    ),
}


def validate_uploaded_image(field: str, upload: UploadedFile) -> str:
    """Validate file upload theo spec field. Trả PIL format text (vd ``"PNG"``).

    Raises:
        django.core.exceptions.ValidationError: bất kỳ rule vi phạm.

    Behavior:
        - Reject sớm nếu field không nằm trong IMAGE_FIELD_SPECS.
        - Cap size bằng ``upload.size`` (server đã enforce
          ``FILE_UPLOAD_MAX_MEMORY_SIZE`` ở stage parse, đây là double-check
          theo spec per-field nhỏ hơn).
        - Verify TRUE image bằng PIL: load bytes → ``Image.verify()`` raise
          ``UnidentifiedImageError`` nếu file fake (vd attacker rename
          ``shell.php`` → ``logo.png``).
        - Verify dimension (width × height) trong bound spec.
        - Verify PIL format nằm trong ``allowed_mime``.
        - SVG bị reject ngầm vì Pillow KHÔNG decode SVG → ``UnidentifiedImageError``.
          Sprint 4+ nếu cần SVG: thêm nhánh riêng + scan ``<script>`` chống XSS.
    """
    spec = IMAGE_FIELD_SPECS.get(field)
    if spec is None:
        raise ValidationError(
            f"Field ảnh không hợp lệ: {field}. Chỉ chấp nhận: "
            f"{', '.join(sorted(IMAGE_FIELD_SPECS))}."
        )

    if upload.size is None or upload.size <= 0:
        raise ValidationError("File rỗng hoặc không đọc được kích thước.")

    if upload.size > spec.max_bytes:
        raise ValidationError(
            f"Kích thước vượt giới hạn {spec.max_bytes // 1024} KB "
            f"cho field {field} (file {upload.size // 1024} KB)."
        )

    # Reset stream về đầu trước khi verify để PIL đọc từ byte 0. PIL.Image.open
    # KHÔNG tự rewind, và caller có thể đã đọc trước (vd middleware).
    upload.seek(0)
    try:
        # verify() chỉ scan header + structure, KHÔNG decode full pixel data
        # → không tốn memory. Sau verify, image instance đã ở trạng thái không
        # dùng được nữa (PIL doc) → mở lại để đọc size + format.
        verifier = Image.open(upload)
        verifier.verify()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        ValueError,
        SyntaxError,
    ) as exc:
        # 5 exception PIL doc liệt kê cho file corrupt/truncated/bomb. KHÔNG bắt
        # Exception chung — để Pillow bug thật bubble lên 500 + sentry alert.
        raise ValidationError(
            f"File không phải ảnh hợp lệ ({type(exc).__name__})."
        ) from exc

    upload.seek(0)
    try:
        image = Image.open(upload)
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        ValueError,
        SyntaxError,
    ) as exc:
        raise ValidationError(
            f"File không phải ảnh hợp lệ ({type(exc).__name__})."
        ) from exc
    detected_format = image.format or ""

    if detected_format not in spec.allowed_mime:
        raise ValidationError(
            f"Định dạng {detected_format or 'không xác định'} không được "
            f"chấp nhận cho field {field}. Chỉ chấp nhận: "
            f"{', '.join(sorted(spec.allowed_mime))}."
        )

    width, height = image.size
    min_w, min_h = spec.min_dimension
    max_w, max_h = spec.max_dimension
    if width < min_w or height < min_h:
        raise ValidationError(
            f"Kích thước ảnh {width}x{height} nhỏ hơn tối thiểu "
            f"{min_w}x{min_h} cho field {field}."
        )
    if width > max_w or height > max_h:
        raise ValidationError(
            f"Kích thước ảnh {width}x{height} vượt tối đa "
            f"{max_w}x{max_h} cho field {field}."
        )

    upload.seek(0)
    return detected_format


def safe_image_filename(field: str, detected_format: str) -> str:
    """Sinh tên file ngẫu nhiên dạng ``{field}_{uuid4}.{ext}``.

    Không dùng tên gốc do user upload để:

    - Chống path traversal (vd ``../../etc/passwd``).
    - Chống collision khi 2 ảnh cùng tên (browser cache không refresh).
    - Tên dự đoán được sẽ giúp attacker enumerate file → uuid v4 đảm bảo
      unpredictable.
    """
    ext_map = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp", "ICO": "ico"}
    ext = ext_map.get(detected_format, detected_format.lower())
    return f"{field}_{uuid.uuid4().hex}.{ext}"


def to_audit_value(field_file: Any) -> str:
    """Convert ImageFieldFile thành string an toàn cho AuditLog (chỉ tên file).

    KHÔNG log URL absolute (lộ MEDIA_URL prefix + có thể chứa token). Đường
    dẫn tương đối ``brand/logo_xxx.png`` đủ truy vết.
    """
    if not field_file:
        return ""
    return str(field_file)
