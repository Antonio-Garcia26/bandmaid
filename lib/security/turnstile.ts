import "server-only";

import { getAppOrigin } from "@/lib/security/config";

type TurnstileResult = {
  success?: boolean;
  action?: string;
  hostname?: string;
};

export type TurnstileStatus = "valid" | "invalid" | "unavailable";

export async function verifyTurnstile(
  token: unknown,
  expectedAction: "register" | "login" | "create-post",
  request: Request,
): Promise<TurnstileStatus> {
  const secret = process.env.TURNSTILE_SECRET_KEY?.trim();
  const appOrigin = getAppOrigin(request);
  if (!secret || secret.toUpperCase() === "PENDIENDTE" || !appOrigin) return "unavailable";
  if (typeof token !== "string" || token.length < 1 || token.length > 2048) return "invalid";

  try {
    const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ secret, response: token }),
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
    });
    if (!response.ok) return "unavailable";

    const result = (await response.json()) as TurnstileResult;
    return result.success && result.action === expectedAction && result.hostname === appOrigin.hostname
      ? "valid"
      : "invalid";
  } catch {
    return "unavailable";
  }
}
