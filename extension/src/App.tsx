
import RegistrationForm from './components/RegistrationForm';
import LoginForm from './components/LoginForm';
import { useEffect, useRef, useState } from 'react';
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
import {
  clearSession,
  loadSession,
  saveSession,
} from './services/session';
import { AuthRequestGuard } from './authRequestGuard';

export default function App() {
  const [onCanvas, setOnCanvas] = useState(false);
  const [backgroundOk, setBackgroundOk] = useState(false);
  const [timesOpened, setTimesOpened] = useState(0);
  const [user, setUser] = useState<User | null>(null);

  // Prevent outdated authentication requests
  const authGuard = useRef(new AuthRequestGuard());

  // Keep session storage writes in order
  const sessionWriteQueue = useRef<Promise<void>>(
    Promise.resolve()
  );

  function queueSessionWrite(
    action: () => Promise<void>
  ): Promise<void> {
    const operation = sessionWriteQueue.current
      .catch(() => undefined)
      .then(action);

    sessionWriteQueue.current = operation;
    return operation;
  }

  // Runs once every time the popup opens
  useEffect(() => {
    async function setup() {
      const url = await getActiveTabUrl();
      setOnCanvas(isCanvasUrl(url));
      setBackgroundOk(await pingBackground());

      const count =
        ((await loadValue<number>('timesOpened')) ?? 0) + 1;

      await saveValue('timesOpened', count);
      setTimesOpened(count);
    }

    setup().catch((error) => {
      console.error('Popup setup failed:', error);
    });
  }, []);

  // Restore saved login when popup opens
  useEffect(() => {
    const requestId = authGuard.current.begin();

    async function restore() {
      const session = await loadSession();

      // Ignore outdated requests
      if (!authGuard.current.isCurrent(requestId)) {
        return;
      }

      if (!session) return;

      // Display saved user immediately
      setUser(session.user);

      try {
        const currentUser = await getCurrentUser(
          session.token
        );

        if (!authGuard.current.isCurrent(requestId)) {
          return;
        }

        setUser(currentUser);
      } catch (error) {
        if (!authGuard.current.isCurrent(requestId)) {
          return;
        }

        // Only clear session when token is invalid
        if (
          error instanceof ApiError &&
          error.status === 401
        ) {
          await queueSessionWrite(clearSession);

          if (authGuard.current.isCurrent(requestId)) {
            setUser(null);
          }
        }
      }
    }

    restore().catch((error) => {
      console.error('Restoring login failed:', error);
    });

    // Cancel outdated requests on cleanup
    return () => {
      authGuard.current.invalidate();
    };
  }, []);

  // Handle successful login
  async function handleLoggedIn(
    token: string,
    loggedInUser: User
  ) {
    const requestId = authGuard.current.begin();

    await queueSessionWrite(() =>
      saveSession({ token, user: loggedInUser })
    );

    if (!authGuard.current.isCurrent(requestId)) {
      return;
    }

    setUser(loggedInUser);
  }

  // Handle logout
  async function handleLogout() {
    // Invalidate pending authentication requests
    authGuard.current.invalidate();

    try {
      await queueSessionWrite(clearSession);
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  }

  return (
    <main className="shell">
      <div className="tag">SPRINT 1</div>

      <h1>
        Submit<span>EXP</span>
      </h1>

      <p className="motto">
        Finish early. Level up.
      </p>

      {user ? (
        <section className="panel">
          <h2>Welcome, {user.username}</h2>
          <p>Logged in as {user.email}</p>
          <button
            type="button"
            className="link"
            onClick={handleLogout}
          >
            Log out
          </button>
        </section>
      ) : (
        <LoginForm onLoggedIn={handleLoggedIn} />
      )}

      <section
        className="panel"
        style={{ marginTop: 12 }}
      >
        <h2>Status</h2>

        <ul className="status">
          <li>
            Running as extension:{' '}
            {isExtension ? 'yes' : 'no (dev preview)'}
          </li>
          <li>
            Background worker:{' '}
            {backgroundOk ? 'running' : 'not found'}
          </li>
          <li>
            Current tab is Canvas:{' '}
            {onCanvas ? 'yes' : 'no'}
          </li>
          <li>
            Popup opened: {timesOpened} times
          </li>
        </ul>

        <button
          disabled={!onCanvas || !user}
          title={
            !user
              ? 'Log in first'
              : onCanvas
                ? ''
                : 'Open a Canvas page first'
          }
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
        OCR will run locally in your browser
        to protect your screenshots.
      </small>
    </main>
  );
}
