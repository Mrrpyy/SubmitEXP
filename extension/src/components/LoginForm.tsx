import { useState } from 'react';
import type { FormEvent } from 'react';
import { loginUser } from '../services/api';
import type { User } from '../services/api';

type Props = {
  onLoggedIn: (token: string, user: User) => void | Promise<void>;
};

export default function LoginForm({ onLoggedIn }: Props) {
  const [identifier, setIdentifier] = useState(''); // username or email
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await loginUser(identifier.trim(), password);
      await onLoggedIn(result.access_token, result.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel login-panel">
      <h2>Log In</h2>

      <form onSubmit={handleSubmit}>
        <label htmlFor="login-identifier">Username or email</label>
        <input
          id="login-identifier"
          type="text"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          autoComplete="username"
          required
        />

        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />

        <button type="submit" disabled={loading}>
          {loading ? 'Logging in...' : 'Log In'}
        </button>
      </form>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}