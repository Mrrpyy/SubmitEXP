import { describe, expect, it } from 'vitest';
import type { AdminUserRow } from './services/api';
import { canChangeRole, filterUsers, otherRole, replaceUser } from './services/adminFilters';

// setup

const ROWS: AdminUserRow[] = [
  { user_id: 1, username: 'admin_user', email: 'admin@example.com', role: 'admin', total_points: 0 },
  { user_id: 2, username: 'Miguel_G', email: 'miguel@ufl.edu', role: 'student', total_points: 120 },
  { user_id: 3, username: 'brian_t', email: 'brian@ufl.edu', role: 'student', total_points: 75 },];

//filtering

describe('filterUsers', () => {
  it('returns everyone with no search and all roles', () => {
    expect(filterUsers(ROWS, '', 'all')).toHaveLength(3);
  });

  it('matches username with any capitals', () => {
    expect(filterUsers(ROWS, 'miguel', 'all').map((row) => row.user_id)).toEqual([2]);
  });

  it('matches email', () => {
    expect(filterUsers(ROWS, 'ufl.edu', 'all').map((row) => row.user_id)).toEqual([2, 3]);
  });

  it('ignores spaces around the search', () => {
    expect(filterUsers(ROWS, '  brian  ', 'all').map((row) => row.user_id)).toEqual([3]);
  });

  it('filters by role', () => {
    expect(filterUsers(ROWS, '', 'admin').map((row) => row.user_id)).toEqual([1]);
    expect(filterUsers(ROWS, '', 'student').map((row) => row.user_id)).toEqual([2, 3]);
  });

  it('combines search and role', () => {
    expect(filterUsers(ROWS, 'admin', 'student')).toEqual([]);
  });

  it('does not change the original list', () => {
    filterUsers(ROWS, 'brian', 'student');
    expect(ROWS).toHaveLength(3);
  });
});

//updating a row

describe('replaceUser', () => {
  it('swaps only the matching row', () => {
    const updated = { ...ROWS[1], role: 'admin' as const };
    const result = replaceUser(ROWS, updated);
    expect(result[1].role).toBe('admin');
    expect(result[0]).toBe(ROWS[0]);
    expect(result[2]).toBe(ROWS[2]);
  });

  it('leaves the list alone for an unknown user', () => {
    const stranger = { ...ROWS[0], user_id: 99 };
    expect(replaceUser(ROWS, stranger)).toEqual(ROWS);
  });
});

//role buttons

describe('otherRole', () => {
  it('flips between student and admin', () => {
    expect(otherRole('student')).toBe('admin');
    expect(otherRole('admin')).toBe('student');
  });
});

describe('canChangeRole', () => {
  it('blocks the logged in admin from changing themselves', () => {
    expect(canChangeRole(ROWS[0], 1)).toBe(false);
    expect(canChangeRole(ROWS[1], 1)).toBe(true);
  });
});