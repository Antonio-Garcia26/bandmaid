import type { FanUser, Post } from "@/lib/types";

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

type ApiErrorPayload = { error?: unknown; code?: unknown };

async function parseError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload = {};
  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    // Keep a useful local message if an upstream error was not JSON.
  }
  return new ApiError(
    typeof payload.error === "string" ? payload.error : "No se pudo completar la solicitud.",
    response.status,
    typeof payload.code === "string" ? payload.code : undefined,
  );
}

export async function requestJson<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    method: "GET",
    credentials: "same-origin",
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as T;
}

export async function mutateJson<T>(url: string, body: Record<string, unknown>): Promise<T> {
  const csrfResponse = await fetch("/api/csrf", {
    method: "GET",
    credentials: "same-origin",
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!csrfResponse.ok) throw await parseError(csrfResponse);

  const csrfPayload = (await csrfResponse.json()) as { token?: unknown };
  if (typeof csrfPayload.token !== "string" || !csrfPayload.token) {
    throw new ApiError("No se pudo iniciar la validación segura. Actualiza la página e inténtalo de nuevo.", 503, "CSRF_UNAVAILABLE");
  }

  const response = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfPayload.token,
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as T;
}

export function newPostId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();

  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export type SessionResponse = { user: FanUser | null; configured: boolean };
export type PostsResponse = { posts: Post[]; configured: true };
