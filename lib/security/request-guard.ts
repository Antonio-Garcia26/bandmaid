import { configuredValue, isProduction } from "@/lib/security/config";
import { constantTimeMatch } from "@/lib/security/constant-time";
import { jsonError } from "@/lib/security/responses";

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
  if (isProduction()) {
    const expectedOrigin = productionAppOrigin();
    if (!expectedOrigin) {
      return jsonError("PENDIENDTE: Configura APP_ORIGIN con una URL HTTPS válida.", 503, "CONFIG_PENDING");
    }

    const requestHost = request.headers.get("host")?.toLowerCase() ?? "";
    if (!requestHost || requestHost !== expectedOrigin.host.toLowerCase()) {
      return jsonError("No se pudo validar el host de la solicitud.", 421, "HOST_REJECTED");
    }
  }

  return validateCloudflareOrigin(request);
}
