import { NextResponse, type NextRequest } from "next/server";
import { getAppOrigin } from "@/lib/security/config";
import { cookieOptions, CSRF_COOKIE, newCsrfToken } from "@/lib/security/mutation";
import { jsonError } from "@/lib/security/responses";
import { validateApiRequest } from "@/lib/security/request-guard";

const CSRF_TTL_SECONDS = 60 * 60;

export async function GET(request: NextRequest) {
  const apiGuard = validateApiRequest(request);
  if (apiGuard) return apiGuard;
  const origin = getAppOrigin(request);
  if (!origin) return jsonError("El servicio aún no está configurado.", 503, "CONFIG_PENDING");

  const existingToken = request.cookies.get(CSRF_COOKIE)?.value;
  const token = existingToken && /^[a-f0-9]{64}$/i.test(existingToken) ? existingToken : newCsrfToken();
  const response = NextResponse.json({ token }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.set(CSRF_COOKIE, token, cookieOptions(CSRF_TTL_SECONDS));
  return response;
}
