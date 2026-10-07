import "server-only";

import type { NextRequest } from "next/server";
import { getFirebaseAdmin } from "@/lib/firebase-admin";
import type { FanUser } from "@/lib/types";
import { configuredValue } from "@/lib/security/config";
import { SESSION_COOKIE } from "@/lib/security/mutation";

type IdentityToolkitResult = {
  idToken?: string;
  localId?: string;
  email?: string;
  displayName?: string;
};

export function toFanUser(input: {
  uid: string;
  email?: string | null;
  displayName?: string | null;
}): FanUser {
  return {
    uid: input.uid,
    displayName: input.displayName?.trim() || "Fan de BAND-MAID",
    email: input.email ?? "",
  };
}

export async function getSessionUser(request: NextRequest): Promise<FanUser | null> {
  const sessionCookie = request.cookies.get(SESSION_COOKIE)?.value;
  const services = getFirebaseAdmin();
  if (!sessionCookie || !services) return null;

  try {
    const decoded = await services.auth.verifySessionCookie(sessionCookie, true);
    return toFanUser({ uid: decoded.uid, email: decoded.email, displayName: decoded.name });
  } catch {
    return null;
  }
}

export async function signInWithPassword(email: string, password: string): Promise<IdentityToolkitResult | null> {
  const apiKey = configuredValue("NEXT_PUBLIC_FIREBASE_API_KEY");
  if (!apiKey) return null;

  const response = await fetch(
    `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${encodeURIComponent(apiKey)}`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, password, returnSecureToken: true }),
      signal: AbortSignal.timeout(7000),
      cache: "no-store",
    },
  );
  if (!response.ok) return null;

  const result = (await response.json()) as IdentityToolkitResult;
  return typeof result.idToken === "string" && typeof result.localId === "string" ? result : null;
}

export async function createSessionCookie(idToken: string): Promise<string | null> {
  const services = getFirebaseAdmin();
  if (!services) return null;
  return services.auth.createSessionCookie(idToken, { expiresIn: 5 * 24 * 60 * 60 * 1000 });
}

export function getSessionCookieName(): string {
  return SESSION_COOKIE;
}
