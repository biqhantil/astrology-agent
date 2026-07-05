/* ── Typed HTTP client with JWT auth ─────────────────── */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

function getToken(): string | null {
  return sessionStorage.getItem('access_token');
}

function setToken(token: string): void {
  sessionStorage.setItem('access_token', token);
}

function clearToken(): void {
  sessionStorage.removeItem('access_token');
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, errBody.detail ?? 'Request failed');
  }

  return res.json() as Promise<T>;
}

/* ── Public helpers ──────────────────────────────────── */

export { getToken, setToken, clearToken };

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/* ── Typed HTTP methods ──────────────────────────────── */

export function get<T>(path: string): Promise<T> {
  return request<T>('GET', path);
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>('POST', path, body);
}

export function put<T>(path: string, body?: unknown): Promise<T> {
  return request<T>('PUT', path, body);
}

export function del<T>(path: string): Promise<T> {
  return request<T>('DELETE', path);
}

/* ── API-specific helpers ────────────────────────────── */

export function getAuthHeaders(): Record<string, string> {
  const token = getToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}
