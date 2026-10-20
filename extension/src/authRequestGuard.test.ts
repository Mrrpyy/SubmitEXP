import { describe, it, expect } from 'vitest';
import { AuthRequestGuard } from './authRequestGuard';

describe('AuthRequestGuard', () => {
  it('accepts the current request', () => {
    const guard = new AuthRequestGuard();
    const requestId = guard.begin();

    expect(guard.isCurrent(requestId)).toBe(true);
  });

  it('rejects requests after logout', () => {
    const guard = new AuthRequestGuard();
    const requestId = guard.begin();

    guard.invalidate();

    expect(guard.isCurrent(requestId)).toBe(false);
  });

  it('rejects outdated requests', () => {
    const guard = new AuthRequestGuard();

    const firstRequest = guard.begin();
    const secondRequest = guard.begin();

    expect(guard.isCurrent(firstRequest)).toBe(false);
    expect(guard.isCurrent(secondRequest)).toBe(true);
  });
});
