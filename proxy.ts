import { isIP } from "node:net";
import { NextResponse, type NextRequest } from "next/server";
import { configuredValue, isProduction } from "@/lib/security/config";
import { trustedClientIp } from "@/lib/security/ip";
import { validateApiRequest } from "@/lib/security/request-guard";

const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'self'",
  `script-src 'self' 'unsafe-inline'${isProduction() ? "" : " 'unsafe-eval'"} https://challenges.cloudflare.com`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://i.ytimg.com https://img.youtube.com",
  "font-src 'self' data:",
  "connect-src 'self' https://*.googleapis.com https://challenges.cloudflare.com wss://firestore.googleapis.com",
  "frame-src https://www.youtube-nocookie.com https://www.youtube.com https://challenges.cloudflare.com",
].join("; ");

function addSecurityHeaders(response: Response): Response {
  response.headers.set("Content-Security-Policy", contentSecurityPolicy);
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  if (isProduction()) response.headers.set("Strict-Transport-Security", "max-age=31536000");
  return response;
}

function deniedIp(request: NextRequest): boolean {
  const configured = configuredValue("BLOCKED_IPS");
  if (!configured) return false;
  const blocked = configured
    .split(",")
    .map((ip) => ip.trim())
    .filter((ip) => isIP(ip) !== 0);
  const clientIp = trustedClientIp(request);
  return clientIp !== "unknown" && blocked.includes(clientIp);
}

export function proxy(request: NextRequest) {
  if (deniedIp(request)) {
    return addSecurityHeaders(NextResponse.json({ error: "Acceso denegado.", code: "IP_BLOCKED" }, { status: 403 }));
  }

  if (isProduction() && request.nextUrl.pathname.startsWith("/api/")) {
    const apiGuard = validateApiRequest(request);
    if (apiGuard) return addSecurityHeaders(apiGuard);
  }

  return addSecurityHeaders(NextResponse.next());
}

export const config = {
  matcher: "/:path*",
};
