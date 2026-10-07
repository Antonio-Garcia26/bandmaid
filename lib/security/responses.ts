export function jsonError(message: string, status: number, code?: string, headers?: HeadersInit): Response {
  const responseHeaders = new Headers(headers);
  responseHeaders.set("Cache-Control", "no-store");
  return Response.json(
    { error: message, ...(code ? { code } : {}) },
    { status, headers: responseHeaders },
  );
}

export function pendingResponse(service: string): Response {
  return jsonError(`PENDIENDTE: Configura ${service} para habilitar esta función.`, 503, "CONFIG_PENDING");
}

export function badRequest(message = "La solicitud no es válida."): Response {
  return jsonError(message, 400, "INVALID_REQUEST");
}
