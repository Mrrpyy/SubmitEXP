import { describe, expect, it } from 'vitest';
import { getCanvasAssignmentIds } from './services/chromeHelpers';

describe('Canvas assignment URL parsing', () => {
  it('extracts assignment identifiers', () => {
    const result = getCanvasAssignmentIds(
      'https://ufl.instructure.com/courses/12345/assignments/67890'
    );

    expect(result).toEqual({
      canvas_course_id: 12345,
      canvas_assignment_id: 67890,
    });
  });

  it('rejects non-Canvas URLs', () => {
    expect(
      getCanvasAssignmentIds(
        'https://example.com/courses/123/assignments/456'
      )
    ).toBeNull();
  });

  it('rejects non-assignment pages', () => {
    expect(
      getCanvasAssignmentIds(
        'https://ufl.instructure.com/courses/12345'
      )
    ).toBeNull();
  });
});
