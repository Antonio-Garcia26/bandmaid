import { NextResponse, type NextRequest } from "next/server";
import { enforceRateLimit } from "@/lib/security/rate-limit";
import { validateApiRequest, validateUserAgent } from "@/lib/security/request-guard";
import { jsonError } from "@/lib/security/responses";
import { bandMembers } from "@/lib/data";

/**
 * Endpoint protegido para la entrega diferida de integrantes de la banda.
 * Previene el raspado directo del HTML inicial (SSR) mediante:
 * 1. Filtro estricto de User-Agent (bloquea curl, python-requests, scrapers).
 * 2. Validación de cabecera obligatoria X-Requested-With: XMLHttpRequest.
 * 3. Rate limiting local por IP (máx 30 peticiones/minuto).
 */
export async function GET(request: NextRequest) {
  // 1. Validar User-Agent sospechoso
  const uaCheck = validateUserAgent(request);
  if (uaCheck) return uaCheck;

  // 2. Validar guard general de API
  const apiCheck = validateApiRequest(request);
  if (apiCheck) return apiCheck;

  // 3. Rate limit local
  const limited = await enforceRateLimit(request, "members-list", undefined, { maxRequests: 30 });
  if (limited) return limited;

  // 4. Exigir cabecera interactiva personalizada
  const requestedWith = request.headers.get("x-requested-with");
  if (!requestedWith || requestedWith.toLowerCase() !== "xmlhttprequest") {
    return jsonError(
      "Acceso no autorizado. Este recurso requiere una solicitud interactiva del cliente.",
      403,
      "HEADER_REQUIRED"
    );
  }

  return NextResponse.json(
    { members: bandMembers },
    {
      headers: {
        "Cache-Control": "no-store, no-cache, must-revalidate",
        Pragma: "no-cache",
        "X-Content-Type-Options": "nosniff",
      },
    }
  );
}
