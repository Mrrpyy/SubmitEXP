import { describe, it, expect } from 'vitest';
import { parseSubmission } from './services/parse';

describe('Canvas assignment parsing', () => {
  it('extracts assignment details', () => {
    const text = `
      Assignments > Homework 1
      Due: Oct 20, 2026 at 11:59 PM
      Submitted on Oct 19, 2026 at 3:30 PM
    `;

    const result = parseSubmission(text);

    expect(result.title).toBe('Homework 1');
    expect(result.type).toBe('assignment');
    expect(result.dueAt).toBe('2026-10-20 23:59:00');
    expect(result.submittedAt).toBe('2026-10-19 15:30:00');
    expect(result.missing).toEqual([]);
  });

  it('recognizes weekday prefixes', () => {
    const text = `
      Assignments > Lab 2
      Due: Tue, Oct 20, 2026 at 11:59 PM
      Submitted Oct 19, 2026 at 3:30 PM
    `;

    const result = parseSubmission(text);

    expect(result.dueAt).toBe('2026-10-20 23:59:00');
    expect(result.submittedAt).toBe('2026-10-19 15:30:00');
  });

  it('uses a supplied year when dates omit it', () => {
    const text = `
      Assignments > Homework 2
      Due: Oct 20 at 11:59 PM
      Submitted Oct 19 at 3:30 PM
    `;

    const result = parseSubmission(text, 2026);

    expect(result.dueAt).toBe('2026-10-20 23:59:00');
    expect(result.submittedAt).toBe('2026-10-19 15:30:00');
  });

  it('does not invent a year', () => {
    const result = parseSubmission(
      'Assignments > Homework 2\nDue: Oct 20 at 11:59 PM'
    );

    expect(result.dueAt).toBeNull();
    expect(result.missing).toContain('dueAt');
  });

  it('rejects invalid dates', () => {
    const text = `
      Assignments > Homework 3
      Due: Oct 32, 2026 at 11:59 PM
      Submitted Oct 19, 2026 at 3:30 PM
    `;

    const result = parseSubmission(text);

    expect(result.dueAt).toBeNull();
    expect(result.missing).toContain('dueAt');
  });

  it('uses the heading when breadcrumbs are missing', () => {
    const text = `
      Home
      Assignments
      Lab 7: Reflection
      Due: Oct 20, 2026 at 11:59 PM
    `;

    const result = parseSubmission(text);

    expect(result.title).toBe('Lab 7: Reflection');
  });

  it('reports missing submission information', () => {
    const result = parseSubmission(
      'Assignments > Homework 4\nDue: Oct 20, 2026 at 11:59 PM'
    );

    expect(result.missing).toContain('submittedAt');
  });

  it('preserves quiz classification', () => {
    const result = parseSubmission(
      'Quizzes > Weekly Quiz\nTime Limit: 20 Minutes'
    );

    expect(result.type).toBe('quiz');
    expect(result.missing).toContain('submission');
  });
});
