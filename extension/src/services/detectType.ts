// detect tests and exams (backlog item 10)

export type SubmissionType = 'assignment' | 'quiz' | 'test' | 'exam';

export type TypeDetection = {
  type: SubmissionType;
  reason: string;
};

// words after exam or final that mean it is really a project, not a sit down exam, a number can sit in between
const NOT_AN_EXAM_AFTER = String.raw`(?!\s+(?:\d+\s+)?(?:project|paper|report|essay|presentation|draft|reflection|portfolio|proposal|corrections?|wrapper))`;

// exam, midterm, mid-term, mid term
const EXAM_WORDS = new RegExp(String.raw`\b(?:exam|exams|examination|midterm|mid-term|mid term)\b${NOT_AN_EXAM_AFTER}`, 'i');

// final only counts on a quiz page, an assignment called final is usually a project
const FINAL_WORD = new RegExp(String.raw`\bfinal\b${NOT_AN_EXAM_AFTER}`, 'i');

// test but not test cases, test plan and other coding assignment names
const TEST_WORDS = /\b(?:test|tests)\b(?!\s+(?:case|cases|plan|plans|suite|suites|report|driven|bank))/i;

// practice and review versions are low stakes, they stay a quiz or assignment
const PRACTICE_WORDS = /\b(?:practice|sample|mock|review|study guide)\b/i;

// text canvas only shows on quiz style pages
const QUIZ_PAGE_SIGNS = [
  /time limit/i,
  /quizzes\s*[>»›]/i,
  /attempt history/i,
  /allowed attempts/i,
  /take the quiz/i,
  /quiz instructions/i,
];

// proctoring tools are almost only used for tests and exams
const PROCTORED = /\b(?:lockdown browser|respondus|honorlock|proctorio|proctoru|proctored)\b/i;

export function isQuizPage(ocrText: string): boolean {
  return QUIZ_PAGE_SIGNS.some((sign) => sign.test(ocrText));
}

// gives back the word that matched so the popup can explain the choice
function matchedWord(pattern: RegExp, text: string): string | null {
  const match = text.match(pattern);
  return match ? match[0] : null;
}

// title decides first, page text only helps when the title has no clue
export function detectSubmissionType(title: string | null, ocrText: string): TypeDetection {
  const quizPage = isQuizPage(ocrText);
  const proctored = PROCTORED.test(ocrText);
  const name = title ?? '';
  const fallback: SubmissionType = quizPage ? 'quiz' : 'assignment';

  // practice exam or test review stays low stakes
  const practice = matchedWord(PRACTICE_WORDS, name);
  if (practice && (EXAM_WORDS.test(name) || TEST_WORDS.test(name) || FINAL_WORD.test(name))) {
    return { type: fallback, reason: `title says "${practice}", so it is not graded as a real test or exam` };
  }

  const examWord = matchedWord(EXAM_WORDS, name);
  if (examWord) {
    return { type: 'exam', reason: `title contains "${examWord}"` };
  }

  const finalWord = matchedWord(FINAL_WORD, name);
  if (finalWord && (quizPage || proctored)) {
    return { type: 'exam', reason: `title contains "${finalWord}" on a quiz page` };
  }

  const testWord = matchedWord(TEST_WORDS, name);
  if (testWord) {
    return { type: 'test', reason: `title contains "${testWord}"` };
  }

  // no clue in the title but it needs a lockdown browser or proctor
  if (quizPage && proctored) {
    return { type: 'test', reason: 'quiz page uses a proctoring tool' };
  }

  if (quizPage) {
    return { type: 'quiz', reason: 'page has canvas quiz details' };
  }

  return { type: 'assignment', reason: 'no test or exam words found' };
}