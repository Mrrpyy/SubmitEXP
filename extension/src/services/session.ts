import type { User } from './api';
import { loadValue, saveValue } from './chromeHelpers';

// The saved login. It lives in chrome.storage, so it survives closing the popup.
// Logging out is just deleting it, the server keeps no sessions.
export type Session = { token: string; user: User };

export function loadSession(): Promise<Session | null | undefined> {
  return loadValue<Session | null>('session');
}

export function saveSession(session: Session): Promise<void> {
  return saveValue('session', session);
}

export function clearSession(): Promise<void> {
  return saveValue('session', null);
}