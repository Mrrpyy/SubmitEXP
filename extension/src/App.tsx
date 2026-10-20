import RegistrationForm from './components/RegistrationForm';
import LoginForm from './components/LoginForm';
import { useEffect, useState } from 'react';
import BackendConnectionStatus from './components/BackendConnectionStatus';
import { ApiError, getCurrentUser } from './services/api';
import type { User } from './services/api';
import {
  getActiveTabUrl,
  isCanvasUrl,
  isExtension,
  loadValue,
  pingBackground,
  saveValue,
} from './services/chromeHelpers';
import { clearSession, loadSession, saveSession } from './services/session';


export default function App() {
  const [onCanvas, setOnCanvas] = useState(false);
  const [backgroundOk, setBackgroundOk] = useState(false);
  const [timesOpened, setTimesOpened] = useState(0);
  const [user, setUser] = useState<User | null>(null);


  // Runs once every time the popup opens
  useEffect(() => {
    async function setup() {
      const url = await getActiveTabUrl();
      setOnCanvas(isCanvasUrl(url));
      setBackgroundOk(await pingBackground());

      // Proves storage works across popup sessions
      const count =
        ((await loadValue<number>('timesOpened')) ?? 0) + 1;

      await saveValue('timesOpened', count);
      setTimesOpened(count);
    }

    setup().catch((error) => {
      console.error('Popup setup failed:', error);
    });
  }, []);

  // Restore the saved login when the popup opens
  useEffect(() => {
    async function restore() {
      const session = await loadSession();
      if (!session) return;
      setUser(session.user); // show it right away
      try {
        setUser(await getCurrentUser(session.token)); // make sure the token still works
      } catch (error) {
        // Only a 401 means the login is really over
        if (error instanceof ApiError && error.status === 401) {
          await clearSession();
          setUser(null);
        }
      }
    }

    restore().catch((error) => {
      console.error('Restoring login failed:', error);
    });
  }, []);

  async function handleLoggedIn(token: string, loggedInUser: User) {
    await saveSession({ token, user: loggedInUser });
    setUser(loggedInUser);
  }

  async function handleLogout() {
    await clearSession();
    setUser(null);
  }

  return (
    <main className="shell">
      <div className="tag">SPRINT 1</div>

      <h1>
        Submit<span>EXP</span>
      </h1>

      <p className="motto">Finish early. Level up.</p>

            {user ? (
        <section className="panel">
          <h2>Welcome, {user.username}</h2>
          <p>Logged in as {user.email}</p>
          <button type="button" className="link" onClick={handleLogout}>
            Log out
          </button>
        </section>
      ) : (
        <LoginForm onLoggedIn={handleLoggedIn} />
      )}

      <section className="panel" style={{ marginTop: 12 }}>
        <h2>Status</h2>

        <ul className="status">
          <li>
            Running as extension: {isExtension ? 'yes' : 'no (dev preview)'}
          </li>
          <li>
            Background worker: {backgroundOk ? 'running' : 'not found'}
          </li>
          <li>
            Current tab is Canvas: {onCanvas ? 'yes' : 'no'}
          </li>
          <li>
            Popup opened: {timesOpened} times
          </li>
        </ul>

        <button
          disabled={!onCanvas || !user}
          title={!user ? 'Log in first' : onCanvas ? '' : 'Open a Canvas page first'}
        >
          Check Submission
        </button>
      </section>

      <BackendConnectionStatus />
      {!user && <RegistrationForm />}

      <small>
        Screenshot capture comes in a later item.
      </small>
      <small>
        OCR will run locally in your browser to protect your screenshots.
      </small>
    </main>
  );
}
