import { describe, it, expect } from 'vitest';
import { detectSubmissionType } from './services/detectType';
import { parseSubmission } from './services/parse';

// text a canvas quiz page shows, used to fake a quiz page
const QUIZ_PAGE = 'Quiz Instructions\nTime Limit: 50 Minutes\nAllowed Attempts: 1';
const ASSIGNMENT_PAGE = 'Due: Oct 20, 2026 at 11:59 PM\nPoints 10';

describe('test and exam detection', () => {
  it('finds exams from the title', () => {
    expect(detectSubmissionType('Exam 1', QUIZ_PAGE).type).toBe('exam');
    expect(detectSubmissionType('Midterm Exam', QUIZ_PAGE).type).toBe('exam');
    expect(detectSubmissionType('Mid-Term 2', QUIZ_PAGE).type).toBe('exam');
  });

  it('finds an exam even on an assignment page, like a take home exam', () => {
    expect(detectSubmissionType('Take Home Exam 2', ASSIGNMENT_PAGE).type).toBe('exam');
  });

  it('finds tests from the title', () => {
    expect(detectSubmissionType('Chapter 3 Test', QUIZ_PAGE).type).toBe('test');
    expect(detectSubmissionType('Unit 2 Test', ASSIGNMENT_PAGE).type).toBe('test');
  });

  it('treats final as an exam only on a quiz page', () => {
    expect(detectSubmissionType('Final', QUIZ_PAGE).type).toBe('exam');
    expect(detectSubmissionType('Final', ASSIGNMENT_PAGE).type).toBe('assignment');
  });

  it('does not count projects and papers as exams', () => {
    expect(detectSubmissionType('Final Project', QUIZ_PAGE).type).toBe('quiz');
    expect(detectSubmissionType('Midterm Project', ASSIGNMENT_PAGE).type).toBe('assignment');
    expect(detectSubmissionType('Exam 1 Corrections', ASSIGNMENT_PAGE).type).toBe('assignment');
  });

  it('does not count coding assignments about testing', () => {
    expect(detectSubmissionType('Write Test Cases', ASSIGNMENT_PAGE).type).toBe('assignment');
    expect(detectSubmissionType('Test Plan Draft', ASSIGNMENT_PAGE).type).toBe('assignment');
    expect(detectSubmissionType('Unit Testing Lab', ASSIGNMENT_PAGE).type).toBe('assignment');
    expect(detectSubmissionType('Pretest Survey', ASSIGNMENT_PAGE).type).toBe('assignment');
  });

  it('keeps practice and review versions low stakes', () => {
    expect(detectSubmissionType('Practice Exam', QUIZ_PAGE).type).toBe('quiz');
    expect(detectSubmissionType('Midterm Review', ASSIGNMENT_PAGE).type).toBe('assignment');
  });

  it('marks a proctored quiz page as a test when the title has no clue', () => {
    const text = `${QUIZ_PAGE}\nThis quiz requires Respondus LockDown Browser`;
    expect(detectSubmissionType('Module 4 Check', text).type).toBe('test');
  });

  it('keeps normal quizzes and assignments the same as before', () => {
    expect(detectSubmissionType('Weekly Quiz', QUIZ_PAGE).type).toBe('quiz');
    expect(detectSubmissionType('Homework 1', ASSIGNMENT_PAGE).type).toBe('assignment');
    expect(detectSubmissionType(null, ASSIGNMENT_PAGE).type).toBe('assignment');
  });

  it('explains why it picked the type', () => {
    expect(detectSubmissionType('Midterm 1', QUIZ_PAGE).reason).toContain('Midterm');
  });

  it('flows through parseSubmission from ocr text', () => {
    const result = parseSubmission('Quizzes > Exam 2\nTime Limit: 75 Minutes\nSubmission Details');
    expect(result.title).toBe('Exam 2');
    expect(result.type).toBe('exam');
    expect(result.typeReason).toContain('Exam');
    expect(result.missing).toEqual([]);
  });
});