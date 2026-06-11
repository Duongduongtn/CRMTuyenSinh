"""Sprint 3 Tuần 7 (2026-06-12) — gói B: gỡ bảng OTPRequest.

Auth học viên đã chuyển sang SĐT + 6 số cuối CCCD ở migration 0003 + commit
gói B (xem [[student-auth-flow]]). Bảng OTPRequest không còn đường tới nó:

- View ``request_otp`` + ``verify_otp`` đã bị xóa.
- ZNS adapter đã bị xóa hoàn toàn.
- Admin reg đã bị xóa.

Drop bảng OTPRequest. Dữ liệu OTP cũ là log, không có ràng buộc FK, xóa an
toàn. Không backup vì OTP code đã hash + dữ liệu này không có giá trị forensic
sau khi gỡ flow.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0003_studentaccount_lock_fields"),
    ]

    operations = [
        migrations.DeleteModel(
            name="OTPRequest",
        ),
    ]
