//profile display helpers

const DAY_MS = 24 * 60 * 60 * 1000;

// the backend stores utc without a timezone, so add one before parsing
export function parseServerDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(value);
  const date = new Date(hasZone ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

// shows something like Sep 2026
export function formatMemberSince(value: string | null | undefined): string {
  const date = parseServerDate(value);
  if (!date) return 'unknown';
  return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

// today, yesterday, a few days ago, or the date for older ones
export function formatLastSubmitted(value: string | null | undefined, now: Date = new Date()): string {
  const date = parseServerDate(value);
  if (!date) return 'never';
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfThatDay = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const daysAgo = Math.round((startOfToday - startOfThatDay) / DAY_MS);
  if (daysAgo < 0) {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric', });
  }
  if (daysAgo === 0) return 'today';
  if (daysAgo === 1) return 'yesterday';
  if (daysAgo < 7) return `${daysAgo} days ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// percent of submissions turned in before the due date
export function earlyRate(early: number, total: number): number {
  if (total <= 0) return 0;
  const rate = Math.round((early / total) * 100);
  return Math.min(100, Math.max(0, rate));
}

// first letter for the avatar circle
export function initialFor(username: string): string {
  const letter = username.trim().charAt(0);
  return letter ? letter.toUpperCase() : '?';
}
