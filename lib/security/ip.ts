import { isIP } from "node:net";
import type { NextRequest } from "next/server";
import { configuredValue, isProduction } from "@/lib/security/config";
import { constantTimeMatch } from "@/lib/security/constant-time";

export function trustedClientIp(request: NextRequest): string {
  if (isProduction()) {
    const cloudflareSecret = configuredValue("CLOUDFLARE_ORIGIN_SECRET");
    if (cloudflareSecret) {
      if (cloudflareSecret.length < 32) return "unknown";
      const supplied = request.headers.get("x-bandmaid-origin") ?? "";
      if (!constantTimeMatch(cloudflareSecret, supplied)) return "unknown";
      const clientIp = request.headers.get("x-bandmaid-client-ip")?.trim();
      return clientIp && isIP(clientIp) ? clientIp : "unknown";
    }
  }

  if (process.env.VERCEL === "1") {
    const candidate = request.headers.get("x-vercel-forwarded-for")?.split(",", 1)[0]?.trim();
    return candidate && isIP(candidate) ? candidate : "unknown";
  }

  if (!isProduction()) return "127.0.0.1";
  return "unknown";
}
