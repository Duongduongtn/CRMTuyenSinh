"""Auto-provision StudentAccount khi Enrollment được tạo.

Pattern theo memory [[student-auth-flow]]: sale chốt đơn → tạo Enrollment →
hệ thống tự tạo StudentAccount cho SĐT (nếu chưa có) để HV login được ngay.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.orders.models import Enrollment

from .models import StudentAccount, normalize_phone


@receiver(post_save, sender=Enrollment)
def auto_provision_student_account(sender, instance: Enrollment, created: bool, **kwargs):
    if not created or not instance.student_phone:
        return
    phone = normalize_phone(instance.student_phone)
    if not phone:
        return
    StudentAccount.objects.get_or_create(
        phone=phone,
        defaults={"display_name": instance.student_name or ""},
    )
