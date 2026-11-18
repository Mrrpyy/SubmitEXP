import { useEffect, useState } from 'react';
import AdminSubmissionHistory from './AdminSubmissionHistory';
import { changeUserRole, getAdminStats, listUsers } from '../services/api';
import type { AdminStats, AdminUserRow, User } from '../services/api';
import { loadSession } from '../services/session';
import { canChangeRole, filterUsers, otherRole, replaceUser } from '../services/adminFilters';
import type { RoleFilter } from '../services/adminFilters';

// administrator interface (backlog item 18)

interface AdminPanelProps {
  currentUser: User;
}

export default function AdminPanel({ currentUser }: AdminPanelProps) {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all');
  // the row waiting on a confirm click
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [historyUser, setHistoryUser] = useState<AdminUserRow | null>(null);

  // ---------- loading ----------

  async function getToken(): Promise<string> {
    const session = await loadSession();
    if (!session || session.user.user_id !== currentUser.user_id) {
      throw new Error('Your login has expired. Please sign in again.');
    }
    return session.token;
  }

  async function loadAll() {
    setHistoryUser(null);
    setLoading(true);
    setError(null);
    setStats(null);
    setUsers([]);
    try {
      const token = await getToken();
      const [statsResult, usersResult] = await Promise.all([getAdminStats(token), listUsers(token)]);
      setStats(statsResult);
      setUsers(usersResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load admin data');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAll();
  }, [currentUser.user_id]);

  // ---------- role changes ----------

  async function confirmRoleChange(row: AdminUserRow) {
    const newRole = otherRole(row.role);
    setSavingId(row.user_id);
    setError(null);
    setNotice(null);
    try {
      const token = await getToken();
      const updated = await changeUserRole(token, row.user_id, newRole);
      setUsers((current) => replaceUser(current, updated));
      setNotice(
        `${updated.username} is now ${updated.role === 'admin' ? 'an admin' : 'a student'}.`
      );
      try {
        setStats(await getAdminStats(token));
      } catch {
        setError(
          'Role updated, but statistics could not refresh. Click Refresh to retry.'
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not change role');
    } finally {
      setSavingId(null);
      setPendingId(null);
    }
  }

  const shown = filterUsers(users, search, roleFilter);

  // ---------- app totals ----------

  return (
    <section className="panel admin-panel">
      <div className="admin-title">
        <h2>Admin</h2>
        <button type="button" className="link" onClick={() => void loadAll()} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {stats && (
        <div className="stat-grid admin-stats">
          <div className="stat">
            <strong>{stats.total_users}</strong>
            <span>Users</span>
          </div>
          <div className="stat">
            <strong>{stats.total_submissions}</strong>
            <span>Submissions</span>
          </div>
          <div className="stat">
            <strong>{stats.students}</strong>
            <span>Students</span>
          </div>
          <div className="stat">
            <strong>{stats.admins}</strong>
            <span>Admins</span>
          </div>
          <div className="stat stat-wide">
            <strong>{stats.total_points_awarded}</strong>
            <span>Total EXP awarded</span>
          </div>
        </div>
      )}

      {/* ---------- search and filter ---------- */}
      <div className="admin-filters">
        <input
          type="search"
          placeholder="Search name or email"
          aria-label="Search users"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select
          aria-label="Filter by role"
          value={roleFilter}
          onChange={(event) => setRoleFilter(event.target.value as RoleFilter)}
        >
          <option value="all">All</option>
          <option value="student">Students</option>
          <option value="admin">Admins</option>
        </select>
      </div>

      {error && <p className="form-error">{error}</p>}
      {notice && <p className="form-success">{notice}</p>}

      {/* ---------- user list ---------- */}
      <ul className="admin-list">
        {shown.map((row) => (
          <li key={row.user_id} className="admin-row">
            <div className="admin-user">
              <strong>
                {row.username}
                {row.user_id === currentUser.user_id && <em> (you)</em>}
              </strong>
              <span>{row.email}</span>
              <span>
                <span className={`role-badge role-${row.role}`}>{row.role}</span> {row.total_points} EXP
              </span>
            </div>

            <div className="admin-actions">
              <button
                type="button"
                className="small-button"
                onClick={() => {
                  setHistoryUser((previous) => previous?.user_id === row.user_id ? null : row);
                }}
                aria-expanded={historyUser?.user_id === row.user_id}
              >
                {historyUser?.user_id === row.user_id ? 'Hide history' : 'History'}
              </button>
              {canChangeRole(row, currentUser.user_id) && (
                pendingId === row.user_id ? (
                  <>
                    <button
                      type="button"
                      className="small-button confirm"
                      disabled={savingId !== null}
                      onClick={() => void confirmRoleChange(row)}
                    >
                      {savingId === row.user_id ? 'Saving...' : 'Confirm'}
                    </button>
                    <button
                      type="button"
                      className="small-button"
                      disabled={savingId !== null}
                      onClick={() => setPendingId(null)}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    className="small-button"
                    disabled={savingId !== null}
                    onClick={() => setPendingId(row.user_id)}
                  >
                    Make {otherRole(row.role)}
                  </button>
                )
              )}
            </div>
          </li>
        ))}
      </ul>

      {!loading && shown.length === 0 && <p>No users match.</p>}

      {historyUser && (
        <AdminSubmissionHistory
          key={`${currentUser.user_id}:${historyUser.user_id}`}
          currentUser={currentUser}
          selectedUser={historyUser}
          onClose={() => setHistoryUser(null)}
        />
      )}
    </section>
  );
}
