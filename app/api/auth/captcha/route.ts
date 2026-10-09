import { type NextRequest } from "next/server";
import { connection } from "next/server";
import { generateTextCaptcha } from "@/lib/security/captcha";
import { enforceRateLimit } from "@/lib/security/rate-limit";
import { validateApiRequest } from "@/lib/security/request-guard";

export async function GET(request: NextRequest) {
  await connection();

  const apiGuard = validateApiRequest(request);
  if (apiGuard) return apiGuard;

  // Límite de tasa para impedir raspado masivo automatizado pero permitiendo recargas legítimas (hasta 30 por minuto)
  const limited = await enforceRateLimit(request, "auth-captcha", undefined, { maxRequests: 30 });
  if (limited) return limited;

  const challenge = generateTextCaptcha();

  return Response.json(challenge, {
    headers: {
      "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
      Pragma: "no-cache",
    },
  });
}
