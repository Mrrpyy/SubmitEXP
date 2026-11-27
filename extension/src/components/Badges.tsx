import { useEffect, useState } from 'react';
import { getMyBadges } from '../services/api';
import type { BadgeList, User } from '../services/api';
import { loadSession } from '../services/session';


interface BadgeProps {
    user: User;
    refreshKey: number;
    }

export default function Badges( {user, refreshKey }: BadgeProps) {
    const [data, setData] = useState<BadgeList | null>(null);
    const [error, setError] = useState<string | null>(null);


useEffect(() => {
    let cancelled = false;
    setError(null);

    async function load() {
        try {
            const session = await loadSession();
            if (!session || session.user.user_id !== user.user_id) {
                throw new Error('Your login has changed. Please sign in again.');
            }
            const result = await getMyBadges(session.token);
            if (!cancelled) setData(result);
        } catch (err) {
            if (!cancelled) {
                setError(err instanceof Error ? err.message : 'Unable to load');
            }
        }
    }

    void load();
    return () => { cancelled = true; };
}, [user.user_id, refreshKey]);

return (
    <section className="panel badges-panel">
      <h2>Badges</h2>

      {error && <p className="form-error" role="alert">{error}</p>}
      {!data && !error && <p role="status">Loading badges...</p>}

      {data && (
        <>
          <p>{data.earned_count} of {data.total} earned</p>
          <ul className="badge-list">
            {data.badges.map((badge) => (
              <li key={badge.id} className={badge.earned ? 'badge-item badge-earned' : 'badge-item badge-locked'}>
                <strong>{badge.earned ? '★ ' : '🔒 '}{badge.name}</strong>
                <span>{badge.description}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}