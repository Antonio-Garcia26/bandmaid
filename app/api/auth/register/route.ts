import { FieldValue } from "firebase-admin/firestore";
import { NextResponse, type NextRequest } from "next/server";
import { getFirebaseAdmin } from "@/lib/firebase-admin";
import { createSessionCookie, signInWithPassword, toFanUser } from "@/lib/security/auth";
import { verifyTextCaptcha } from "@/lib/security/captcha";
import { configuredValue } from "@/lib/security/config";
import { cookieOptions, SESSION_TTL_MS } from "@/lib/security/mutation";
import { enforceRateLimit } from "@/lib/security/rate-limit";
import { jsonError, pendingResponse } from "@/lib/security/responses";
import { validateMutation } from "@/lib/security/mutation";
import { verifyTurnstile } from "@/lib/security/turnstile";

const SESSION_TTL_SECONDS = SESSION_TTL_MS / 1000;

export async function POST(request: NextRequest) {
  const limited = await enforceRateLimit(request, "auth-register");
  if (limited) return limited;

  const mutation = await validateMutation(request);
  if ("response" in mutation) return mutation.response;
  const { body } = mutation;

  if (typeof body.website !== "string" || body.website.trim() !== "") {
    return jsonError("No se pudo validar el formulario.", 400, "BOT_REJECTED");
  }

  const displayName = typeof body.displayName === "string" ? body.displayName.trim() : "";
  const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
  const password = typeof body.password === "string" ? body.password : "";
  if (displayName.length < 2 || displayName.length > 50 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254 || password.length < 8 || password.length > 128) {
    return jsonError("Revisa el nombre, correo y contraseña e inténtalo de nuevo.", 400, "INVALID_FIELDS");
  }

  // Verificación estricta del CAPTCHA de texto distorsionado contra registros automatizados y bots
  const captchaVerification = verifyTextCaptcha(body.captchaToken, body.captchaAnswer);
  if (!captchaVerification.success) {
    if (captchaVerification.code === "CAPTCHA_EXPIRED") {
      return jsonError("El código de seguridad ha expirado. Recarga la imagen para continuar.", 400, "CAPTCHA_EXPIRED");
    }
    if (captchaVerification.code === "CAPTCHA_REPLAYED") {
      return jsonError("Este código ya fue procesado. Recarga la imagen para obtener uno nuevo.", 400, "CAPTCHA_REPLAYED");
    }
    return jsonError("El texto introducido no coincide con la imagen. Inténtalo de nuevo.", 400, "CAPTCHA_INVALID");
  }

  // Si Turnstile está presente y configurado, se valida adicionalmente
  if (typeof body.turnstileToken === "string" && body.turnstileToken.trim().length > 0) {
    const turnstile = await verifyTurnstile(body.turnstileToken, "register", request);
    if (turnstile === "invalid") return jsonError("No se pudo verificar que eres una persona.", 400, "TURNSTILE_REJECTED");
  }

  const services = getFirebaseAdmin();
  if (!services || !configuredValue("NEXT_PUBLIC_FIREBASE_API_KEY")) {
    if (process.env.NODE_ENV !== "production") {
      // Modo de desarrollo: permite probar el registro y CAPTCHA localmente
      return NextResponse.json(
        {
          user: toFanUser({
            uid: "dev-registered-user-id",
            displayName,
            email,
          }),
        },
        { headers: { "Cache-Control": "no-store" } },
      );
    }
    return pendingResponse("Firebase Authentication y Firestore");
  }

  let createdUid: string | undefined;
  try {
    const created = await services.auth.createUser({ email, password, displayName });
    createdUid = created.uid;
    await services.db.collection("users").doc(created.uid).set({
      uid: created.uid,
      displayName,
      email,
      createdAt: FieldValue.serverTimestamp(),
    });

    const identity = await signInWithPassword(email, password);
    if (!identity?.idToken) throw new Error("Registration session could not be created");
    const sessionCookie = await createSessionCookie(identity.idToken);
    if (!sessionCookie) throw new Error("Registration session could not be created");

    const response = NextResponse.json(
      { user: toFanUser({ uid: created.uid, displayName, email }) },
      { headers: { "Cache-Control": "no-store" } },
    );
    response.cookies.set(
      process.env.NODE_ENV === "production" ? "__Host-bandmaid_session" : "bandmaid_session",
      sessionCookie,
      cookieOptions(SESSION_TTL_SECONDS),
    );
    return response;
  } catch (error) {
    if (createdUid) {
      await Promise.allSettled([
        services.db.collection("users").doc(createdUid).delete(),
        services.auth.deleteUser(createdUid),
      ]);
    }

    const code = error && typeof error === "object" && "code" in error ? error.code : undefined;
    if (code === "auth/email-already-exists") {
      return jsonError("No se pudo crear la cuenta con esos datos.", 409, "ACCOUNT_UNAVAILABLE");
    }
    return jsonError("No se pudo completar el registro. Inténtalo de nuevo más tarde.", 503, "AUTH_UNAVAILABLE");
  }
}
