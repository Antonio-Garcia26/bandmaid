import { randomBytes } from "node:crypto";
import type { NextRequest } from "next/server";
import { getAppOrigin, isProduction } from "@/lib/security/config";
import { badRequest, jsonError } from "@/lib/security/responses";
import { constantTimeMatch } from "@/lib/security/constant-time";
import { validateApiRequest } from "@/lib/security/request-guard";

export const MAX_JSON_BODY_BYTES = 16 * 1024;
export const CSRF_COOKIE = isProduction() ? "__Host-bandmaid_csrf" : "bandmaid_csrf";
export const SESSION_COOKIE = isProduction() ? "__Host-bandmaid_session" : "bandmaid_session";
export const SESSION_TTL_MS = 5 * 24 * 60 * 60 * 1000;

export type JsonRecord = Record<string, unknown>;
export type MutationResult = { body: JsonRecord } | { response: Response };

async function readBoundedJson(request: Request): Promise<JsonRecord | null> {
  const length = Number(request.headers.get("content-length"));
  if (Number.isFinite(length) && length > MAX_JSON_BODY_BYTES) return null;
  if (!request.body) return null;

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_JSON_BODY_BYTES) {
        await reader.cancel();
        return null;
      }
      chunks.push(value);
    }
  } catch {
    return null;
  }

  try {
    const bytes = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    const parsed: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    return parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as JsonRecord)
      : null;
  } catch {
    return null;
  }
}

export async function validateMutation(request: NextRequest): Promise<MutationResult> {
  const apiGuard = validateApiRequest(request);
  if (apiGuard) return { response: apiGuard };

  const origin = getAppOrigin(request);
  if (!origin) {
    return { response: jsonError("El servicio aún no está configurado.", 503, "CONFIG_PENDING") };
  }

  if (request.headers.get("origin") !== origin.origin) {
    return { response: jsonError("No se pudo validar el origen de la solicitud.", 403, "ORIGIN_REJECTED") };
  }

  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite?.toLowerCase() === "cross-site") {
    return { response: jsonError("No se pudo validar el origen de la solicitud.", 403, "ORIGIN_REJECTED") };
  }

  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? "")) {
    return { response: badRequest("El formato de la solicitud debe ser JSON.") };
  }

  const csrfCookie = request.cookies.get(CSRF_COOKIE)?.value ?? "";
  const csrfHeader = request.headers.get("x-csrf-token") ?? "";
  if (!csrfCookie || !csrfHeader || !constantTimeMatch(csrfCookie, csrfHeader)) {
    return { response: jsonError("No se pudo validar la solicitud. Actualiza la página e inténtalo de nuevo.", 403, "CSRF_REJECTED") };
  }

  const body = await readBoundedJson(request);
  if (!body) {
    return { response: jsonError("La solicitud está vacía, no es válida o excede el tamaño permitido.", 413, "BODY_REJECTED") };
  }

  return { body };
}

export function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: isProduction(),
    sameSite: "strict" as const,
    path: "/",
    maxAge,
  };
}

export function newCsrfToken(): string {
  return randomBytes(32).toString("hex");
}
