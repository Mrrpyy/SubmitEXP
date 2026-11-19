import type { AssignmentAwardResponse } from '../services/api';
import type { CanvasAssignmentIds } from '../services/chromeHelpers';
import type { ParsedSubmission } from '../services/parse';

type Props = {
  submission: ParsedSubmission;
  assignmentIds: CanvasAssignmentIds;
  previewPoints: number;
  confirmed: boolean;
  recording: boolean;
  result: AssignmentAwardResponse | null;
  error: string | null;
  onConfirmedChange: (value: boolean) => void;
  onBack: () => void;
  onRecord: () => void;
  onDone: () => void;
};

/** A separate review step. Nothing is recorded until the user confirms. */
export default function SubmissionConfirmation({
  submission, assignmentIds, previewPoints, confirmed, recording, result, error, onConfirmedChange, onBack, onRecord,
  onDone, }: Props) {
  return (
    <section className="panel submission-confirmation" aria-label="Submission confirmation">
      {result ? (
        <>
          <p className="confirmation-step">Submission recorded</p>
          <h2>EXP recorded</h2>
          <p className="form-success" role="status">
            This assignment was recorded successfully.
          </p>
          <dl className="confirmation-details">
            <div><dt>Assignment</dt><dd>{submission.title}</dd></div>
            <div><dt>EXP awarded</dt><dd>{`+${result.points_awarded}`}</dd></div>
            <div><dt>Total EXP</dt><dd>{result.total_points}</dd></div>
            <div><dt>Current level</dt><dd>{result.current_level}</dd></div>
          </dl>
          <button type="button" onClick={onDone}>Done</button>
        </>
      ) : (
        <>
          <p className="confirmation-step">Final step · Review before recording</p>
          <h2>Confirm submission</h2>
          <p>Compare these OCR-detected details with the current Canvas assignment.</p>
          <dl className="confirmation-details">
            <div><dt>Assignment</dt><dd>{submission.title}</dd></div>
            <div><dt>Type</dt><dd>{submission.type}</dd></div>
            <div><dt>Canvas course ID</dt><dd>{assignmentIds.canvas_course_id}</dd></div>
            <div><dt>Canvas assignment ID</dt><dd>{assignmentIds.canvas_assignment_id}</dd></div>
            <div><dt>Due</dt><dd>{submission.dueAt}</dd></div>
            <div><dt>Submitted</dt><dd>{submission.submittedAt}</dd></div>
            <div>
              <dt>Computer timezone</dt>
              <dd>{Intl.DateTimeFormat().resolvedOptions().timeZone || 'Local time'}</dd>
            </div>
          </dl>
          <div className="confirmation-exp">
            <span>EXP to record</span>
            <strong>{`+${previewPoints} EXP`}</strong>
          </div>
          <p className="confirmation-disclaimer">
            Local prototype: these dates come from OCR and have not been independently
            verified against Canvas by the backend. No EXP is recorded until you confirm.
          </p>
          <label className="confirmation-checkbox">
            <input type="checkbox" checked={confirmed} disabled={recording}
              onChange={(event) => onConfirmedChange(event.target.checked)}
            />
            <span>
              I checked the assignment title and dates against Canvas, including
              the year and my computer timezone.
            </span>
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="confirmation-actions">
            <button type="button" className="confirmation-back" disabled={recording} onClick={onBack}>
              Back to details
            </button>
            <button type="button" disabled={!confirmed || recording} onClick={onRecord}>
              {recording ? 'Recording...' : 'Confirm and record EXP'}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
