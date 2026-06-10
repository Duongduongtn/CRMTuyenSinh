"""
Khởi tạo dữ liệu mặc định sau khi migrate lần đầu:
- 4 Group quyền: admin, sale, accountant, clerk
- 9 Course cho 9 hạng GPLX theo Luật 2025
- SiteSettings singleton (chỉ tạo nếu chưa có)

Idempotent: chạy nhiều lần không tạo trùng. Cập nhật field nếu Course đã tồn tại.

Cách chạy:
    python manage.py bootstrap_data
"""
from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import SiteSettings
from apps.courses.models import Course, VehicleClass, VehicleGroup
from apps.documents.models import DocumentType


GROUPS_SPEC = {
    "admin": "Quản trị viên — toàn quyền",
    "sale": "Tư vấn viên — lead, order",
    "accountant": "Kế toán — xác nhận thanh toán, báo cáo",
    "clerk": "Văn thư — duyệt hồ sơ, in đơn, upload hộ HV",
}


COURSES_SPEC = [
    {
        "slug": "a1",
        "title": "A1",
        "vehicle_class": VehicleClass.A1,
        "vehicle_group": VehicleGroup.MOTORCYCLE,
        "short_description": "Xe máy phổ thông dưới 175cc. Lý thuyết và thực hành ngắn gọn.",
        "tuition_fee": Decimal("1500000"),
        "deposit_amount": Decimal("200000"),
        "duration_days": 14,
        "duration_display": "2 tuần",
        "total_slots": 60,
        "available_slots": 60,
        "is_featured": False,
        "sort_order": 10,
    },
    {
        "slug": "a",
        "title": "A",
        "vehicle_class": VehicleClass.A,
        "vehicle_group": VehicleGroup.MOTORCYCLE,
        "short_description": "Xe phân khối lớn trên 175cc. Thi sa hình mô tô đầy đủ.",
        "tuition_fee": Decimal("5500000"),
        "deposit_amount": Decimal("500000"),
        "duration_days": 21,
        "duration_display": "3 tuần",
        "total_slots": 30,
        "available_slots": 30,
        "sort_order": 20,
    },
    {
        "slug": "b1",
        "title": "B1",
        "vehicle_class": VehicleClass.B1,
        "vehicle_group": VehicleGroup.MOTORCYCLE,
        "short_description": "Mô tô 3 bánh và xe điện công suất lớn theo Luật 2025.",
        "tuition_fee": Decimal("2500000"),
        "deposit_amount": Decimal("300000"),
        "duration_days": 14,
        "duration_display": "2 tuần",
        "total_slots": 20,
        "available_slots": 20,
        "sort_order": 30,
    },
    {
        "slug": "b-so-san",
        "title": "B số sàn",
        "vehicle_class": VehicleClass.B_MT,
        "vehicle_group": VehicleGroup.CAR,
        "short_description": "Lái mọi loại ô tô con dưới 9 chỗ, cả số sàn và số tự động.",
        "tuition_fee": Decimal("17500000"),
        "deposit_amount": Decimal("1000000"),
        "duration_days": 120,
        "duration_display": "4 tháng",
        "total_slots": 30,
        "available_slots": 30,
        "is_featured": True,
        "sort_order": 40,
    },
    {
        "slug": "b-so-tu-dong",
        "title": "B số tự động",
        "vehicle_class": VehicleClass.B_AT,
        "vehicle_group": VehicleGroup.CAR,
        "short_description": "Dễ học, phù hợp người mới. Chỉ lái xe số tự động dưới 9 chỗ.",
        "tuition_fee": Decimal("18500000"),
        "deposit_amount": Decimal("1000000"),
        "duration_days": 120,
        "duration_display": "4 tháng",
        "total_slots": 30,
        "available_slots": 30,
        "sort_order": 50,
    },
    {
        "slug": "c1",
        "title": "C1",
        "vehicle_class": VehicleClass.C1,
        "vehicle_group": VehicleGroup.TRUCK,
        "short_description": "Xe tải dưới 7,5 tấn. Phù hợp người chạy giao hàng nội tỉnh.",
        "tuition_fee": Decimal("22000000"),
        "deposit_amount": Decimal("2000000"),
        "duration_days": 150,
        "duration_display": "5 tháng",
        "total_slots": 20,
        "available_slots": 20,
        "sort_order": 60,
    },
    {
        "slug": "c",
        "title": "C",
        "vehicle_class": VehicleClass.C,
        "vehicle_group": VehicleGroup.TRUCK,
        "short_description": "Xe tải trên 7,5 tấn. Hỗ trợ làm hồ sơ và phương tiện thi.",
        "tuition_fee": Decimal("28000000"),
        "deposit_amount": Decimal("3000000"),
        "duration_days": 150,
        "duration_display": "5 tháng",
        "total_slots": 20,
        "available_slots": 20,
        "sort_order": 70,
    },
    {
        "slug": "d1",
        "title": "D1",
        "vehicle_class": VehicleClass.D1,
        "vehicle_group": VehicleGroup.BUS,
        "short_description": "Xe khách đến 16 chỗ. Đào tạo bao gồm kỹ năng đường đèo.",
        "tuition_fee": Decimal("30000000"),
        "deposit_amount": Decimal("3000000"),
        "duration_days": 180,
        "duration_display": "6 tháng",
        "total_slots": 15,
        "available_slots": 15,
        "sort_order": 80,
    },
    {
        "slug": "d2",
        "title": "D2",
        "vehicle_class": VehicleClass.D2,
        "vehicle_group": VehicleGroup.BUS,
        "short_description": "Xe khách trên 16 chỗ. Cấp giấy phép lái xe đường dài.",
        "tuition_fee": Decimal("35000000"),
        "deposit_amount": Decimal("3500000"),
        "duration_days": 180,
        "duration_display": "6 tháng",
        "total_slots": 15,
        "available_slots": 15,
        "sort_order": 90,
    },
]


class Command(BaseCommand):
    help = "Khởi tạo 4 group quyền, 9 khóa học theo Luật 2025, và SiteSettings mặc định."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("== Bootstrap dữ liệu mặc định =="))

        # 1. Groups
        self.stdout.write("\n[1/3] Tạo 4 group quyền...")
        for name, description in GROUPS_SPEC.items():
            group, created = Group.objects.get_or_create(name=name)
            status = "tạo mới" if created else "đã tồn tại"
            self.stdout.write(f"  - {name} ({description}): {status}")

        # Gán permission Django built-in cho admin group: toàn quyền
        admin_group = Group.objects.get(name="admin")
        admin_group.permissions.set(Permission.objects.all())
        self.stdout.write(f"  - Group 'admin' đã gán toàn bộ {Permission.objects.count()} permission.")

        # Permission set tối thiểu cho sale (lead + enrollment view/add/change, payment view)
        sale_group = Group.objects.get(name="sale")
        sale_perms = Permission.objects.filter(
            content_type__app_label__in=["leads", "orders"],
            codename__in=[
                "view_lead", "add_lead", "change_lead",
                "view_leadcontact", "add_leadcontact",
                "view_leadnote", "add_leadnote",
                "view_leadreason",
                "view_enrollment", "add_enrollment", "change_enrollment",
            ],
        )
        sale_group.permissions.set(sale_perms)
        self.stdout.write(f"  - Group 'sale' gán {sale_perms.count()} permission (lead + enrollment).")

        # Kế toán: payment + casso tx + enrollment readonly
        accountant_group = Group.objects.get(name="accountant")
        acc_perms = Permission.objects.filter(
            content_type__app_label__in=["payments", "orders"],
            codename__in=[
                "view_payment", "add_payment", "change_payment",
                "view_cassotransaction",
                "view_enrollment", "change_enrollment",
            ],
        )
        accountant_group.permissions.set(acc_perms)
        self.stdout.write(f"  - Group 'accountant' gán {acc_perms.count()} permission (payment + đơn).")

        # Văn thư: enrollment view + duyệt hồ sơ + upload hộ HV
        clerk_group = Group.objects.get(name="clerk")
        clerk_perms = Permission.objects.filter(
            content_type__app_label__in=["orders", "leads", "documents", "students"],
            codename__in=[
                "view_enrollment", "view_lead",
                # Duyệt + upload hộ tài liệu
                "view_persondocument", "add_persondocument", "change_persondocument",
                "view_enrollmentdocument", "add_enrollmentdocument", "change_enrollmentdocument",
                "view_documenttype",
                # Person + StudentAccount: xem, sửa cơ bản
                "view_studentaccount", "change_studentaccount",
                "view_person", "add_person", "change_person",
                "view_accountpersonlink", "add_accountpersonlink",
            ],
        )
        clerk_group.permissions.set(clerk_perms)
        self.stdout.write(f"  - Group 'clerk' gán {clerk_perms.count()} permission (đơn + hồ sơ).")

        # 2. Courses
        self.stdout.write("\n[2/3] Tạo 9 khóa học theo Luật 2025...")
        for spec in COURSES_SPEC:
            slug = spec["slug"]
            course, created = Course.objects.update_or_create(
                slug=slug,
                defaults={k: v for k, v in spec.items() if k != "slug"},
            )
            status = "tạo mới" if created else "đã cập nhật"
            self.stdout.write(
                f"  - {course.title} ({course.vehicle_class}) "
                f"· {int(course.tuition_fee):,}đ".replace(",", ".") + f" · {status}"
            )

        # 3. DocumentType — 5 loại mặc định
        self.stdout.write("\n[3/4] Khởi tạo 5 loại tài liệu mặc định...")
        DOC_TYPES = [
            ("cccd_front", "CCCD mặt trước", "person", True,
             "Chụp rõ 4 góc, không chói sáng. Đọc được tên, ngày sinh, số CCCD."),
            ("cccd_back", "CCCD mặt sau", "person", True,
             "Chụp rõ 4 góc, không che mã QR và nơi cấp."),
            ("portrait", "Ảnh chân dung", "person", True,
             "Ảnh 4x6 nền trắng, áo có cổ, mặt rõ, không kính đen."),
            ("health_cert", "Giấy khám sức khỏe", "person", True,
             "Mẫu Bộ Y tế, có dấu bệnh viện, còn hạn 6 tháng."),
            ("application_form", "Đơn đăng ký học lái xe", "enrollment", False,
             "Đơn mẫu Sở GTVT. Trung tâm in giúp sau khi duyệt hồ sơ."),
        ]
        for sort_order, (code, name, scope, required, desc) in enumerate(DOC_TYPES, start=10):
            dt, created = DocumentType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "scope": scope,
                    "is_required": required,
                    "description": desc,
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )
            self.stdout.write(f"  - {dt.name} ({code}): {'tạo mới' if created else 'cập nhật'}")

        # 4. SiteSettings
        self.stdout.write("\n[4/4] Khởi tạo SiteSettings singleton...")
        site, _ = SiteSettings.objects.get_or_create(pk=1)
        self.stdout.write(f"  - SiteSettings (brand: {site.brand_name}): OK")

        self.stdout.write(self.style.SUCCESS("\n✓ Hoàn tất bootstrap dữ liệu."))
        self.stdout.write(
            "\nGợi ý bước tiếp theo:\n"
            "  - Vào http://localhost:8000/admin/ → 'Thông tin trung tâm' để chỉnh tên, logo, hotline, địa chỉ.\n"
            "  - Vào 'Người dùng CRM' để tạo tài khoản cho sale/kế toán/văn thư và gán group tương ứng.\n"
        )
