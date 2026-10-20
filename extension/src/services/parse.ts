export type SubmissionType = 'assignment' | 'quiz' | 'test' | 'exam';

export type ParsedSubmission = {
  title: string | null;
  type: SubmissionType;
  dueAt: string | null; 
  submittedAt: string | null;
  missing: string[]; // things the user needs to fill in, this is helpful so that the student can see what is missing
};

const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];

// both have two different fromats, one with a year and one without so I made sure it reads both. 
const DUE = /due:?\s+(?:[a-z]{3}\s+)?([a-z]{3,9})\s+(\d{1,2})(?:,?\s+(\d{4}))?,?\s*(?:at)?\s*(\d{1,2})[:.](\d{2})\s*([ap]m)/i;
const SUBMITTED = /submitted(?:\s+on)?:?\s+([a-z]{3,9})\s+(\d{1,2}),?\s+(\d{4}),?\s*(?:at)?\s*(\d{1,2})[:.](\d{2})\s*([ap]m)/i;

function toDateTime(m: RegExpMatchArray): string | null {

  const [, monthText, day, year, hour, minute, ampm] = m;
  const month = MONTHS.indexOf(monthText.slice(0, 3).toLowerCase());
  if (month === -1) return null;
  let h = Number(hour) % 12;
  if (ampm.toLowerCase() === 'pm') h += 12;
  const pad = (n: number) => String(n).padStart(2, '0');
  const y = year ?? new Date().getFullYear();
  return `${y}-${pad(month + 1)}-${pad(Number(day))} ${pad(h)}:${minute}:00`;
}

// The title on the canvas page is shown mostly twice, once in a breadcrumb and once as the big heading. So first it checks the breadcru and then the heading
function findTitle(lines: string[]): string | null {
  for (const line of lines) {
    const m = line.match(/(?:assignments|quizzes)\s*[>»›]\s*(.+)$/i);
    // since the breadcrumb is in the same line as the immersive reader link, the ocr sometimes reads the link, so we remove it if it shows up
    if (m) return m[1].replace(/\s*(?:[^\w\s]+\s+)?immersive reader.*$/i, '').trim();
  }
  // back up plan if the breadcrumb is not found we use the big header
  const i = lines.findIndex((l) => /\bdue\b/i.test(l));
  return i > 0 ? lines[i - 1] : null;
}

export function parseSubmission(ocrText: string): ParsedSubmission {
  const lines = ocrText.split('\n').map((l) => l.trim()).filter(Boolean);

  const title = findTitle(lines);

  const dueMatch = ocrText.match(DUE);
  const submittedMatch = ocrText.match(SUBMITTED);
  const dueAt = dueMatch ? toDateTime(dueMatch) : null;
  const submittedAt = submittedMatch ? toDateTime(submittedMatch) : null;

  //exams need exam or midterm in the title. Quizzes can be indentified by the time limit or breadcrumb title. Everything else is an assignment.
  const isQuizPage = /time limit/i.test(ocrText) || /quizzes\s*[>»›]/i.test(ocrText);
  let type: SubmissionType = 'assignment';
  if (title && /\b(exam|midterm)\b/i.test(title)) type = 'exam';
  else if (isQuizPage && title && /\btest\b/i.test(title)) type = 'test';
  else if (isQuizPage) type = 'quiz';

  const missing: string[] = [];
  if (!title) missing.push('title');
  if (type === 'assignment') {
    if (!dueAt) missing.push('dueAt');
    if (!submittedAt) missing.push('submittedAt');
  } else if (!/submission details/i.test(ocrText)) {
    missing.push('submission'); // quiz page with no sign it was actually taken
  }

  return { title, type, dueAt, submittedAt, missing };
}