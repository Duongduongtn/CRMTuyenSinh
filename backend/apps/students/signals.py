"""Signals app students.

Auto-provision trước đây ở đây chỉ tạo ``StudentAccount`` — thiếu ``Person`` +
``AccountPersonLink`` khiến PWA login query qua ``account_links__account`` trả
empty và HV không bao giờ pass auth (xem ``apps.students.views.login`` và
``_verify_last6_cccd``).

Sprint 3 Tuần 7 nhánh Z (2026-06-12): chuyển logic sang
``apps.orders.services._provision_student_account`` để có:
- Đầy đủ 3 model (Account + Person + Link primary).
- Trong cùng transaction convert, atomic với việc tạo Enrollment.
- Dễ test + debug hơn signal nested post_save.

File giữ lại (rỗng) để ``apps.py:ready`` import không vỡ; xóa file sẽ kéo
theo migration không liên quan.
"""
