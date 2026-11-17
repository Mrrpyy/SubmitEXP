import { describe, expect, it } from 'vitest';
import {
  earlyRate,
  formatLastSubmitted,
  formatMemberSince,
  initialFor,
  parseServerDate,
} from './services/profileFormat';

// ---------- server dates ----------

describe('parseServerDate', () => {
  it('treats dates without a timezone as utc', () => {
    expect(parseServerDate('2026-11-10T20:30:00')?.toISOString()).toBe('2026-11-10T20:30:00.000Z');
  });

  it('keeps dates that already have a timezone', () => {
    expect(parseServerDate('2026-11-10T20:30:00Z')?.toISOString()).toBe('2026-11-10T20:30:00.000Z');
    expect(parseServerDate('2026-11-10T15:30:00-05:00')?.toISOString()).toBe('2026-11-10T20:30:00.000Z');
  });

  it('returns null for empty or broken values', () => {
    expect(parseServerDate(null)).toBeNull();
    expect(parseServerDate(undefined)).toBeNull();
    expect(parseServerDate('')).toBeNull();
    expect(parseServerDate('not a date')).toBeNull();
  });
});

// ---------- member since ----------

describe('formatMemberSince', () => {
  it('shows month and year', () => {
    expect(formatMemberSince('2026-09-15T12:00:00')).toBe('Sep 2026');
  });

  it('says unknown when there is no date', () => {
    expect(formatMemberSince(null)).toBe('unknown');
  });
});

// ---------- last submitted ----------

describe('formatLastSubmitted', () => {
  const now = new Date(2026, 10, 16, 12, 0, 0);

  it('says never with no submissions', () => {
    expect(formatLastSubmitted(null, now)).toBe('never');
  });

  it('says today and yesterday', () => {
    expect(formatLastSubmitted(new Date(2026, 10, 16, 8, 0, 0).toISOString(), now)).toBe('today');
    expect(formatLastSubmitted(new Date(2026, 10, 15, 8, 0, 0).toISOString(), now)).toBe('yesterday');
  });

  it('counts days for the last week', () => {
    expect(formatLastSubmitted(new Date(2026, 10, 13, 8, 0, 0).toISOString(), now)).toBe('3 days ago');
  });

  it('shows the date for older submissions', () => {
    expect(formatLastSubmitted(new Date(2026, 9, 1, 8, 0, 0).toISOString(), now)).toBe('Oct 1, 2026');
  });

  it('treats a future date as today', () => {
    expect(formatLastSubmitted(new Date(2026, 10, 17, 8, 0, 0).toISOString(), now)).toBe('today');
  });
});

// ---------- early rate ----------

describe('earlyRate', () => {
  it('rounds to a whole percent', () => {
    expect(earlyRate(2, 3)).toBe(67);
  });

  it('is zero with no submissions', () => {
    expect(earlyRate(0, 0)).toBe(0);
  });

  it('never goes past 0 to 100', () => {
    expect(earlyRate(5, 3)).toBe(100);
    expect(earlyRate(-1, 3)).toBe(0);
  });
});

// ---------- avatar letter ----------

describe('initialFor', () => {
  it('uses the first letter in capitals', () => {
    expect(initialFor('ale_r')).toBe('A');
  });

  it('falls back to a question mark', () => {
    expect(initialFor('   ')).toBe('?');
  });
});