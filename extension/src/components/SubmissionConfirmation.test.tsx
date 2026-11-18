import { describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import SubmissionConfirmation from './SubmissionConfirmation';
import type { ParsedSubmission } from '../services/parse';

const submission: ParsedSubmission = {
  title: 'Chapter 3 Homework',
  type: 'assignment',
  typeReason: 'Canvas assignment',
  dueAt: '2027-01-05 23:59:00',
  submittedAt: '2026-12-30 20:00:00',
  missing: [],
  missingYears: ['dueAt'],
};

const ids = { canvas_course_id: 51, canvas_assignment_id: 72 };

function show(overrides: Partial<Parameters<typeof SubmissionConfirmation>[0]> = {}) {
  return renderToStaticMarkup(
    <SubmissionConfirmation
      submission={submission}
      assignmentIds={ids}
      previewPoints={75}
      confirmed={false}
      recording={false}
      result={null}
      error={null}
      onConfirmedChange={vi.fn()}
      onBack={vi.fn()}
      onRecord={vi.fn()}
      onDone={vi.fn()}
      {...overrides}
    />
  );
}

describe('SubmissionConfirmation', () => {
  it('shows Canvas identity, both years, and previewed EXP before recording', () => {
    const html = show();
    expect(html).toContain('Chapter 3 Homework');
    expect(html).toContain('2027-01-05 23:59:00');
    expect(html).toContain('2026-12-30 20:00:00');
    expect(html).toContain('>51<');
    expect(html).toContain('>72<');
    expect(html).toContain('+75 EXP');
    expect(html).toContain('not been independently');
  });

  it('disables the final record action before user confirmation', () => {
    expect(show()).toMatch(/disabled=""[^>]*>Confirm and record EXP<\/button>/);
    expect(show({ confirmed: true })).not.toMatch(/disabled=""[^>]*>Confirm and record EXP<\/button>/);
  });

  it('disables navigation and record action while recording', () => {
    const html = show({ confirmed: true, recording: true });
    expect(html).toContain('Recording...');
    expect(html).toMatch(/disabled=""[^>]*>Back to details<\/button>/);
  });

  it('shows success instead of the confirmation button after recording', () => {
    const html = show({ result: { submission_id: 5, points_awarded: 75, total_points: 175, current_level: 2 } });
    expect(html).toContain('EXP recorded');
    expect(html).toContain('>175<');
    expect(html).toContain('>2<');
    expect(html).not.toContain('Confirm and record EXP');
    expect(html).toContain('>Done<');
  });

  it('shows record errors in the review step', () => {
    expect(show({ confirmed: true, error: 'This assignment has already been awarded EXP.' }))
      .toContain('This assignment has already been awarded EXP.');
  });
});
