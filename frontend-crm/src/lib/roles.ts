/**
 * Group keys khớp Django Group.name (xem apps/users/management/commands/bootstrap_data.py).
 * Khi BE đổi tên group, chỉ sửa ở đây.
 */
export const ROLES = {
  ADMIN: 'admin',
  SALE: 'sale',
  ACCOUNTANT: 'accountant',
  CLERK: 'clerk',
} as const

export type Role = (typeof ROLES)[keyof typeof ROLES]
