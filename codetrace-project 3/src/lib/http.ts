/** Configurable API settings for the future FastAPI backend. Mock mode is the default. */
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/v1';
export const USE_MOCKS: boolean = (import.meta.env.VITE_USE_MOCKS ?? 'true') === 'true';

export interface ApiErrorBody {
  error?: { code?: string; message?: string; request_id?: string; details?: Record<string, unknown> };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly requestId?: string;

  constructor(status: number, body?: ApiErrorBody) {
    super(body?.error?.message ?? `Request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.code = body?.error?.code;
    this.requestId = body?.error?.request_id;
  }
}

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 20_000);
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) }, signal: controller.signal, ...init });
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw new Error('The API request timed out.');
    throw new Error('The CodeTrace API is unavailable.');
  } finally { window.clearTimeout(timeout); }
  if (!res.ok) {
    let body: ApiErrorBody | undefined;
    try { body = await res.json() as ApiErrorBody; } catch { /* Preserve the status when the server did not return JSON. */ }
    throw new ApiError(res.status, body);
  }
  return res.json() as Promise<T>;
}
