import type { AdminUserRow, UserRole } from './api';

// ---------- admin list helpers ----------

export type RoleFilter = 'all' | UserRole;

// search matches username or email, any capitals
export function filterUsers(rows: AdminUserRow[], search: string, role: RoleFilter): AdminUserRow[] {
  const needle = search.trim().toLowerCase();
  return rows.filter((row) => {
    if (role !== 'all' && row.role !== role) return false;
    if (!needle) return true;
    return row.username.toLowerCase().includes(needle) || row.email.toLowerCase().includes(needle);
  });
}

// swaps in the updated row without touching the others
export function replaceUser(rows: AdminUserRow[], updated: AdminUserRow): AdminUserRow[] {
  return rows.map((row) => (row.user_id === updated.user_id ? updated : row));
}

// the role a button would switch someone to
export function otherRole(role: UserRole): UserRole {
  return role === 'admin' ? 'student' : 'admin';
}

// an admin cannot change their own role, the backend blocks it too
export function canChangeRole(row: AdminUserRow, currentUserId: number): boolean {
  return row.user_id !== currentUserId;
}