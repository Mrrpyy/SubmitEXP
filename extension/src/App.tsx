import { useEffect, useRef, useState } from 'react';
import RegistrationForm from './components/RegistrationForm';
import LoginForm from './components/LoginForm';
import BackendConnectionStatus from './components/BackendConnectionStatus';
import ProfileDashboard from './components/ProfileDashboard';
import AdminPanel from './components/AdminPanel';
import {ApiError, awardAssignment, getCurrentUser, previewAssignmentPoints,} from './services/api';
import type { AssignmentAwardResponse, User } from './services/api';
import {captureCanvasScreenshot, getActiveTabUrl, getCanvasAssignmentIds,
  isCanvasUrl, isExtension, loadValue, pingBackground, saveValue,} from './services/chromeHelpers';
import type { CanvasAssignmentIds } from './services/chromeHelpers';
import { recognizeScreenshot } from './services/ocr';
import { parseSubmission } from './services/parse';
import type { ParsedSubmission } from './services/parse';
import {clearSession, loadSession, saveSession,} from './services/session';
import { AuthRequestGuard } from './authRequestGuard';
import { getStudentProgress } from './services/api';
import type { StudentProgress } from './services/api';
// Convert Canvas local dates to ISO 8601 timestamps, assumes Canvas displays dates in the computers timezone
function canvasDateToISO(value: string): string {
  const match = value.match(
    /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/
  );
  if (!match) {
    throw new Error('Invalid Canvas date format');
  }
  const [, yearText, monthText, dayText, hourText,
    minuteText, secondText] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const hour = Number(hourText);
  const minute = Number(minuteText);
  const second = Number(secondText);
  const date = new Date(
    year,
    month - 1,
    day,
    hour,
    minute,
    second
  );
// Prevent invalid dates from being normalized silently.
  if (
    Number.isNaN(date.getTime()) ||
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day ||
    date.getHours() !== hour ||
    date.getMinutes() !== minute ||
    date.getSeconds() !== second
  ) {
    throw new Error('Invalid Canvas date');
  }

  return date.toISOString();
}
export default function App() {
// Canvas submission checking
  const [checking, setChecking] = useState(false);
  const [submission, setSubmission] =
    useState<ParsedSubmission | null>(null);
  const [checkError, setCheckError] =
    useState<string | null>(null);
  const [rawOcrText, setRawOcrText] = useState<string | null>(null);
  const [dueYear, setDueYear] = useState('');
  const [submittedYear, setSubmittedYear] = useState('');
  const previewRequest = useRef(0);
// Assignment EXP preview
  const [previewPoints, setPreviewPoints] =
    useState<number | null>(null);
  const [previewError, setPreviewError] =
    useState<string | null>(null);
// Review the Canvas assignment identity and OCR dates
  const [assignmentIds, setAssignmentIds] =
    useState<CanvasAssignmentIds | null>(null);
  const [detailsConfirmed, setDetailsConfirmed] =
    useState(false);
// EXP recording for local prototype tests; OCR is not independent proof of submission
  const [awarding, setAwarding] = useState(false);
  const [awardResult, setAwardResult] =
    useState<AssignmentAwardResponse | null>(null);
  const [awardError, setAwardError] =
    useState<string | null>(null);
// Extension status
  const [onCanvas, setOnCanvas] = useState(false);
  const [backgroundOk, setBackgroundOk] = useState(false);
  const [timesOpened, setTimesOpened] = useState(0);
// Logged in user
  const [user, setUser] = useState<User | null>(null);
  const authGuard = useRef(new AuthRequestGuard());
  const sessionWriteQueue = useRef<Promise<void>>(
    Promise.resolve()
  );

  function queueSessionWrite(
    action: () => Promise<void>
  ): Promise<void> {
    const operation = sessionWriteQueue.current
      .catch(() => undefined)
      .then(action);

    sessionWriteQueue.current = operation;
    return operation;
  }

// Runs once every time the popup opens
  useEffect(() => {
    async function setup() {
      const url = await getActiveTabUrl();

      setOnCanvas(isCanvasUrl(url));
      setBackgroundOk(await pingBackground());

      const count =
        ((await loadValue<number>('timesOpened')) ?? 0) + 1;

      await saveValue('timesOpened', count);
      setTimesOpened(count);
    }

    setup().catch((error) => {
      console.error('Popup setup failed:', error);
    });
  }, []);
  const [progress, setProgress] =
  useState<StudentProgress | null>(null);

  const [progressError, setProgressError] =
    useState<string | null>(null);

// only students earn EXP, admins can look but not record
  const isStudent = user?.role === 'student';
  useEffect(() => {
    let cancelled = false;
    setProgress(null);
    setProgressError(null);

    if (!user || user.role !== 'student') {
      return;
    }

    const userId = user.user_id;

    async function fetchProgress() {
      try {
        const session = await loadSession();

        if (!session || session.user.user_id !== userId) {
          return;
        }

        const result = await getStudentProgress(
          session.token
        );

        if (!cancelled) {
          setProgress(result);
          setProgressError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setProgressError(
            error instanceof Error
              ? error.message
              : 'Unable to load progress'
          );
        }
      }
    }

    void fetchProgress();

    return () => {
      cancelled = true;
    };
  }, [user?.user_id, user?.role]);

// Restore saved login when popup opens
  useEffect(() => {
    const requestId = authGuard.current.begin();

    async function restore() {
      const session = await loadSession();

      if (!authGuard.current.isCurrent(requestId)) {
        return;
      }

      if (!session) return;

// Display saved user immediately
      setUser(session.user);
      try {
        const currentUser = await getCurrentUser(
          session.token
        );

        if (!authGuard.current.isCurrent(requestId)) {
          return;
        }

        setUser(currentUser);
      } catch (error) {
        if (!authGuard.current.isCurrent(requestId)) {
          return;
        }
// Only clear session when token is invalid
        if (
          error instanceof ApiError &&
          error.status === 401
        ) {
          await queueSessionWrite(clearSession);

          if (authGuard.current.isCurrent(requestId)) {
            setUser(null);
          }
        }
      }
    }

    restore().catch((error) => {
      console.error('Restoring login failed:', error);
    });

    return () => {
      authGuard.current.invalidate();
    };
  }, []);
// Handle successful login
  async function handleLoggedIn(
    token: string,
    loggedInUser: User
  ) {
    const requestId = authGuard.current.begin();

    await queueSessionWrite(() =>
      saveSession({ token, user: loggedInUser })
    );

    if (!authGuard.current.isCurrent(requestId)) {
      return;
    }

    setUser(loggedInUser);
  }
// Handle logout
  async function handleLogout() {
    authGuard.current.invalidate();

    try {
      await queueSessionWrite(clearSession);
      setUser(null);
      previewRequest.current += 1;
      setSubmission(null);
      setRawOcrText(null);
      setDueYear('');
      setSubmittedYear('');
      setPreviewPoints(null);
      setPreviewError(null);
      setCheckError(null);
      setAssignmentIds(null);
      setDetailsConfirmed(false);
      setAwardResult(null);
      setAwardError(null);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  }
async function loadExpPreview(parsed: ParsedSubmission) {
  const request = ++previewRequest.current;

  setPreviewPoints(null);
  setPreviewError(null);
  setDetailsConfirmed(false);

  if (
    parsed.type !== 'assignment' ||
    !parsed.dueAt ||
    !parsed.submittedAt
  ) return;

  try {
    const due = canvasDateToISO(parsed.dueAt);
    const submitted = canvasDateToISO(parsed.submittedAt);

    const difference = Math.abs(
      new Date(due).getTime() -
      new Date(submitted).getTime()
    );

    const MAX_DIFFERENCE = 180 * 24 * 60 * 60 * 1000;

    if (difference > MAX_DIFFERENCE) {
      throw new Error(
        'Dates are unusually far apart. Please verify the OCR results.'
      );
    }

    const preview = await previewAssignmentPoints(
      due,
      submitted
    );

    if (request === previewRequest.current) {
      setPreviewPoints(preview.points);
    }
  } catch (error) {
    if (request === previewRequest.current) {
      setPreviewError(
        error instanceof Error
          ? error.message
          : 'Unable to calculate EXP'
      );
    }
  }
}
function invalidateYearSelection() {
  previewRequest.current += 1;
  setPreviewPoints(null);
  setPreviewError(null);
  setDetailsConfirmed(false);
}
async function handleApplyYears() {
  if (
    !rawOcrText ||
    !submission ||
    checking ||
    awarding ||
    awardResult
  ) return;
  invalidateYearSelection();
  const validYear = (value: string) =>
    /^\d{4}$/.test(value) &&
    Number(value) >= 1000;
  if (
    (submission.missingYears.includes('dueAt') &&
      !validYear(dueYear)) ||
    (submission.missingYears.includes('submittedAt') &&
      !validYear(submittedYear))
  ) {
    setPreviewError(
      'Enter a valid four-digit year for each missing date.'
    );
    return;
  }
  const parsed = parseSubmission(rawOcrText, {
    due: dueYear ? Number(dueYear) : undefined,
    submitted: submittedYear ? Number(submittedYear) : undefined,
  });
  setSubmission(parsed);
  if (!parsed.dueAt || !parsed.submittedAt) {
    setPreviewError(
      'Could not read the dates. Check the Canvas page and try again.'
    );
    return;
  }
  await loadExpPreview(parsed);
}
// Capture Canvas and calculate assignment EXP preview
  async function handleCheckSubmission() {
    if (checking || awarding || !user || !isStudent || !onCanvas) return;

    setChecking(true);
    previewRequest.current += 1;
    setCheckError(null);
    setSubmission(null);
    setRawOcrText(null);
    setDueYear('');
    setSubmittedYear('');
    setPreviewPoints(null);
    setPreviewError(null);
    setAssignmentIds(null);
    setDetailsConfirmed(false);
    setAwardResult(null);
    setAwardError(null);
    try {
// Identify the assignment from the active Canvas URL
      const url = await getActiveTabUrl();
      const ids = getCanvasAssignmentIds(url);

      if (!ids) {
        throw new Error(
          'Open an individual Canvas assignment page first.'
        );
      }
      setAssignmentIds(ids);
// Capture the active Canvas page
      const screenshot = await captureCanvasScreenshot();
// Perform OCR locally
      const result = await recognizeScreenshot(screenshot);
      console.log('OCR TEXT:', result.text);
// Extract assignment information
    const parsed = parseSubmission(result.text);
    setRawOcrText(result.text);
    setSubmission(parsed);
    await loadExpPreview(parsed);
    } catch (error) {
      setCheckError(
        error instanceof Error
          ? error.message
          : 'Failed to check submission.'
      );
    } finally {
      setChecking(false);
    }
  }

// Record confirmed OCR-derived submission as EXP for local prototype testing
  async function handleAwardAssignment() {
    if (
      awarding || checking || !user || !detailsConfirmed || !assignmentIds ||
      !submission || submission.type !== 'assignment' ||
      !submission.title?.trim() || !submission.dueAt ||
      !submission.submittedAt || previewPoints === null ||
      previewError !== null || awardResult !== null
    ) {
      return;
    }

    setAwarding(true);
    setAwardError(null);

    try {
// Confirm the active URL still identifies the checked assignment
      const currentIds = getCanvasAssignmentIds(await getActiveTabUrl());
      if (
        !currentIds ||
        currentIds.canvas_course_id !== assignmentIds.canvas_course_id ||
        currentIds.canvas_assignment_id !== assignmentIds.canvas_assignment_id
      ) {
        throw new Error(
          'The active Canvas assignment changed. Check Submission again.'
        );
      }

// Use the existing stored login token
      const session = await loadSession();
      if (!session) {
        throw new Error('Your login has expired. Please sign in again.');
      }

// Only send extracted metadata, never the screenshot
      const response = await awardAssignment(session.token, {
        canvas_course_id: assignmentIds.canvas_course_id,
        canvas_assignment_id: assignmentIds.canvas_assignment_id,
        assignment_title: submission.title.trim(),
        due_at: canvasDateToISO(submission.dueAt),
        submitted_at: canvasDateToISO(submission.submittedAt),
      });

      setAwardResult(response);
      try {
        const updatedProgress = await getStudentProgress(
          session.token
        );

        setProgress(updatedProgress);
        setProgressError(null);
      } catch {
        setProgressError(
          'EXP was recorded, but progress could not refresh.'
        );
      }

    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setAwardError('This assignment has already been awarded EXP.');
      } else if (error instanceof ApiError && error.status === 401) {
        setAwardError('Your login has expired. Please sign in again.');
      } else {
        setAwardError(
          error instanceof Error ? error.message : 'Could not record EXP.'
        );
      }
    } finally {
      setAwarding(false);
    }
  }

  return (
    <main className="shell">
      <div className="tag">SPRINT 1</div>

      <h1>
        Submit<span>EXP</span>
      </h1>

      <p className="motto">
        Finish early. Level up.
      </p>

{/* ---------- profile dashboard ---------- */}
      {user ? (
        <ProfileDashboard
          user={user}
          onLogout={handleLogout}
          refreshKey={awardResult?.submission_id ?? 0}
        />
      ) : (
        <LoginForm onLoggedIn={handleLoggedIn} />
      )}
{/* Student level and EXP progress */}
{user && isStudent && (
  <section className="panel level-panel">
    <h2>Your Progress</h2>

    {progress ? (
      <>
        <div className="level-header">
          <strong>
            Level {progress.current_level}
          </strong>
          <span>
            {progress.total_points} Total EXP
          </span>
        </div>

        <div
          className="exp-track"
          role="progressbar"
          aria-label="Level progress"
          aria-valuemin={0}
          aria-valuemax={progress.exp_for_next_level}
          aria-valuenow={progress.exp_in_level}
        >
          <div
            className="exp-fill"
            style={{
              width: `${progress.progress_percent}%`,
            }}
          />
        </div>

        <p>
          {progress.exp_in_level} /
          {' '}{progress.exp_for_next_level} EXP
        </p>

        <small>
          {progress.exp_to_next_level} EXP needed
          for Level {progress.current_level + 1}
        </small>

        <small>
          {progress.submissions_recorded}
          {' '}submissions recorded
        </small>
      </>
    ) : (
      <p>
        {progressError ?? 'Loading your progress...'}
      </p>
    )}
  </section>
)}

{/* ---------- admin interface ---------- */}
      {user?.role === 'admin' && <AdminPanel currentUser={user} />}

{/* Extension status */}
      <section
        className="panel"
        style={{ marginTop: 12 }}
      >
        <h2>Status</h2>

        <ul className="status">
          <li>
            Running as extension:{' '}
            {isExtension ? 'yes' : 'no (dev preview)'}
          </li>

          <li>
            Background worker:{' '}
            {backgroundOk ? 'running' : 'not found'}
          </li>

          <li>
            Current tab is Canvas:{' '}
            {onCanvas ? 'yes' : 'no'}
          </li>

          <li>
            Popup opened: {timesOpened} times
          </li>
        </ul>

{/* Check Submission */}
        <button
          type="button"
          disabled={!onCanvas || !user || !isStudent || checking || awarding}
          onClick={handleCheckSubmission}
        >
          {checking ? 'Checking...' : 'Check Submission'}
        </button>

{/* admins cannot earn EXP */}
        {user && !isStudent && (
          <p>
            <small>Admin accounts do not earn EXP. Log in as a student to check submissions.</small>
          </p>
        )}

{/* OCR errors */}
        {checkError && (
          <p className="form-error">
            {checkError}
          </p>
        )}

{/* Parsed submission information */}
        {submission && (
          <div>
            <h3>Submission Details</h3>

            <p>
              Title: {submission.title ?? 'Not found'}
            </p>

            <p>
              Type: {submission.type}
            </p>

            <small>
              Why: {submission.typeReason}
            </small>

{/* tests and exams get their own EXP rules later (item 12) */}
            {(submission.type === 'test' || submission.type === 'exam') && (
              <p>
                This looks like a {submission.type}. Test and exam EXP is not scored yet.
              </p>
            )}

            <p>
              Due: {submission.dueAt ?? 'Not found'}
            </p>

            <p>
              Submitted:{' '}
              {submission.submittedAt ?? 'Not found'}
            </p>
            {submission.type === 'assignment' &&
              submission.missingYears.length > 0 && (
                <div>
                  <p className="form-error">
                    Canvas did not show a year for one or more dates.
                    Enter the correct year before calculating EXP.
                  </p>
            
                  {submission.missingYears.includes('dueAt') && (
                    <label>
                      Due year
                      <input
                        type="number"
                        min={1000}
                        max={9999}
                        value={dueYear}
                        disabled={awarding || awardResult !== null}
                        onChange={(event) => {
                          setDueYear(event.target.value);
                          invalidateYearSelection();
                        }}
                        placeholder="e.g. 2027"
                      />
                    </label>
                  )}
            
                  {submission.missingYears.includes('submittedAt') && (
                    <label>
                      Submitted year
                      <input
                        type="number"
                        min={1000}
                        max={9999}
                        value={submittedYear}
                        disabled={awarding || awardResult !== null}
                        onChange={(event) => {
                          setSubmittedYear(event.target.value);
                          invalidateYearSelection();
                        }}
                        placeholder="e.g. 2026"
                      />
                    </label>
                  )}
            
                  <button
                    type="button"
                    disabled={checking || awarding || awardResult !== null}
                    onClick={() => void handleApplyYears()}
                  >
                    Apply years and calculate EXP
                  </button>
                </div>
              )}

            {submission.missing.length > 0 && (
              <p className="form-error">
                Missing:{' '}
                {submission.missing.join(', ')}
              </p>
            )}

            <small>
              Dates are extracted from Canvas using OCR.
              {awardResult
                ? ' EXP has been recorded in the test database.'
                : ' No EXP has been awarded.'}
            </small>
          </div>
        )}

{/* Assignment EXP preview */}
        {previewPoints !== null && (
          <div>
            <h3>Assignment EXP Preview</h3>

            <p>
              EXP Earned: <strong>{previewPoints}</strong>
            </p>

            <small>
              {awardResult
                ? 'Points recorded in the test database. '
                : 'Preview only. No points have been awarded. '}
              Dates are interpreted using your computer's
              timezone and have not been verified against Canvas.
            </small>
          </div>
        )}

{/* Local review and test EXP recording */}
        {previewPoints !== null && assignmentIds && (
          <div style={{ marginTop: 12 }}>
            <h3>Verify Submission</h3>

            <p>
              Canvas Course ID: {assignmentIds.canvas_course_id}
            </p>

            <p>
              Canvas Assignment ID: {assignmentIds.canvas_assignment_id}
            </p>

            <p>
              Computer timezone:{' '}
              {Intl.DateTimeFormat().resolvedOptions().timeZone}
            </p>

            <label>
              <input
                type="checkbox"
                checked={detailsConfirmed}
                disabled={awarding || awardResult !== null}
                onChange={(event) =>
                  setDetailsConfirmed(event.target.checked)
                }
              />
              {' '}I have checked the assignment dates and confirmed
              that Canvas displays times in my computer's timezone.
            </label>

            {detailsConfirmed && (
              <div>
                <p>
                  Submission confirmed locally. Test only: the backend
                  cannot independently verify OCR-derived Canvas dates.
                </p>
                <button
                  type="button"
                  disabled={
                    awarding || checking || awardResult !== null ||
                    !submission?.title?.trim() ||
                    submission?.type !== 'assignment' ||
                    !submission?.dueAt || !submission?.submittedAt
                  }
                  onClick={handleAwardAssignment}
                >
                  {awarding ? 'Recording...' : 'Record EXP (test only)'}
                </button>
              </div>
            )}

            {awardResult && (
              <div>
                <h3>EXP Recorded</h3>
                <p>Points awarded: {awardResult.points_awarded}</p>
                <p>Total EXP: {awardResult.total_points}</p>
                <p>Current level: {awardResult.current_level}</p>
              </div>
            )}

            {awardError && (
              <p className="form-error">{awardError}</p>
            )}
          </div>
        )}

{/* EXP preview errors */}
        {previewError && (
          <p className="form-error">
            {previewError}
          </p>
        )}
      </section>

{/* Backend status */}
      <BackendConnectionStatus />

{/* Registration */}
      {!user && <RegistrationForm />}

      <small>
        OCR runs locally in your browser to
        protect your screenshots.
      </small>
    </main>
  );
}
