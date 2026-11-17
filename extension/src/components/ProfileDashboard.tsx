import { useEffect, useState } from 'react';
import { getProfile } from '../services/api';
import type { Profile, User } from '../services/api';
import { loadSession } from '../services/session';
import {
  earlyRate,
  formatLastSubmitted,
  formatMemberSince,
  initialFor,
} from '../services/profileFormat';

// user profile and dashboard (backlog item 15)

interface ProfileDashboardProps {
  user: User;
  onLogout: () => void;
  // changes after exp is recorded so the numbers reload
  refreshKey: number;
}

export default function ProfileDashboard({ user, onLogout, refreshKey }: ProfileDashboardProps) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ---------- load profile ----------

  useEffect(() => {
    let cancelled = false;
    setProfile(null);
    setError(null);


    async function fetchProfile() {
      try {
        const session = await loadSession();
        // stops a stale login from loading someone else
        if (!session || session.user.user_id !== user.user_id) return;
        const result = await getProfile(session.token);
        if (!cancelled) setProfile(result);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Unable to load profile');
      }
    }

    void fetchProfile();
    return () => {
      cancelled = true;
    };
  }, [user.user_id, user.role, refreshKey]);

  const stats = profile?.user_id === user.user_id? profile.stats: null;

  // ---------- account card ----------

  return (
    <section className="panel profile-panel">
      <div className="profile-header">
        <div className="avatar" aria-hidden="true">
          {initialFor(user.username)}
        </div>
        <div className="profile-name">
          <h2>{user.username}</h2>
          <p>{user.email}</p>
        </div>
        <span className={`role-badge role-${user.role}`}>{user.role}</span>
      </div>

      <small className="member-since">
        Member since {profile && profile.user_id === user.user_id? formatMemberSince(profile.member_since) : '...'}
      </small>

      {error && <p className="form-error">{error}</p>}

      {/* ---------- student stats ---------- */}
      {stats && (
        <>
          <div className="stat-grid">
            <div className="stat">
              <strong>{stats.submissions_recorded}</strong>
              <span>Submissions</span>
            </div>
            <div className="stat">
              <strong>{earlyRate(stats.early_submissions, stats.submissions_recorded)}%</strong>
              <span>Turned in early</span>
            </div>
            <div className="stat">
              <strong>{stats.best_award}</strong>
              <span>Best EXP</span>
            </div>
            <div className="stat">
              <strong>{stats.average_award}</strong>
              <span>Avg EXP</span>
            </div>
          </div>
          <small>Last submission: {formatLastSubmitted(stats.last_submitted_at)}</small>
        </>
      )}

      <button type="button" className="link" onClick={onLogout}>
        Log out
      </button>
    </section>
  );
}
