"""Sprint 3 Tuần 7 (2026-06-12) — gói B: thêm 3 field hỗ trợ rate limit login.

Auth học viên chuyển từ ZNS OTP sang SĐT + 6 số cuối CCCD (xem
[[student-auth-flow]]). Brute force 6 số cuối CCCD = 10^6 khả năng — cần khóa
tay theo SĐT để đảm bảo an toàn:

- ``failed_login_count``: counter sai liên tiếp, reset khi login thành công.
- ``locked_until``: thời điểm hết khóa. Sau 5 lần sai → khóa 15 phút. Sau 10
  lần sai tổng → khóa 24 giờ.
- ``last_login_ip``: IP đăng nhập gần nhất để audit / forensics.

Migration AddField — không backfill (default 0/null là an toàn cho tài khoản
hiện hữu chưa từng đăng nhập theo flow mới).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0002_studentdeleterequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentaccount",
            name="last_login_ip",
            field=models.GenericIPAddressField(
                blank=True,
                null=True,
                verbose_name="IP đăng nhập gần nhất",
            ),
        ),
        migrations.AddField(
            model_name="studentaccount",
            name="failed_login_count",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text=(
                    "Khóa 15 phút sau 5 lần, khóa 24 giờ sau 10 lần. Reset về 0 "
                    "khi đăng nhập thành công."
                ),
                verbose_name="Số lần đăng nhập sai liên tiếp",
            ),
        ),
        migrations.AddField(
            model_name="studentaccount",
            name="locked_until",
            field=models.DateTimeField(
                blank=True,
                help_text="Sau thời điểm này tài khoản có thể đăng nhập lại.",
                null=True,
                verbose_name="Tạm khóa đến",
            ),
        ),
        migrations.AddIndex(
            model_name="studentaccount",
            index=models.Index(fields=["locked_until"], name="sa_locked_until_idx"),
        ),
    ]
