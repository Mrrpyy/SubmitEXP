export type SubmissionType = 'assignment' | 'quiz' | 'test' | 'exam';// The local FastAPI server. This URL is already covered by manifest.json.
export const API_BASE_URL = 'http://127.0.0.1:8000';

export type SubmissionType = 'assignment' | 'quiz' | 'test' | 'exam';

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

async function apiRequest<T>(path: string, body?: unknown): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const options: RequestInit = {
      method: body === undefined ? 'GET' : 'POST',
      signal: controller.signal,
    };

    if (body !== undefined) {
      options.headers = { 'Content-Type': 'application/json' };
      options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE_URL}${path}`, options);
    const data: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      let reason = `Backend returned HTTP ${response.status}`;
      if (data && typeof data === 'object' && 'detail' in data) {
        const detail = data.detail;
        if (typeof detail === 'string') reason = detail;
      }
      throw new Error(reason);
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
