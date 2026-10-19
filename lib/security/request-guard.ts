import { configuredValue, isProduction } from "@/lib/security/config";
import { constantTimeMatch } from "@/lib/security/constant-time";
import { jsonError } from "@/lib/security/responses";

const BLOCKED_USER_AGENTS = [
  "curl",
  "python-requests",
  "python-urllib",
  "urllib",
  "httpx",
  "scrapy",
  "wget",
  "postmanruntime",
  "headlesschrome",
  "selenium",
  "playwright",
  "puppeteer",
];

export function isBlockedUserAgent(userAgent: string | null): boolean {
  if (!userAgent || userAgent.trim() === "") return true;
  const lower = userAgent.toLowerCase();
  return BLOCKED_USER_AGENTS.some((pattern) => lower.includes(pattern));
}

export function validateUserAgent(request: Request): Response | null {
  const userAgent = request.headers.get("user-agent");
  if (isBlockedUserAgent(userAgent)) {
    return jsonError(
      "Acceso denegado. Cliente automatizado o agente de scraping no permitido.",
      403,
      "BOT_USER_AGENT_BLOCKED"
    );
  }
  return null;
}

export function validateCloudflareOrigin(request: Request): Response | null {
  if (!isProduction()) return null;
  const secret = configuredValue("CLOUDFLARE_ORIGIN_SECRET");
  if (!secret) return null;
  if (secret.length < 32) {
    return jsonError("La protección de origen aún no está configurada.", 503, "CONFIG_PENDING");
  }

  const supplied = request.headers.get("x-bandmaid-origin") ?? "";
  if (!constantTimeMatch(secret, supplied)) {
    return jsonError("No se pudo validar el origen de la solicitud.", 403, "ORIGIN_REJECTED");
  }
  return null;
}

function productionAppOrigin(): URL | null {
  const configured = configuredValue("APP_ORIGIN");
  if (!configured) return null;

  try {
    const origin = new URL(configured);
    if (
      origin.protocol !== "https:" ||
      !origin.hostname ||
      origin.username ||
      origin.password ||
      origin.pathname !== "/" ||
      origin.search ||
      origin.hash
    ) {
      return null;
    }
    return origin;
  } catch {
    return null;
  }
}

export function validateApiRequest(request: Request): Response | null {
  // Primero validar User-Agent en toda solicitud API
  const uaCheck = validateUserAgent(request);
  if (uaCheck) return uaCheck;

  if (isProduction()) {
    const expectedOrigin = productionAppOrigin();
    if (expectedOrigin) {
      const requestHost = request.headers.get("host")?.toLowerCase() ?? "";
      if (!requestHost || requestHost !== expectedOrigin.host.toLowerCase()) {
        return jsonError("No se pudo validar el host de la solicitud.", 421, "HOST_REJECTED");
      }
    } else {
      const rawOrigin = configuredValue("APP_ORIGIN");
      if (rawOrigin) {
        return jsonError("PENDIENDTE: Configura APP_ORIGIN con una URL HTTPS válida.", 503, "CONFIG_PENDING");
      }
    }
  }

  return validateCloudflareOrigin(request);
}

