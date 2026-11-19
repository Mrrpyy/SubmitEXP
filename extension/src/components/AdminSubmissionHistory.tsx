import { useEffect, useState } from 'react';
import { getAdminUserSubmissions } from '../services/api';
import type { AdminSubmissionPage, AdminUserRow, User } from '../services/api';
import { loadSession } from '../services/session';

const PAGE_SIZE = 20;

// The submission DATETIME values are stored as UTC without an offset.
function formatDate(value: string | null): string {
  if (!value) return 'Not recorded';
  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(value);
  const date = new Date(hasZone ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit', });
}

interface Props {
  currentUser: User;
  selectedUser: AdminUserRow;
  onClose: () => void;
}

export default function AdminSubmissionHistory({ currentUser, selectedUser, onClose }: Props) {
  const [pageIndex, setPageIndex] = useState(0);
  const [history, setHistory] = useState<AdminSubmissionPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setHistory(null);
    setError(null);

    async function fetchHistory() {
      try {
        const session = await loadSession();
        if (!session || session.user.user_id !== currentUser.user_id) {
          throw new Error('Your login has expired. Please sign in again.');
        }
        const result = await getAdminUserSubmissions(session.token, selectedUser.user_id, PAGE_SIZE,
          pageIndex * PAGE_SIZE,);
        if (!cancelled) setHistory(result);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Could not load submission history');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void fetchHistory();
    return () => { cancelled = true; };
  }, [currentUser.user_id, selectedUser.user_id, pageIndex]);

  const start = pageIndex * PAGE_SIZE;
  const count = history?.submissions.length ?? 0;

  return (
    <div className="admin-history" aria-label={`Submission history for ${selectedUser.username}`}>
      <div className="admin-title">
        <h3>Submission history: {selectedUser.username}</h3>
        <button type="button" className="link" onClick={onClose}>Close</button>
      </div>

      {loading && <p>Loading submissions...</p>}
      {error && <p className="form-error">{error}</p>}
      {!loading && !error && history && history.total === 0 && (
        <p>No submissions recorded for this user.</p>
      )}

      {!loading && !error && history && history.total > 0 && (
        <>
          <p className="history-count">
            Showing {start + 1}–{start + count} of {history.total} submissions
          </p>
          <ul className="history-list">
            {history.submissions.map((entry) => (
              <li key={entry.submission_id} className="history-entry">
                <div className="history-entry-heading">
                  <strong title={entry.assignment_title}>{entry.assignment_title}</strong>
                  <span className="history-points">
                    {entry.points_awarded === null ? 'No EXP record' : `+${entry.points_awarded} EXP`}
                  </span>
                </div>
                <div>{entry.course_name || 'Course not recorded'} · {entry.submission_type}</div>
                <div>Submitted: {formatDate(entry.submitted_at)}</div>
                <div>Due: {formatDate(entry.due_at)}</div>
                <div>Recorded: {formatDate(entry.created_at)}</div>
              </li>
            ))}
          </ul>
          <div className="history-pagination">
            <button type="button" className="small-button" disabled={pageIndex === 0}
              onClick={() => setPageIndex((index) => index - 1)}
            >
              Previous
            </button>
            <span>Page {pageIndex + 1} of {Math.ceil(history.total / PAGE_SIZE)}</span>
            <button type="button" className="small-button" disabled={start + count >= history.total}
              onClick={() => setPageIndex((index) => index + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
