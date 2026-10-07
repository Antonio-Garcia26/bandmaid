import { NextResponse, type NextRequest } from "next/server";
import { cookieOptions, CSRF_COOKIE, SESSION_COOKIE, validateMutation } from "@/lib/security/mutation";

export async function POST(request: NextRequest) {
  const mutation = await validateMutation(request);
  if ("response" in mutation) return mutation.response;

  const response = NextResponse.json({ ok: true }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.set(SESSION_COOKIE, "", cookieOptions(0));
  response.cookies.set(CSRF_COOKIE, "", cookieOptions(0));
  return response;
}
