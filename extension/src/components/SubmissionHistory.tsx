import { useEffect, useState } from 'react';
import { getMyHistory } from '../services/api';
import type { HistoryPage, User } from '../services/api';
import { loadSession } from '../services/session';

const PAGE_SIZE = 20;

interface SubmissionHistoryProps {
    user: User;
    //lsit refreshes automatically
    refreshKey: number;
}

function formatDate(value: string | null): string {
    if (!value) return 'Not available';
    const date = new Date(/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`);
    if (Number.isNaN(date.getTime())) return 'Not available';
    return date.toLocaleString();
}

export default function SubmissionHistory({ user, refreshKey }: SubmissionHistoryProps) {
    const [data, setData] = useState<HistoryPage | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [offset, setOffset] = useState(0);
    const [reloadKey, setReloadKey] = useState(0);

    useEffect(() => {
        setOffset(0);
    }, [refreshKey]);
    
    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        setError(null);

        async function loadHistory() {
            try {
                const session = await loadSession();
                if (!session || session.user.user_id !== user.user_id) {
                    throw new Error('Your login has changed. Please sign in again.');
                }
                const result = await getMyHistory(session.token, PAGE_SIZE, offset);
                if (!cancelled) {
                    setData(result);
                }
            } catch (err) {
                if (!cancelled) {
                    setError(err instanceof Error ? err.message : 'Unable to load history');
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        }
        void loadHistory();
        return () => { cancelled = true; };
    }, [user.user_id, offset, refreshKey, reloadKey]);

    const total = data?.total ?? 0;
    const first = total === 0 ? 0 : offset + 1;
    const last = Math.min(offset + PAGE_SIZE, total);

    return (
    <section className="panel leaderboard-panel">
      <div className="leaderboard-heading">
        <h2>My History</h2>
        <button type="button" className="link" disabled={loading}
          onClick={() => setReloadKey((value) => value + 1)}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}

      {data && (
        <>
          {data.submissions.length === 0 ? (
            <p>No submissions recorded yet.</p>
          ) : (
            <>
              <p className="history-count">Showing {first}-{last} of {total}</p>
              <ul className="history-list">
                {data.submissions.map((row) => (
                  <li key={row.submission_id} className="history-entry">
                    <div className="history-entry-heading">
                      <strong>{row.assignment_title}</strong>
                      <span className="history-points">
                        {row.points_awarded !== null ? `+${row.points_awarded} EXP` : '-'}
                      </span>
                    </div>
                    <div>{row.course_name ?? 'No course'} · {row.submission_type}</div>
                    <div>Due: {formatDate(row.due_at)}</div>
                    <div>Submitted: {formatDate(row.submitted_at)}</div>
                  </li>
                ))}
              </ul>
              <div className="history-pagination">
                <button type="button" className="small-button"
                  disabled={loading || offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                  Previous
                </button>
                <button type="button" className="small-button"
                  disabled={loading || offset + PAGE_SIZE >= total}
                  onClick={() => setOffset(offset + PAGE_SIZE)}>
                  Next
                </button>
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}

