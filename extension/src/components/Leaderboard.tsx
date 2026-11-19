import { useEffect, useState } from 'react';
import { getLeaderboard } from '../services/api';
import type { LeaderboardResponse, User } from '../services/api';
import { loadSession } from '../services/session';
interface LeaderboardProps {
  user: User;
// Changes after recording EXP, so the leaderboard refreshes automatically.
  refreshKey: number;
}
export default function Leaderboard({ user, refreshKey }: LeaderboardProps) {
  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setData(null);
    setLoading(true);
    setError(null);
    async function load() {
      try {
        const session = await loadSession();
        if (!session || session.user.user_id !== user.user_id) {
          throw new Error('Your login has changed. Please sign in again.');
        }
        const result = await getLeaderboard(session.token);
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unable to load leaderboard');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [user.user_id, refreshKey, reloadKey]);
  return (
    <section className="panel leaderboard-panel">
      <div className="leaderboard-heading">
        <h2>Leaderboard</h2>
        <button type="button" className="link" disabled={loading} onClick={() => setReloadKey((value) => value + 1)} >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>
      <p>Top 10 students by total EXP</p>

      {loading && <p role="status">Loading leaderboard...</p>}
      {error && <p className="form-error" role="alert">{error}</p>}

      {data && (
        <>
          {data.leaders.length === 0 ? (
            <p>No students on the leaderboard yet.</p>
          ) : (
            <ol className="leaderboard-list" aria-label="Top students">
              {data.leaders.map((entry) => (
                <li key={entry.user_id} className={entry.user_id === user.user_id ? 'leaderboard-row leaderboard-self' : 'leaderboard-row'}>
                  <span className="leaderboard-rank">#{entry.rank}</span>
                  <div className="leaderboard-user">
                    <strong>{entry.username}{entry.user_id === user.user_id ? ' (you)' : ''}</strong>
                    <span>Level {entry.current_level} · {entry.submissions_recorded} submissions</span>
                  </div>
                  <strong className="leaderboard-exp">{entry.total_points} EXP</strong>
                </li>
              ))}
            </ol>
          )}

          {user.role === 'student' && data.your_rank !== null && (
            <p className="leaderboard-standing">
              Your rank: <strong>#{data.your_rank}</strong> of {data.total_students} students
              {' · '}{data.your_total_points ?? 0} EXP
            </p>
          )}
          {user.role === 'admin' && <small>Admin accounts are excluded from student rankings.</small>}
        </>
      )}
    </section>
  );
}
