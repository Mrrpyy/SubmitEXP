// The local FastAPI server. This URL is already covered by manifest.json.
export type SubmissionType = 'assignment' | 'quiz' | 'test' | 'exam';
export const API_BASE_URL = 'http://127.0.0.1:8000';

export interface SubmissionMetadata {
  assignment_title: string;
  course_name?: string | null;
  submission_type: SubmissionType;
  due_at?: string | null;        // ISO 8601 date/time
  submitted_at?: string | null;  // ISO 8601 date/time
}

export interface ValidationResponse {
  accepted: boolean;
  submission_type: SubmissionType;
  message: string;
}

interface HealthResponse {
  status: string;
}

// the two roles the backend allows
export type UserRole = 'student' | 'admin';

export interface User {
  user_id: number;
  username: string;
  email: string;
  role: UserRole;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// remembers the HTTP status so the popup can tell "login expired" from "backend offline"
export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

async function apiRequest<T>(path: string, body?: unknown, token?: string): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const options: RequestInit = {
      method: body === undefined ? 'GET' : 'POST',
      signal: controller.signal,
    };

    const headers: Record<string, string> = {};

    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }

     // Logged in requests carry the login token from /auth/login.
    if (token) headers.Authorization = `Bearer ${token}`;
    options.headers = headers;

    const response = await fetch(`${API_BASE_URL}${path}`, options);
    const data: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      let reason = `Backend returned HTTP ${response.status}`;
      if (data && typeof data === 'object' && 'detail' in data) {
        const detail = data.detail;
        if (typeof detail === 'string') reason = detail;

        else if (Array.isArray(detail) && typeof detail[0]?.msg === 'string') reason = detail[0].msg;
      }
      throw new ApiError(reason, response.status);
    }

    if (data === null) throw new Error('Backend returned invalid JSON');
    return data as T;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Backend request timed out after 8 seconds');
    }
    if (error instanceof TypeError) {
      throw new Error(`Cannot connect to backend at ${API_BASE_URL}`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function checkBackendHealth(): Promise<boolean> {
  const response = await apiRequest<HealthResponse>('/health');
  return response.status === 'ok';
}

// Sends only parsed metadata. Never pass raw screenshots or credentials.
export function validateSubmissionMetadata(
  metadata: SubmissionMetadata,
): Promise<ValidationResponse> {
  return apiRequest<ValidationResponse>('/integration/validate', metadata);
}

// Implementation for user registration.
export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface RegisterResponse {
  user_id: number;
  username: string;
  email: string;
  role: string;
}

export function registerUser(
  user: RegisterRequest
): Promise<RegisterResponse> {
  return apiRequest<RegisterResponse>(
    '/auth/register',
    user
  );
}

// identifier is the username or the email
export function loginUser(identifier: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>('/auth/login', { identifier, password });
}

// Checks that a saved token still works and returns who it belongs to
export function getCurrentUser(token: string): Promise<User> {
  return apiRequest<User>('/auth/me', undefined, token);
}

// Assignment EXP calculation
export interface AssignmentPointsResponse {
  points: number;
  message: string;
}
export function previewAssignmentPoints(
  dueAt: string,
  submittedAt: string
): Promise<AssignmentPointsResponse> {
  return apiRequest<AssignmentPointsResponse>(
    '/integration/assignment-points-preview',
    {
      due_at: dueAt,
      submitted_at: submittedAt,
    }
  );
}

// Authenticated assignment EXP recording
export interface AssignmentAwardRequest {
  canvas_course_id: number;
  canvas_assignment_id: number;
  assignment_title: string;
  course_name?: string | null;
  due_at: string;
  submitted_at: string;
}

export interface AssignmentAwardResponse {
  submission_id: number;
  points_awarded: number;
  total_points: number;
  current_level: number;
}

export function awardAssignment(
  token: string,
  assignment: AssignmentAwardRequest
): Promise<AssignmentAwardResponse> {
  return apiRequest<AssignmentAwardResponse>(
    '/submissions/assignment',
    assignment,
    token
  );
}

// student only, the logged in student's points and level
export interface StudentProgress {
  username: string;
  total_points: number;
  current_level: number;
  submissions_recorded: number;
}

export function getStudentProgress(token: string): Promise<StudentProgress> {
  return apiRequest<StudentProgress>('/student/progress', undefined, token);
}

// admin only, every account and its points
export interface AdminUserRow {
  user_id: number;
  username: string;
  email: string;
  role: UserRole;
  total_points: number;
}

export function listUsers(token: string): Promise<AdminUserRow[]> {
  return apiRequest<AdminUserRow[]>('/admin/users', undefined, token);
}

// admin only, makes another account a student or an admin
export function changeUserRole(token: string, userId: number, role: UserRole): Promise<AdminUserRow> {
  return apiRequest<AdminUserRow>(`/admin/users/${userId}/role`, { role }, token);
}