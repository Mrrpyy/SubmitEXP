import { useEffect, useState } from 'react';
import {
  checkBackendHealth,
  validateSubmissionMetadata,
} from '../services/api';

type BackendStatus = 'checking' | 'connected' | 'offline';

export default function BackendConnectionStatus() {
  const [status, setStatus] = useState<BackendStatus>('checking');
  const [message, setMessage] = useState('');
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    let active = true;
    checkBackendHealth()
      .then((ok) => {
        if (active) setStatus(ok ? 'connected' : 'offline');
      })
      .catch(() => {
        if (active) setStatus('offline');
      });
    return () => { active = false; };
  }, []);

  async function testConnection() {
    setTesting(true);
    setMessage('');
    try {
      // Synthetic example ONLY. Nothing is stored in MySQL.
      const result = await validateSubmissionMetadata({
        assignment_title: 'SubmitEXP connection test',
        course_name: 'Demo Course',
        submission_type: 'assignment',
      });
      setStatus(result.accepted ? 'connected' : 'offline');
      setMessage(result.message);
    } catch (error) {
      setStatus('offline');
      setMessage(error instanceof Error ? error.message : 'Unknown API error');
    } finally {
      setTesting(false);
    }
  }

  return (
    <section className="panel" style={{ marginTop: 12 }}>
      <h2>Backend connection</h2>
      <p aria-live="polite">API: {status}</p>
      <button type="button" onClick={testConnection} disabled={testing}>
        {testing ? 'Testing...' : 'Test API connection'}
      </button>
      {message && <p role="status">{message}</p>}
    </section>
  );
}
