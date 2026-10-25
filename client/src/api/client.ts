/**
 * GlobalPay 2.0 Typed API Client for /api/v1
 * Automatically attaches Bearer session token, CSRF header, and Idempotency-Key.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export interface ApiRequestOptions extends RequestInit {
  token?: string | null;
  idempotencyKey?: string;
}

export async function apiFetch<T>(endpoint: string, options: ApiRequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }
  if (options.idempotencyKey) {
    headers.set("Idempotency-Key", options.idempotencyKey);
  }
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: "include",
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `API request failed with status ${response.status}`);
  }
  return payload as T;
}
