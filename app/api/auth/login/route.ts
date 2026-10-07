import { NextResponse, type NextRequest } from "next/server";
import { getFirebaseAdmin } from "@/lib/firebase-admin";
import { createSessionCookie, signInWithPassword, toFanUser } from "@/lib/security/auth";
import { configuredValue } from "@/lib/security/config";
import { cookieOptions, SESSION_TTL_MS } from "@/lib/security/mutation";
import { enforceRateLimit } from "@/lib/security/rate-limit";
import { jsonError, pendingResponse } from "@/lib/security/responses";
import { validateMutation } from "@/lib/security/mutation";
import { verifyTurnstile } from "@/lib/security/turnstile";

const SESSION_TTL_SECONDS = SESSION_TTL_MS / 1000;

export async function POST(request: NextRequest) {
  const limited = await enforceRateLimit(request, "auth-login");
  if (limited) return limited;

  const mutation = await validateMutation(request);
  if ("response" in mutation) return mutation.response;
  const { body } = mutation;

  if (typeof body.website !== "string" || body.website.trim() !== "") {
    return jsonError("No se pudo validar el formulario.", 400, "BOT_REJECTED");
  }

  const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
  const password = typeof body.password === "string" ? body.password : "";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254 || password.length < 1 || password.length > 128) {
    return jsonError("El correo o la contraseña no son válidos.", 400, "INVALID_FIELDS");
  }

  const turnstile = await verifyTurnstile(body.turnstileToken, "login", request);
  if (turnstile === "unavailable") return pendingResponse("Cloudflare Turnstile");
  if (turnstile === "invalid") return jsonError("No se pudo verificar que eres una persona.", 400, "TURNSTILE_REJECTED");

  if (!getFirebaseAdmin() || !configuredValue("NEXT_PUBLIC_FIREBASE_API_KEY")) {
    return pendingResponse("Firebase Authentication");
  }

  try {
    const identity = await signInWithPassword(email, password);
    if (!identity?.idToken || !identity.localId) {
      return jsonError("El correo o la contraseña no coinciden.", 401, "INVALID_CREDENTIALS");
    }
    const sessionCookie = await createSessionCookie(identity.idToken);
    if (!sessionCookie) return pendingResponse("Firebase Authentication");

    const response = NextResponse.json(
      {
        user: toFanUser({
          uid: identity.localId,
          email: identity.email ?? email,
          displayName: identity.displayName,
        }),
      },
      { headers: { "Cache-Control": "no-store" } },
    );
    response.cookies.set(
      process.env.NODE_ENV === "production" ? "__Host-bandmaid_session" : "bandmaid_session",
      sessionCookie,
      cookieOptions(SESSION_TTL_SECONDS),
    );
    return response;
  } catch {
    return jsonError("No se pudo completar el inicio de sesión. Inténtalo de nuevo más tarde.", 503, "AUTH_UNAVAILABLE");
  }
}
