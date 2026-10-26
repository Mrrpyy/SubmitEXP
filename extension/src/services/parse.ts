import { detectSubmissionType } from './detectType';
import type { SubmissionType } from './detectType';

// other files still import the type from here
export type { SubmissionType } from './detectType';

export type ParsedSubmission = {
  title: string | null;
  type: SubmissionType;
// why it was picked as a test, exam, quiz or assignment
  typeReason: string;
  dueAt: string | null;
  submittedAt: string | null;
  missing: string[];
};

const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
const DATE_PART = String.raw`(?:[a-z]{3,9},?\s+)?([a-z]{3,9})\s+(\d{1,2})(?:,?\s+(\d{4}))?,?\s*(?:at\s+)?(\d{1,2})[:.](\d{2})\s*([ap]m)\b`;
const DUE = new RegExp(String.raw`\bdue(?:\s+date)?\s*:?\s*${DATE_PART}`, 'i');
const SUBMITTED = new RegExp(
  String.raw`\b(?:submitted|submited|sumitted)(?:\s+(?:on|at))?\s*[:!]?\s*${DATE_PART}`,
  'i'
);

function dateFromMatch(match: RegExpMatchArray | null, fallbackYear?: number): string | null {
  if (!match) return null;

  const [, monthText, dayText, yearText, hourText, minuteText, meridiem] = match;
  const month = MONTHS.indexOf(monthText.slice(0, 3).toLowerCase());
  const year = yearText ? Number(yearText) : fallbackYear;
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);

  if (month < 0 || year === undefined || year < 1000 || year > 9999 ||
      hour < 1 || hour > 12 || minute > 59) return null;

  const valid = new Date(Date.UTC(year, month, day));
  if (valid.getUTCFullYear() !== year || valid.getUTCMonth() !== month ||
      valid.getUTCDate() !== day) return null;

  const hour24 = (hour % 12) + (meridiem.toLowerCase() === 'pm' ? 12 : 0);
  const pad = (n: number) => String(n).padStart(2, '0');

  return `${year}-${pad(month + 1)}-${pad(day)} ${pad(hour24)}:${pad(minute)}:00`;
}

function findTitle(lines: string[]): string | null {
  for (const line of lines) {
    const breadcrumb = line.match(/(?:assignments|quizzes)\s*[>»›]\s*(.+)$/i);

    if (breadcrumb) {
      const title = breadcrumb[1].replace(/\s*immersive reader.*$/i, '').trim();
      if (title) return title;
    }

    const label = line.match(/^(?:assignment (?:name|title)|title)\s*:\s*(.+)$/i);
    if (label) return label[1].trim();
  }

  const dueIndex = lines.findIndex((line) => /^due(?:\s|:)/i.test(line));

  for (let i = dueIndex - 1; dueIndex >= 0 && i >= Math.max(0, dueIndex - 3); i--) {
    const line = lines[i];

    if (/^(?:assignments?|quizzes?|modules?|grades?|home|dashboard|points?|submission details|immersive reader)$/i.test(line)) continue;
    if (/^(?:available|due|submitted|points?)\s*:/i.test(line)) continue;

    if (line.length >= 3 && line.length <= 120) return line;
  }

  return null;
}

function nearbyYear(
  match: RegExpMatchArray | null,
  other: RegExpMatchArray | null
): number | undefined {
  if (!match || !other?.[3]) return undefined;

  const firstMonth = MONTHS.indexOf(match[1].slice(0, 3).toLowerCase());
  const otherMonth = MONTHS.indexOf(other[1].slice(0, 3).toLowerCase());

  if (firstMonth < 0 || otherMonth < 0 ||
      Math.abs(firstMonth - otherMonth) > 2) return undefined;

  return Number(other[3]);
}

export function parseSubmission(
  ocrText: string,
  contextYear?: number
): ParsedSubmission {
  const lines = ocrText.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const title = findTitle(lines);

  const dueMatch = ocrText.match(DUE);
  const submittedMatch = ocrText.match(SUBMITTED);

  const dueAt = dateFromMatch(
    dueMatch,
    contextYear ?? nearbyYear(dueMatch, submittedMatch)
  );

  const submittedAt = dateFromMatch(
    submittedMatch,
    contextYear ?? nearbyYear(submittedMatch, dueMatch)
  );

// tests and exams are detected in detectType.ts
  const { type, reason: typeReason } = detectSubmissionType(title, ocrText);

  const missing: string[] = [];
  if (!title) missing.push('title');

  if (type === 'assignment') {
    if (!dueAt) missing.push('dueAt');
    if (!submittedAt) missing.push('submittedAt');
  } else if (!/submission details/i.test(ocrText)) {
    missing.push('submission');
  }

  return { title, type, typeReason, dueAt, submittedAt, missing };
}